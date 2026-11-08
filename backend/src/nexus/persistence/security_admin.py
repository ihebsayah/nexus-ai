"""Explicit, approval-gated M1.4 administration; never called by the application."""

import argparse
import hashlib
import json
import sys
from collections.abc import Sequence
from pathlib import Path

import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.util.exc import CommandError
from sqlalchemy.engine import URL, Connection
from sqlalchemy.pool import NullPool

from nexus.persistence.migration_settings import MigrationSafetyError, bootstrap_environment
from nexus.persistence.models import Base

ROOT = Path(__file__).resolve().parents[3]
INITIAL_HASH = "b40e0c557e23f3484b817f44c7ea686bbf5d455e0a654ffee89a44ec0622124c"
ROLES = {"nexus_owner", "nexus_app", "nexus_tool"}
TABLES = {"customers", "orders", "shipment_events", "audit_events", "alembic_version"}
VIEWS = {"v_customers", "v_orders", "v_shipment_events"}


def frozen_config() -> Config:
    """Allow only the reviewed initial source, not future heads or downgrades."""
    revision = ROOT / "migrations/versions/0001_initial_schema.py"
    if hashlib.sha256(revision.read_bytes()).hexdigest() != INITIAL_HASH:
        raise MigrationSafetyError("Frozen initial revision hash changed; stop for review.")
    if list(revision.parent.glob("*.py")) != [revision]:
        raise MigrationSafetyError("Initial-only deployment requires exactly one revision.")
    config = Config()
    config.set_main_option("script_location", str(ROOT / "security/migrations"))
    config.set_main_option("version_locations", str(revision.parent))
    config.set_main_option("path_separator", "os")
    return config


def identity(connection: Connection, expected: str) -> None:
    actual = connection.exec_driver_sql(
        "SELECT current_database(), session_user, current_user, "
        "current_setting('server_version_num')::int / 10000, "
        "(SELECT system_identifier::text FROM pg_control_system()), "
        "(SELECT rolsuper FROM pg_roles WHERE rolname = current_user), "
        "(SELECT pg_get_userbyid(datdba) FROM pg_database "
        "WHERE datname = current_database())"
    ).one()
    if tuple(actual) != ("nexus_ai", "postgres", "postgres", 16, expected, True, "postgres"):
        raise MigrationSafetyError("Target/cluster/bootstrap identity mismatch.")
    connection.exec_driver_sql("SET LOCAL search_path = pg_catalog, public")
    connection.exec_driver_sql("SET LOCAL lock_timeout = '5s'")
    connection.exec_driver_sql("SET LOCAL statement_timeout = '30s'")


def inventory(connection: Connection) -> tuple[set[str], set[str]]:
    roles = set(
        connection.exec_driver_sql(
            "SELECT rolname FROM pg_roles WHERE rolname IN "
            "('nexus_owner', 'nexus_app', 'nexus_tool')"
        ).scalars()
    )
    relations = set(
        connection.exec_driver_sql(
            "SELECT relname FROM pg_class WHERE relnamespace = 'public'::regnamespace "
            "AND relkind IN ('r', 'v', 'm', 'f', 'p')"
        ).scalars()
    )
    return roles, relations


def empty_target(connection: Connection) -> None:
    if connection.exec_driver_sql(
        "SELECT EXISTS (SELECT 1 FROM pg_class WHERE relnamespace = 'public'::regnamespace) "
        "OR EXISTS (SELECT 1 FROM pg_proc WHERE pronamespace = 'public'::regnamespace) "
        "OR EXISTS (SELECT 1 FROM pg_type WHERE typnamespace = 'public'::regnamespace) "
        "OR EXISTS (SELECT 1 FROM pg_namespace WHERE nspname NOT LIKE 'pg_%' "
        "AND nspname NOT IN ('public', 'information_schema')) "
        "OR EXISTS (SELECT 1 FROM pg_default_acl) "
        "OR EXISTS (SELECT 1 FROM pg_roles WHERE rolname IN "
        "('nexus_owner', 'nexus_app', 'nexus_tool')) "
        "OR EXISTS (SELECT 1 FROM pg_database WHERE datname = current_database() "
        "AND datacl IS NOT NULL) "
        "OR EXISTS (SELECT 1 FROM pg_namespace n WHERE nspname = 'public' AND "
        "(pg_get_userbyid(nspowner) <> 'pg_database_owner' OR nspacl::text IS DISTINCT FROM "
        "'{pg_database_owner=UC/pg_database_owner,=U/pg_database_owner}'))"
    ).scalar():
        raise MigrationSafetyError("Initial target is not the exact fresh empty baseline.")


def schema_fingerprint(connection: Connection) -> str:
    # No row data or secrets: deparsed schema expressions, names, types and identity only.
    rows = connection.exec_driver_sql(
        "SELECT 'column', c.relname, a.attname, "
        "format_type(a.atttypid, a.atttypmod) || ':' || a.attnotnull::text || ':' || "
        "a.attidentity::text || ':' || coalesce(pg_get_expr(d.adbin,d.adrelid), '') "
        "FROM pg_class c JOIN pg_attribute a ON a.attrelid=c.oid "
        "LEFT JOIN pg_attrdef d ON d.adrelid=c.oid AND d.adnum=a.attnum "
        "WHERE c.relnamespace='public'::regnamespace AND c.relkind='r' "
        "AND a.attnum>0 AND NOT a.attisdropped UNION ALL "
        "SELECT 'constraint', c.relname, x.conname, pg_get_constraintdef(x.oid) "
        "FROM pg_constraint x JOIN pg_class c ON c.oid=x.conrelid "
        "WHERE c.relnamespace='public'::regnamespace UNION ALL "
        "SELECT 'index', tablename, indexname, indexdef FROM pg_indexes "
        "WHERE schemaname='public' ORDER BY 1,2,3,4"
    ).all()
    return hashlib.sha256(json.dumps([list(row) for row in rows]).encode()).hexdigest()


