"""Future approval-only provisioning; importing this module never creates secrets."""

import argparse
import os
import secrets
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

import sqlalchemy as sa
from psycopg import sql
from sqlalchemy.engine import URL, Connection
from sqlalchemy.pool import NullPool

from nexus.persistence.migration_settings import MigrationSafetyError, bootstrap_environment
from nexus.persistence.security_admin import ROOT, identity

PROJECT = ROOT.parent
RUNTIME_FILE = PROJECT / "infra/.env.runtime"


def disabled_policy(connection: Connection, cluster: str) -> None:
    identity(connection, cluster)
    rows = connection.exec_driver_sql((ROOT / "security/verify_security.sql").read_text()).all()
    if not rows or any(ok is not True for _, ok in rows):
        raise MigrationSafetyError("Security policy must pass before credential provisioning.")
    if (
        connection.exec_driver_sql(
            "SELECT count(*) FROM pg_roles WHERE rolname IN ('nexus_app', 'nexus_tool') "
            "AND NOT rolcanlogin"
        ).scalar()
        != 2
    ):
        raise MigrationSafetyError("Both runtime roles must already be NOLOGIN.")
    if connection.exec_driver_sql(
        "SELECT EXISTS (SELECT 1 FROM pg_stat_activity "
        "WHERE usename IN ('nexus_app', 'nexus_tool'))"
    ).scalar():
        raise MigrationSafetyError("Existing runtime sessions require separate investigation.")


def suppress_secret_logging(connection: Connection) -> None:
    # Fail closed on extensions/preload hooks whose logging we have not reviewed.
    if connection.exec_driver_sql(
        "SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname <> 'plpgsql') OR "
        "current_setting('shared_preload_libraries') <> '' OR "
        "current_setting('session_preload_libraries') <> '' OR "
        "current_setting('local_preload_libraries') <> ''"
    ).scalar():
        raise MigrationSafetyError("Unreviewed extensions/preload hooks block secret operations.")
    for statement in (
        "SET LOCAL log_statement = 'none'",
        "SET LOCAL log_duration = off",
        "SET LOCAL log_min_duration_statement = -1",
        "SET LOCAL log_min_duration_sample = -1",
        "SET LOCAL log_statement_sample_rate = 0",
        "SET LOCAL log_transaction_sample_rate = 0",
        "SET LOCAL log_min_error_statement = 'panic'",
        "SET LOCAL log_parameter_max_length = 0",
        "SET LOCAL log_parameter_max_length_on_error = 0",
        "SET LOCAL debug_print_parse = off",
        "SET LOCAL debug_print_rewritten = off",
        "SET LOCAL debug_print_plan = off",
        "SET LOCAL password_encryption = 'scram-sha-256'",
    ):
        connection.exec_driver_sql(statement)


def write_exclusive_credentials() -> tuple[str, str]:
    """Call only after approval/preflight; never overwrite or display secret values."""
    if RUNTIME_FILE.parent.is_symlink():
        raise MigrationSafetyError("Runtime credential directory must not be a symlink.")
    result = subprocess.run(
        ["git", "check-ignore", "--quiet", "--", str(RUNTIME_FILE)],
        cwd=PROJECT,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise MigrationSafetyError("Runtime credential path must be excluded from Git.")
    app, tool = secrets.token_urlsafe(48), secrets.token_urlsafe(48)
    descriptor = os.open(RUNTIME_FILE, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w") as handle:
        os.fchmod(handle.fileno(), 0o600)
        handle.write(
            "NEXUS_DB_HOST=127.0.0.1\nNEXUS_DB_PORT=5432\nNEXUS_DB_NAME=nexus_ai\n"
            f"NEXUS_DB_APP=nexus_app\nNEXUS_DB_APP_PASSWORD={app}\n"
            f"NEXUS_DB_TOOL=nexus_tool\nNEXUS_DB_TOOL_PASSWORD={tool}\n"
        )
        handle.flush()
        os.fsync(handle.fileno())
    return app, tool


def provision(env_file: Path, cluster: str) -> None:
    password = bootstrap_environment({}, env_file)["NEXUS_MIGRATION_PASSWORD"]
    if password == "replace-me":
        raise MigrationSafetyError("Placeholder bootstrap password is forbidden.")
    engine = sa.create_engine(
        URL.create(
            "postgresql+psycopg",
            username="postgres",
            password=password,
            host="127.0.0.1",
            port=5432,
            database="nexus_ai",
        ),
        poolclass=NullPool,
        hide_parameters=True,
        echo=False,
        connect_args={"connect_timeout": 3},
    )
    try:
        with engine.connect() as connection, connection.begin():
            disabled_policy(connection, cluster)
            suppress_secret_logging(connection)
            app, tool = write_exclusive_credentials()
            # Utility PASSWORD clauses need SQL composition, not ordinary DML binds.
            # Use the driver directly so SQLAlchemy cannot include secret SQL in errors.
            driver = connection.connection.driver_connection
            if driver is None:
                raise MigrationSafetyError(
                    "Driver unavailable; retain credential file and inspect."
                )
            with driver.cursor() as cursor:
                for role, value in (("nexus_app", app), ("nexus_tool", tool)):
                    cursor.execute(
                        sql.SQL("ALTER ROLE {} PASSWORD {} LOGIN").format(
                            sql.Identifier(role), sql.Literal(value)
                        )
                    )
        print("Runtime credentials provisioned; run separately approved authenticated tests.")
    finally:
        engine.dispose()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["provision"])
    parser.add_argument("--database", choices=["nexus_ai"], required=True)
    parser.add_argument("--expected-cluster-id", required=True)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--runtime-env-file", type=Path, required=True)
    parser.add_argument("--acknowledge-target-scope", action="store_true")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    try:
        if not args.execute or not args.acknowledge_target_scope:
            raise MigrationSafetyError(
                "Separate approval, --execute and scope acknowledgement required."
            )
        if not args.expected_cluster_id.isdecimal():
            raise MigrationSafetyError("Expected cluster identifier must be numeric.")
        if args.runtime_env_file.absolute() != RUNTIME_FILE:
            raise MigrationSafetyError(
                "Only the fixed ignored infra/.env.runtime path is supported."
            )
        if RUNTIME_FILE.exists() or RUNTIME_FILE.is_symlink():
            raise MigrationSafetyError(
                "Credential path already exists; never overwrite or retry blindly."
            )
        provision(args.env_file, args.expected_cluster_id)
        return 0
    except MigrationSafetyError as error:
        print(f"BLOCKED: {error}", file=sys.stderr)
        return 2
    except Exception:
        # Deliberately do not expose exception text, SQL, driver state or password values.
        print(
            "FAILED: details suppressed. Retain any credential file; inspect roles read-only. "
            "A lost commit acknowledgement requires investigation before retry.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
