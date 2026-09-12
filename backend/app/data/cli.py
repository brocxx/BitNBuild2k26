"""Database setup, reference import and demo seed.

    python -m app.data.cli migrate
    python -m app.data.cli import
    python -m app.data.cli seed
    python -m app.data.cli reset      # all three, in order

`reset` is the one-liner for a fresh working demo database.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config

from app.data.importer import import_reference_data
from app.data.seed import seed_demo
from app.db.session import session_scope

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("seed")

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


def migrate() -> None:
    """Bring the database up to head. The same command works on Postgres."""
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    config.attributes["configure_logger"] = False
    command.upgrade(config, "head")
    logger.info("Database is at head.")


def run_import() -> None:
    with session_scope() as db:
        report = import_reference_data(db)
    logger.info("\n--- reference import ---\n%s", report.summary())


def run_seed() -> None:
    with session_scope() as db:
        report = seed_demo(db)
    logger.info("\n--- demo seed ---\n%s", report.summary())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="app.data.cli")
    parser.add_argument("command", choices=["migrate", "import", "seed", "reset"])
    args = parser.parse_args(argv)

    if args.command in ("migrate", "reset"):
        migrate()
    if args.command in ("import", "reset"):
        run_import()
    if args.command in ("seed", "reset"):
        run_seed()
    return 0


if __name__ == "__main__":
    sys.exit(main())
