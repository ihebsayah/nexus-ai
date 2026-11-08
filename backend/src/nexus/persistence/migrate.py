"""Narrow Alembic command wrapper with explicit test-only online access."""

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from nexus.persistence.migration_settings import (
    TEST_DATABASE,
    MigrationSafetyError,
    bootstrap_environment,
    settings_from_environment,
)

BACKEND_ROOT = Path(__file__).resolve().parents[3]
OFFLINE_ACTIONS = {"heads", "history", "sql"}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action", choices=["heads", "history", "sql", "current", "check", "upgrade", "downgrade"]
    )
    parser.add_argument("--database", choices=[TEST_DATABASE], default=TEST_DATABASE)
    parser.add_argument(
        "--env-file", type=Path, help="Explicit bootstrap file, online commands only"
    )
    args = parser.parse_args(argv)
    try:
        from alembic import command
        from alembic.config import Config
        from alembic.util.exc import CommandError
        from sqlalchemy.exc import SQLAlchemyError
    except ImportError:
        print(
            "BLOCKED: approved SQLAlchemy/Alembic/psycopg installation is required.",
            file=sys.stderr,
        )
        return 2
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    try:
        if args.action not in OFFLINE_ACTIONS:
            environment = dict(os.environ)
            if args.env_file is not None:
                environment = bootstrap_environment(environment, args.env_file)
            environment["NEXUS_MIGRATION_DATABASE"] = args.database
            settings = settings_from_environment(environment)
            config.attributes["nexus_migration_settings"] = settings
            config.attributes["nexus_read_only"] = args.action in {"current", "check"}
        if args.action == "heads":
            command.heads(config)
        elif args.action == "history":
            command.history(config)
        elif args.action == "sql":
            command.upgrade(config, "head", sql=True)
        elif args.action == "current":
            command.current(config)
        elif args.action == "check":
            command.check(config)
        elif args.action == "upgrade":
            command.upgrade(config, "head")
        else:
            command.downgrade(config, "base")
    except MigrationSafetyError as error:
        print(str(error), file=sys.stderr)
        return 2
    except (CommandError, SQLAlchemyError, OSError):
        # Do not serialize driver exceptions, connection parameters or URLs.
        print(
            "Migration command failed; details suppressed to protect credentials.", file=sys.stderr
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
