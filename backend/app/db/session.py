"""Engine and session management.

The models are written to be Postgres-compatible; SQLite is the zero-credential
local default. The only behavioural difference we care about is row locking:
SELECT ... FOR UPDATE is a no-op on SQLite, so the reservation path also relies
on a unique constraint and a version check rather than locks alone.
"""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

_settings = get_settings()

if _settings.is_sqlite:
    _connect_args: dict = {"check_same_thread": False}
    _engine_kwargs: dict = {}
else:
    # Supabase's session pooler drops idle connections; pre-ping and recycle
    # rather than handing a dead one to a request. The pool is kept small
    # because the free plan has a modest connection allowance.
    _connect_args = {"connect_timeout": 15}
    _engine_kwargs = {"pool_size": 5, "max_overflow": 5, "pool_recycle": 300}

engine: Engine = create_engine(
    _settings.active_database_url,
    connect_args=_connect_args,
    pool_pre_ping=not _settings.is_sqlite,
    future=True,
    **_engine_kwargs,
)

if _settings.is_sqlite:

    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_connection, _record):  # pragma: no cover - driver glue
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


def get_db() -> Iterator[Session]:
    """FastAPI dependency."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    """Standalone session for background tasks, scripts and the coordinator."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
