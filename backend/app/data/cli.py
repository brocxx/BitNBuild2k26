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


DESTRUCTIVE = {"import", "seed", "reset"}


def confirm_shared_database(command: str, assume_yes: bool) -> bool:
    """Guard the shared team database against a careless reseed.

    `seed` wipes every operational table and `import` rebuilds the reference
    tables. Doing that against DB_TARGET=supabase destroys whatever the rest
    of the team is working against, including mid-demo. Local SQLite is the
    caller's own file, so it is never gated.
    """
    from app.config import get_settings

    settings = get_settings()
    if settings.db_target != "supabase" or command not in DESTRUCTIVE or assume_yes:
        return True

    logger.warning(
        "\n'%s' will DESTROY data in the SHARED Supabase database, not a local "
        "file.\nAnyone else using it right now loses their state.\n",
        command,
    )
    try:
        answer = input("Type 'yes' to continue: ").strip().lower()
    except EOFError:
        # Non-interactive (CI, a piped shell): refuse rather than assume.
        logger.error("Refusing: not interactive. Pass --yes if this is intended.")
        return False
    return answer == "yes"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="app.data.cli")
    parser.add_argument("command", choices=["migrate", "import", "seed", "reset"])
    parser.add_argument(
        "--yes",
        action="store_true",
        help="skip the confirmation prompt when targeting the shared database",
    )
    args = parser.parse_args(argv)

    if not confirm_shared_database(args.command, args.yes):
        return 1

    if args.command in ("migrate", "reset"):
        migrate()
    if args.command in ("import", "reset"):
        run_import()
    if args.command in ("seed", "reset"):
        run_seed()
    return 0


if __name__ == "__main__":
    sys.exit(main())
