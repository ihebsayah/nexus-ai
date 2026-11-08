"""Future approved M1.4 login/privilege checks. Disabled throughout preparation.

Transactions roll back DML/DDL, but a successful identity INSERT consumes a sequence
value even after rollback. Enabling these tests requires approval of that effect.
No fixtures create credentials, roles, seed rows, databases or schema.
"""

import os
import stat
from collections.abc import Iterator
from pathlib import Path

import pytest
import sqlalchemy as sa
from sqlalchemy.engine import URL, Connection, Engine
from sqlalchemy.pool import NullPool

from nexus.persistence import security_admin as admin
from nexus.persistence.migration_settings import bootstrap_environment

pytestmark = [
    pytest.mark.security_runtime,
    pytest.mark.skipif(
        os.environ.get("NEXUS_M14_ALLOW_DB_TESTS") != "1",
        reason="BLOCKED: M1.4 runtime tests need separate approval and deployment",
    ),
]


def connect_engine(user: str, password: str) -> Engine:
    return sa.create_engine(
        URL.create(
            "postgresql+psycopg",
            username=user,
            password=password,
            host="127.0.0.1",
            port=5432,
            database="nexus_ai",
        ),
        poolclass=NullPool,
        echo=False,
        hide_parameters=True,
        connect_args={"connect_timeout": 3},
    )


@pytest.fixture(scope="module")
def runtime_engines() -> Iterator[dict[str, Engine]]:
    if os.environ.get("NEXUS_M14_ACK_TARGET_SCOPE") != "1":
        pytest.fail("Explicit acknowledgement of target-scoped isolation is required")
    if os.environ.get("NEXUS_M14_DATABASE") != "nexus_ai":
        pytest.fail("Exact nexus_ai target is required")
    cluster = os.environ.get("NEXUS_M14_EXPECTED_CLUSTER_ID", "")
    if not cluster.isdecimal():
        pytest.fail("Explicit numeric cluster identity is required")
    runtime_file = Path(os.environ.get("NEXUS_M14_RUNTIME_ENV_FILE", "/nonexistent"))
    bootstrap_file = Path(os.environ.get("NEXUS_M14_ADMIN_ENV_FILE", "/nonexistent"))
    engines: dict[str, Engine] = {}
    try:
        if (
            runtime_file.is_symlink()
            or not runtime_file.is_file()
            or stat.S_IMODE(runtime_file.stat().st_mode) != 0o600
        ):
            pytest.fail("Runtime credential file must be a regular mode0600 file")
        values: dict[str, str] = {}
        for line in runtime_file.read_text().splitlines():
            if not line or line.startswith("#"):
                continue
            key, separator, value = line.partition("=")
            if not separator or key in values:
                pytest.fail("Runtime credential file must contain unique plain entries")
            values[key] = value
        for role in ("app", "tool"):
            password = values.get(f"NEXUS_DB_{role.upper()}_PASSWORD", "")
            if len(password) < 32 or password == "replace-me":
                pytest.fail("Explicit non-placeholder runtime passwords are required")
            engines[role] = connect_engine(f"nexus_{role}", password)
        bootstrap = bootstrap_environment({}, bootstrap_file)
        engines["admin"] = connect_engine("postgres", bootstrap["NEXUS_MIGRATION_PASSWORD"])
        with engines["admin"].connect() as connection, connection.begin():
            connection.exec_driver_sql("SET TRANSACTION READ ONLY")
            admin.identity(connection, cluster)
            roles, relations = admin.inventory(connection)
            if roles != admin.ROLES or not relations >= admin.TABLES | admin.VIEWS:
                pytest.fail("Security deployment is incomplete")
            rows = connection.exec_driver_sql(
                (admin.ROOT / "security/verify_security.sql").read_text()
            ).all()
            if not rows or not all(ok is True for _, ok in rows):
                pytest.fail("Read-only security contract failed before runtime tests")
            enabled = (
                connection.exec_driver_sql(
                    "SELECT rolname FROM pg_roles WHERE rolcanlogin "
                    "AND rolname IN ('nexus_app','nexus_tool')"
                )
                .scalars()
                .all()
            )
            if set(enabled) != {"nexus_app", "nexus_tool"}:
                pytest.fail("Runtime roles must already have approved LOGIN credentials")
        yield engines
    except (OSError, ValueError, sa.exc.SQLAlchemyError):
        pytest.fail("Runtime preflight failed; sensitive database/file details suppressed")
    finally:
        for engine in engines.values():
            engine.dispose()


@pytest.fixture
def tool(runtime_engines: dict[str, Engine]) -> Iterator[Connection]:
    with runtime_engines["tool"].connect() as connection:
        transaction = connection.begin()
        try:
            yield connection
        finally:
            transaction.rollback()


@pytest.fixture
def app(runtime_engines: dict[str, Engine]) -> Iterator[Connection]:
    with runtime_engines["app"].connect() as connection:
        transaction = connection.begin()
        try:
            yield connection
        finally:
            transaction.rollback()