def initial_contract(connection: Connection) -> None:
    """Compare types/defaults/indexes/FKs plus named checks against frozen metadata."""
    if set(sa.inspect(connection).get_table_names(schema="public")) != TABLES:
        raise MigrationSafetyError("Initial table inventory differs.")
    if connection.exec_driver_sql(
        "SELECT version_num FROM public.alembic_version"
    ).scalars().all() != ["0001_initial_schema"]:
        raise MigrationSafetyError("Initial revision differs.")
    context = MigrationContext.configure(
        connection,
        opts={
            "compare_type": True,
            "compare_server_default": True,
        },
    )
    differences = compare_metadata(context, Base.metadata)
    # Alembic excludes its own tracking table from comparison.
    if differences:
        raise MigrationSafetyError("Initial metadata differs; stop for schema review.")
    inspector = sa.inspect(connection)
    for table in Base.metadata.sorted_tables:
        expected = {c.name for c in table.constraints if isinstance(c, sa.CheckConstraint)}
        observed = {c["name"] for c in inspector.get_check_constraints(table.name, schema="public")}
        if observed != expected:
            raise MigrationSafetyError("Initial check constraint inventory differs.")
        if connection.execute(sa.select(sa.exists().select_from(table))).scalar():
            raise MigrationSafetyError(
                "Application tables must remain empty before security apply."
            )


def run_online(args: argparse.Namespace) -> int:
    if not args.expected_cluster_id or not args.expected_cluster_id.isdecimal():
        raise MigrationSafetyError("An explicit numeric expected cluster identifier is required.")
    if args.env_file is None:
        raise MigrationSafetyError("An explicit bootstrap credential file is required.")
    environment = bootstrap_environment({}, args.env_file)
    password = environment["NEXUS_MIGRATION_PASSWORD"]
    if password == "replace-me":
        raise MigrationSafetyError("Placeholder credentials are forbidden.")
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
        with engine.connect() as connection:
            with connection.begin():
                connection.exec_driver_sql("SET TRANSACTION READ ONLY")
                identity(connection, args.expected_cluster_id)
                roles, relations = inventory(connection)
                if args.action == "check":
                    if not roles and not relations:
                        print("NOT_DEPLOYED: nexus_ai is empty and designated roles are absent.")
                        return 2
                    if roles != ROLES or not relations >= (TABLES | VIEWS):
                        raise MigrationSafetyError(
                            "Partial/conflicting security deployment; inspect read-only."
                        )
                    rows = connection.exec_driver_sql(
                        (ROOT / "security/verify_security.sql").read_text()
                    ).all()
                    for name, ok in rows:
                        print(f"{name}: {'PASS' if ok is True else 'FAIL'}")
                    return 0 if rows and all(ok is True for _, ok in rows) else 1
                if roles:
                    raise MigrationSafetyError("Existing designated role conflicts; stop.")
                if args.action == "initial-apply":
                    empty_target(connection)
                if args.action == "apply":
                    initial_contract(connection)
                    if not args.expected_schema_sha256 or (
                        schema_fingerprint(connection) != args.expected_schema_sha256
                    ):
                        raise MigrationSafetyError(
                            "Frozen deployment catalog fingerprint mismatch."
                        )
            if not args.execute or args.database != "nexus_ai":
                raise MigrationSafetyError(
                    "Mutation requires --execute --database nexus_ai and owner approval."
                )
            if args.action == "initial-apply":
                with connection.begin():
                    identity(connection, args.expected_cluster_id)
                    empty_target(connection)
                    config = frozen_config()
                    config.attributes["connection"] = connection
                    config.attributes["initial_only"] = True
                    command.upgrade(config, "0001_initial_schema")
                    initial_contract(connection)
                    print("Initial frozen schema SHA256:", schema_fingerprint(connection))
            else:
                # Script owns BEGIN/COMMIT: driver autocommit avoids an outer transaction.
                connection.execution_options(isolation_level="AUTOCOMMIT")
                connection.exec_driver_sql((ROOT / "security/apply_security.sql").read_text())
            print("Deployment command completed; run separate read-only check before activation.")
            return 0
    finally:
        engine.dispose()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["plan", "render", "check", "initial-apply", "apply"])
    parser.add_argument("--database", choices=["nexus_ai"])
    parser.add_argument("--expected-cluster-id")
    parser.add_argument("--expected-schema-sha256")
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    try:
        frozen_config()
        if args.action == "plan":
            print(
                "PREPARATION ONLY: empty-target initial-apply -> apply disabled roles/security "
                "-> read-only check -> separately reviewed credentials/activation -> runtime tests."
            )
            print("Never downgrade/drop/reset. Credentials and LOGIN are not implemented here.")
            return 0
        if args.action == "render":
            print((ROOT / "security/apply_security.sql").read_text(), end="")
            return 0
        if args.action != "check" and not args.execute:
            raise MigrationSafetyError(
                "No connection: future mutation requires explicit --execute."
            )
        return run_online(args)
    except MigrationSafetyError as error:
        print(f"BLOCKED: {error}", file=sys.stderr)
        return 2
    except (sa.exc.SQLAlchemyError, CommandError, OSError, ValueError):
        print(
            "FAILED: sensitive database/file details suppressed; inspect state read-only.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