def denied(connection: Connection, statement: str) -> None:
    savepoint = connection.begin_nested()
    try:
        try:
            connection.exec_driver_sql(statement)
        except sa.exc.DBAPIError as error:
            assert getattr(error.orig, "sqlstate", None) == "42501", (
                "Expected insufficient_privilege, not syntax/constraint/target failure"
            )
        else:
            pytest.fail("Forbidden statement unexpectedly succeeded")
    finally:
        savepoint.rollback()


@pytest.mark.parametrize(
    "view,columns",
    [
        ("v_customers", ("id", "name", "email")),
        ("v_orders", ("id", "customer_id", "status", "created_at", "expected_delivery_at")),
        ("v_shipment_events", ("id", "order_id", "event_type", "occurred_at")),
    ],
)
def test_tool_view_projection(tool: Connection, view: str, columns: tuple[str, ...]) -> None:
    # view is a fixed test allowlist value, never caller/model input.
    result = tool.exec_driver_sql(f"SELECT * FROM public.{view} LIMIT 0")
    assert tuple(result.keys()) == columns


@pytest.mark.parametrize("role", ["tool", "app"])
def test_actual_login_defaults(runtime_engines: dict[str, Engine], role: str) -> None:
    with runtime_engines[role].connect() as connection:
        assert connection.exec_driver_sql("SELECT current_user").scalar() == f"nexus_{role}"
        assert connection.exec_driver_sql("SHOW search_path").scalar() == "pg_catalog, public"


@pytest.mark.parametrize(
    "table", ["customers", "orders", "shipment_events", "audit_events", "alembic_version"]
)
def test_tool_base_table_reads_denied(tool: Connection, table: str) -> None:
    denied(tool, f"SELECT * FROM public.{table} LIMIT 0")


@pytest.mark.parametrize(
    "statement",
    [
        "INSERT INTO public.v_customers (name,email) VALUES ('test','test@example.invalid')",
        "UPDATE public.v_orders SET status='pending' WHERE false",
        "DELETE FROM public.v_shipment_events WHERE false",
        "INSERT INTO public.customers(name,email) VALUES ('test','test@example.invalid')",
        "UPDATE public.orders SET status='pending' WHERE false",
        "DELETE FROM public.shipment_events WHERE false",
        "CREATE TABLE public.m14_forbidden_probe(id integer)",
        "CREATE TEMP TABLE m14_forbidden_probe(id integer)",
        "ALTER TABLE public.customers ADD COLUMN m14_forbidden_probe integer",
        "ALTER VIEW public.v_orders OWNER TO nexus_tool",
        "SET ROLE nexus_owner",
        "SET ROLE nexus_app",
        "GRANT nexus_owner TO nexus_tool",
        "GRANT SELECT ON public.customers TO nexus_tool",
        "SELECT * FROM public.audit_events_id_seq",
        "SELECT nextval('public.audit_events_id_seq')",
    ],
)
def test_tool_mutation_and_escalation_denied(tool: Connection, statement: str) -> None:
    denied(tool, statement)


def test_app_audit_insert_without_returning(app: Connection) -> None:
    # Transaction rollback retains no audit row but DOES consume an identity sequence value.
    result = app.exec_driver_sql(
        "INSERT INTO public.audit_events(request_id,event_type,actor_id) "
        "VALUES (gen_random_uuid(),'request','m1.4-security-probe')"
    )
    assert result.rowcount == 1


@pytest.mark.parametrize(
    "statement",
    [
        "SELECT * FROM public.audit_events LIMIT 0",
        "SELECT * FROM public.customers LIMIT 0",
        "SELECT * FROM public.orders LIMIT 0",
        "SELECT * FROM public.shipment_events LIMIT 0",
        "SELECT * FROM public.alembic_version LIMIT 0",
        "SELECT * FROM public.v_customers LIMIT 0",
        "UPDATE public.audit_events SET actor_id='probe' WHERE false",
        "DELETE FROM public.audit_events WHERE false",
        "TRUNCATE public.audit_events",
        "INSERT INTO public.audit_events(request_id,event_type) "
        "VALUES (gen_random_uuid(),'request') RETURNING id",
        "INSERT INTO public.audit_events(id,request_id,event_type) "
        "OVERRIDING SYSTEM VALUE VALUES (999,gen_random_uuid(),'request')",
        "INSERT INTO public.customers(name,email) VALUES ('test','test@example.invalid')",
        "CREATE TABLE public.m14_forbidden_probe(id integer)",
        "CREATE TEMP TABLE m14_forbidden_probe(id integer)",
        "SET ROLE nexus_owner",
        "SET ROLE nexus_tool",
        "GRANT nexus_owner TO nexus_app",
        "SELECT * FROM public.audit_events_id_seq",
        "SELECT nextval('public.audit_events_id_seq')",
    ],
)
def test_app_reads_mutation_and_escalation_denied(app: Connection, statement: str) -> None:
    denied(app, statement)
