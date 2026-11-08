"""Architecture contract and explicitly opted-in disposable PostgreSQL tests.

No database connection or credential-file read occurs during collection. PostgreSQL
fixtures require owner-approved opt-in; reversal has an additional explicit flag.
"""

import os
import re
from collections.abc import Iterator
from io import StringIO
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import URL, Connection, Engine
from sqlalchemy.exc import DBAPIError, IntegrityError

from nexus.persistence.migration_settings import (
    MigrationSettings,
    bootstrap_environment,
    settings_from_environment,
)
from nexus.persistence.models import Base

BACKEND = Path(__file__).resolve().parents[1]
# Independent Architecture 10.2 contract: type and nullable, not model-derived.
COLUMNS = {
    "customers": {
        "id": ("uuid", False),
        "name": ("text", False),
        "email": ("text", False),
        "created_at": ("timestamptz", False),
    },
    "orders": {
        "id": ("uuid", False),
        "customer_id": ("uuid", False),
        "status": ("text", False),
        "created_at": ("timestamptz", False),
        "expected_delivery_at": ("timestamptz", False),
    },
    "shipment_events": {
        "id": ("uuid", False),
        "order_id": ("uuid", False),
        "event_type": ("text", False),
        "occurred_at": ("timestamptz", False),
    },
    "audit_events": {
        "id": ("int8", False),
        "request_id": ("uuid", False),
        "event_type": ("text", False),
        "actor_id": ("text", False),
        "tool_name": ("text", True),
        "args_hash": ("text", True),
        "decision": ("text", True),
        "row_count": ("int4", True),
        "latency_ms": ("int4", True),
        "model": ("text", True),
        "error_code": ("text", True),
        "created_at": ("timestamptz", False),
    },
}
CHECKS = {
    "ck_customers_name_length": "length(btrim(name)) BETWEEN 1 AND 200",
    "ck_customers_email_at": "position('@' in email) > 1",
    "ck_orders_status": (
        "status IN ('pending', 'confirmed', 'in_transit', 'delivered', 'cancelled')"
    ),
    "ck_orders_expected_delivery": "expected_delivery_at >= created_at",
    "ck_shipment_events_event_type": (
        "event_type IN ('created', 'picked_up', 'in_transit', "
        "'out_for_delivery', 'delivered', 'exception')"
    ),
    "ck_audit_events_event_type": (
        "event_type IN ('request', 'tool_decision', 'grounding', 'error')"
    ),
    "ck_audit_events_decision": "decision IN ('allowed', 'denied', 'completed', 'error')",
    "ck_audit_events_row_count": "row_count >= 0",
    "ck_audit_events_latency_ms": "latency_ms >= 0",
}
INDEX_SQL = {
    "customers_email_lower_uidx": (
        "CREATE UNIQUE INDEX customers_email_lower_uidx ON customers (lower(email))"
    ),
    "customers_name_lower_idx": "CREATE INDEX customers_name_lower_idx ON customers (lower(name))",
    "orders_pending_idx": (
        "CREATE INDEX orders_pending_idx ON orders (created_at ASC, id "
        "ASC) WHERE status = 'pending'"
    ),
    "orders_overdue_idx": (
        "CREATE INDEX orders_overdue_idx ON orders (expected_delivery_at "
        "ASC, id ASC) WHERE status NOT IN ('delivered', 'cancelled')"
    ),
    "orders_customer_created_idx": (
        "CREATE INDEX orders_customer_created_idx ON orders (customer_id, created_at DESC, id DESC)"
    ),
    "shipment_events_order_occurred_idx": (
        "CREATE INDEX shipment_events_order_occurred_idx ON "
        "shipment_events (order_id, occurred_at DESC, id DESC)"
    ),
    "audit_events_request_idx": (
        "CREATE INDEX audit_events_request_idx ON audit_events (request_id, created_at ASC)"
    ),
    "audit_events_created_idx": (
        "CREATE INDEX audit_events_created_idx ON audit_events (created_at ASC)"
    ),
}


def normalize(sql: str) -> str:
    return re.sub(r"\s+", " ", sql).strip().lower()


def config(settings: MigrationSettings | None = None, *, read_only: bool = False) -> Config:
    result = Config(str(BACKEND / "alembic.ini"))
    if settings is not None:
        result.attributes["nexus_migration_settings"] = settings
    result.attributes["nexus_read_only"] = read_only
    return result


def test_metadata_columns_defaults_and_identity_match_contract() -> None:
    assert set(Base.metadata.tables) == set(COLUMNS)
    for name, expected in COLUMNS.items():
        table = Base.metadata.tables[name]
        assert set(table.c.keys()) == set(expected)
        assert list(table.primary_key.columns.keys()) == ["id"]
        assert table.primary_key.name == "pk_" + name
        for key, (kind, nullable) in expected.items():
            column = table.c[key]
            assert column.nullable is nullable
            assert column.default is None
            assert column.onupdate is None
            if kind == "uuid":
                assert isinstance(column.type, postgresql.UUID) and column.type.as_uuid
            elif kind == "timestamptz":
                assert isinstance(column.type, sa.DateTime) and column.type.timezone
            elif kind == "text":
                assert isinstance(column.type, sa.Text)
            elif kind == "int8":
                assert isinstance(column.type, sa.BigInteger)
            else:
                assert type(column.type) is sa.Integer
            if key == "created_at":
                assert isinstance(column.server_default, sa.schema.DefaultClause)
                assert str(column.server_default.arg) == "now()"
            elif key == "id" and name != "audit_events":
                assert isinstance(column.server_default, sa.schema.DefaultClause)
                assert str(column.server_default.arg) == "gen_random_uuid()"
            elif name == "audit_events" and key == "actor_id":
                assert isinstance(column.server_default, sa.schema.DefaultClause)
                assert str(column.server_default.arg) == "'local'"
            elif name == "audit_events" and key == "id":
                assert column.identity is not None and column.identity.always
            else:
                assert column.server_default is None


def test_metadata_checks_foreign_keys_and_indexes_match_contract() -> None:
    checks = {
        str(c.name): normalize(str(c.sqltext))
        for t in Base.metadata.tables.values()
        for c in t.constraints
        if isinstance(c, sa.CheckConstraint)
    }
    assert checks == {k: normalize(v) for k, v in CHECKS.items()}
    fks = {
        (
            t.name,
            tuple(c.columns.keys()),
            tuple(e.target_fullname for e in c.elements),
            c.ondelete,
            c.onupdate,
        )
        for t in Base.metadata.tables.values()
        for c in t.foreign_key_constraints
    }
    assert fks == {
        ("orders", ("customer_id",), ("customers.id",), "RESTRICT", None),
        ("shipment_events", ("order_id",), ("orders.id",), "RESTRICT", None),
    }
    dialect = URL.create("postgresql").get_dialect()()
    indexes = {
        str(i.name): normalize(str(sa.schema.CreateIndex(i).compile(dialect=dialect)))
        for t in Base.metadata.tables.values()
        for i in t.indexes
    }
    assert indexes == {k: normalize(v) for k, v in INDEX_SQL.items()}


def test_alembic_has_one_initial_head_and_offline_schema_without_credentials() -> None:
    cfg = config()
    script = ScriptDirectory.from_config(cfg)
    assert script.get_heads() == ["0001_initial_schema"]
    revision = script.get_revision("0001_initial_schema")
    assert revision is not None and revision.down_revision is None
    output = StringIO()
    cfg.output_buffer = output
    command.upgrade(cfg, "head", sql=True)
    sql = output.getvalue()
    for table in COLUMNS:
        assert "CREATE TABLE " + table in sql
    assert sql.count("CREATE TABLE ") == 5  # four tables plus Alembic bookkeeping
    for name in INDEX_SQL:
        assert name in sql
    assert "GENERATED ALWAYS AS IDENTITY" in sql
    for expression in CHECKS.values():
        assert normalize(expression) in normalize(sql)
    assert (
        "CREATE ROLE" not in sql and "CREATE VIEW" not in sql and "INSERT INTO customers" not in sql
    )


@pytest.fixture(scope="module")
def pg_settings() -> MigrationSettings:
    if os.environ.get("NEXUS_M13_ALLOW_DB_TESTS") != "1":
        pytest.skip("BLOCKED: owner-approved disposable PostgreSQL test opt-in required")
    values = dict(os.environ)
    if "NEXUS_M13_ENV_FILE" in values:
        values = bootstrap_environment(values, Path(values["NEXUS_M13_ENV_FILE"]))
    return settings_from_environment(values)


@pytest.fixture(scope="module")
def pg_engine(pg_settings: MigrationSettings) -> Iterator[Engine]:
    engine = sa.create_engine(
        URL.create(
            "postgresql+psycopg",
            username=pg_settings.user,
            password=pg_settings.password,
            host=pg_settings.host,
            port=pg_settings.port,
            database=pg_settings.database,
        ),
        hide_parameters=True,
        connect_args={"connect_timeout": 3},
    )
    try:
        with engine.connect() as connection:
            actual = connection.execute(
                sa.text(
                    "SELECT current_database(), shobj_description(oid, 'pg_database') "
                    "FROM pg_database WHERE datname=current_database()"
                )
            ).one()
            assert tuple(actual) == ("nexus_m13_test", "nexus-ai:m1.3-disposable")
            inspector = sa.inspect(connection)
            assert set(inspector.get_table_names(schema="public")) <= set(COLUMNS) | {
                "alembic_version"
            }
            assert inspector.get_view_names(schema="public") == []
        # The opted-in fixture owns the upgrade, so individually selected tests
        # do not rely on pytest function ordering or reuse of a pre-migrated DB.
        command.upgrade(config(pg_settings), "head")
        yield engine
    finally:
        engine.dispose()


@pytest.fixture()
def transaction(pg_engine: Engine) -> Iterator[Connection]:
    with pg_engine.connect() as connection:
        outer = connection.begin()
        try:
            yield connection
        finally:
            outer.rollback()


@pytest.mark.postgres
def test_postgres_upgrade_catalog_and_model_agreement(
    pg_engine: Engine, pg_settings: MigrationSettings
) -> None:
    with pg_engine.connect() as connection:
        inspector = sa.inspect(connection)
        assert set(inspector.get_table_names(schema="public")) == set(COLUMNS) | {"alembic_version"}
        assert inspector.get_view_names(schema="public") == []
        assert set(inspector.get_sequence_names(schema="public")) == {"audit_events_id_seq"}
        for table in COLUMNS:
            assert inspector.get_pk_constraint(table, schema="public")["constrained_columns"] == [
                "id"
            ]
            assert inspector.get_unique_constraints(table, schema="public") == []
        actual_fks = {
            (
                table,
                tuple(fk["constrained_columns"]),
                fk["referred_table"],
                tuple(fk["referred_columns"]),
                fk["options"].get("ondelete"),
            )
            for table in COLUMNS
            for fk in inspector.get_foreign_keys(table, schema="public")
        }
        assert actual_fks == {
            ("orders", ("customer_id",), "customers", ("id",), "RESTRICT"),
            ("shipment_events", ("order_id",), "orders", ("id",), "RESTRICT"),
        }
        definitions = {
            index["name"]: index
            for table in COLUMNS
            for index in inspector.get_indexes(table, schema="public")
        }
        assert set(definitions) == set(INDEX_SQL)
        for name, index in definitions.items():
            assert bool(index["unique"]) == (name == "customers_email_lower_uidx")
        for name, column in [
            ("customers_email_lower_uidx", "email"),
            ("customers_name_lower_idx", "name"),
        ]:
            assert definitions[name]["column_names"] == [None]
            assert definitions[name]["expressions"] == ["lower(" + column + ")"]
        expected_keys = {
            "orders_pending_idx": ["created_at", "id"],
            "orders_overdue_idx": ["expected_delivery_at", "id"],
            "orders_customer_created_idx": ["customer_id", "created_at", "id"],
            "shipment_events_order_occurred_idx": ["order_id", "occurred_at", "id"],
            "audit_events_request_idx": ["request_id", "created_at"],
            "audit_events_created_idx": ["created_at"],
        }
        for name, keys in expected_keys.items():
            assert definitions[name]["column_names"] == keys
            descending = {"created_at", "id"} if name == "orders_customer_created_idx" else set()
            if name == "shipment_events_order_occurred_idx":
                descending = {"occurred_at", "id"}
            for key in keys:
                assert ("desc" in definitions[name].get("column_sorting", {}).get(key, ())) == (
                    key in descending
                )
        for name in INDEX_SQL:
            predicate = definitions[name].get("dialect_options", {}).get("postgresql_where")
            if name == "orders_pending_idx":
                assert predicate is not None
                cleaned = re.sub(r"[\s()]", "", predicate.replace("::text", "")).lower()
                assert cleaned == "status='pending'"
            elif name == "orders_overdue_idx":
                assert predicate is not None
                cleaned = re.sub(r"[\s()]", "", predicate.replace("::text", "")).lower()
                assert cleaned in {
                    "status<>allarray['delivered','cancelled']",
                    "statusnotin'delivered','cancelled'",
                }
            else:
                assert predicate is None
        assert connection.execute(
            sa.text(
                "SELECT nspname FROM pg_namespace WHERE nspname NOT LIKE 'pg_%' "
                "AND nspname <> 'information_schema'"
            )
        ).scalars().all() == ["public"]
        columns = connection.execute(
            sa.text(
                "SELECT "
                "c.table_name,c.column_name,t.typname,c.is_nullable,c.is_identity,"
                "c.identity_generation FROM information_schema.columns c JOIN "
                "pg_type t ON t.typname=c.udt_name WHERE c.table_schema='public' "
                "AND c.table_name<>'alembic_version'"
            )
        ).all()
        actual: dict[str, dict[str, tuple[str, bool]]] = {name: {} for name in COLUMNS}
        for table, key, kind, nullable, identity, generation in columns:
            actual[table][key] = (kind, nullable == "YES")
            if (table, key) == ("audit_events", "id"):
                assert identity == "YES" and generation == "ALWAYS"
        assert actual == COLUMNS
        checks = {
            name
            for (name,) in connection.execute(
                sa.text(
                    "SELECT conname FROM pg_constraint WHERE contype='c' AND "
                    "connamespace='public'::regnamespace"
                )
            )
        }
        assert checks == set(CHECKS)
        indexes = {
            name
            for (name,) in connection.execute(
                sa.text("SELECT indexname FROM pg_indexes WHERE schemaname='public'")
            )
        }
        assert indexes == set(INDEX_SQL) | {"pk_" + name for name in COLUMNS} | {
            "alembic_version_pkc"
        }
        assert (
            compare_metadata(
                MigrationContext.configure(
                    connection, opts={"compare_type": True, "compare_server_default": True}
                ),
                Base.metadata,
            )
            == []
        )
    command.check(config(pg_settings, read_only=True))


@pytest.mark.postgres
@pytest.mark.parametrize(
    "statement",
    [
        "INSERT INTO customers(name,email) VALUES ('   ','unit@example.invalid')",
        "INSERT INTO customers(name,email) VALUES (repeat('x',201),'unit@example.invalid')",
        "INSERT INTO customers(name,email) VALUES ('unit','invalid')",
        "INSERT INTO customers(name,email) VALUES (NULL,'unit@example.invalid')",
        (
            "INSERT INTO orders(customer_id,status,expected_delivery_at) "
            "VALUES (gen_random_uuid(),'pending',now())"
        ),
        (
            "INSERT INTO orders(customer_id,status,expected_delivery_at) "
            "SELECT id,'unknown',now()+interval '1 day' FROM customers"
        ),
        (
            "INSERT INTO "
            "orders(customer_id,status,created_at,expected_delivery_at) "
            "SELECT id,'pending',now(),now()-interval '1 day' FROM customers"
        ),
        (
            "INSERT INTO shipment_events(order_id,event_type,occurred_at) "
            "VALUES (gen_random_uuid(),'created',now())"
        ),
        (
            "INSERT INTO shipment_events(order_id,event_type,occurred_at) "
            "SELECT id,'unknown',now() FROM orders"
        ),
        "INSERT INTO audit_events(request_id,event_type) VALUES (gen_random_uuid(),'unknown')",
        (
            "INSERT INTO audit_events(request_id,event_type,decision) VALUES "
            "(gen_random_uuid(),'request','unknown')"
        ),
        (
            "INSERT INTO audit_events(request_id,event_type,row_count) VALUES "
            "(gen_random_uuid(),'request',-1)"
        ),
        (
            "INSERT INTO audit_events(request_id,event_type,latency_ms) "
            "VALUES (gen_random_uuid(),'request',-1)"
        ),
    ],
)
def test_postgres_rejects_invalid_records(transaction: Connection, statement: str) -> None:
    transaction.execute(
        sa.text("INSERT INTO customers(name,email) VALUES ('unit','unit@example.invalid')")
    )
    transaction.execute(
        sa.text(
            "INSERT INTO orders(customer_id,status,expected_delivery_at) "
            "SELECT id,'pending',now()+interval '1 day' FROM customers"
        )
    )
    with pytest.raises(IntegrityError), transaction.begin_nested():
        transaction.execute(sa.text(statement))


@pytest.mark.postgres
def test_postgres_defaults_case_insensitive_unique_and_restrict(transaction: Connection) -> None:
    customer = transaction.execute(
        sa.text("INSERT INTO customers(name,email) VALUES ('unit','unit@') RETURNING id,created_at")
    ).one()
    assert customer[1].tzinfo is not None
    with pytest.raises(IntegrityError), transaction.begin_nested():
        transaction.execute(sa.text("INSERT INTO customers(name,email) VALUES ('unit','UNIT@')"))
    order = transaction.execute(
        sa.text(
            "INSERT INTO orders(customer_id,status,expected_delivery_at) "
            "VALUES (:id,'pending',now()+interval '1 day') RETURNING id"
        ),
        {"id": customer[0]},
    ).scalar_one()
    transaction.execute(
        sa.text(
            "INSERT INTO shipment_events(order_id,event_type,occurred_at) "
            "VALUES (:id,'created',now())"
        ),
        {"id": order},
    )
    for statement, key in [
        ("DELETE FROM customers WHERE id=:id", customer[0]),
        ("DELETE FROM orders WHERE id=:id", order),
    ]:
        with pytest.raises(IntegrityError), transaction.begin_nested():
            transaction.execute(sa.text(statement), {"id": key})
    audit = transaction.execute(
        sa.text(
            "INSERT INTO "
            "audit_events(request_id,event_type,decision,row_count,latency_ms)"
            " VALUES (:request,'request',NULL,NULL,NULL) RETURNING "
            "id,actor_id,created_at"
        ),
        {"request": uuid4()},
    ).one()
    assert (
        isinstance(audit[0], int)
        and audit[0] > 0
        and audit[1] == "local"
        and audit[2].tzinfo is not None
    )
    with pytest.raises(DBAPIError) as rejected, transaction.begin_nested():
        transaction.execute(
            sa.text(
                "INSERT INTO audit_events(id,request_id,event_type) VALUES "
                "(999,gen_random_uuid(),'request')"
            )
        )

    assert getattr(rejected.value.orig, "sqlstate", None) == "428C9"


@pytest.mark.postgres
@pytest.mark.parametrize(
    "kind,value",
    [("order", value) for value in ("pending", "confirmed", "in_transit", "delivered", "cancelled")]
    + [
        ("event", value)
        for value in (
            "created",
            "picked_up",
            "in_transit",
            "out_for_delivery",
            "delivered",
            "exception",
        )
    ]
    + [("audit", value) for value in ("request", "tool_decision", "grounding", "error")]
    + [("decision", value) for value in ("allowed", "denied", "completed", "error")],
)
def test_postgres_accepts_documented_values(transaction: Connection, kind: str, value: str) -> None:
    customer = transaction.execute(
        sa.text(
            "INSERT INTO customers(name,email) VALUES ('unit','unit@example.invalid') RETURNING id"
        )
    ).scalar_one()
    order = transaction.execute(
        sa.text(
            "INSERT INTO orders(customer_id,status,expected_delivery_at) "
            "VALUES (:customer,'pending',now()+interval '1 day') RETURNING id"
        ),
        {"customer": customer},
    ).scalar_one()
    if kind == "order":
        transaction.execute(
            sa.text("UPDATE orders SET status=:value WHERE id=:id"), {"value": value, "id": order}
        )
    elif kind == "event":
        transaction.execute(
            sa.text(
                "INSERT INTO shipment_events(order_id,event_type,occurred_at) "
                "VALUES (:id,:value,now())"
            ),
            {"id": order, "value": value},
        )
    elif kind == "audit":
        transaction.execute(
            sa.text(
                "INSERT INTO audit_events(request_id,event_type) VALUES (gen_random_uuid(),:value)"
            ),
            {"value": value},
        )
    else:
        transaction.execute(
            sa.text(
                "INSERT INTO audit_events(request_id,event_type,decision) "
                "VALUES (gen_random_uuid(),'request',:value)"
            ),
            {"value": value},
        )


@pytest.mark.postgres
def test_postgres_accepts_documented_boundaries(transaction: Connection) -> None:
    customer = transaction.execute(
        sa.text("INSERT INTO customers(name,email) VALUES (repeat('x',200),'unit@') RETURNING id")
    ).scalar_one()
    transaction.execute(
        sa.text(
            "INSERT INTO orders(customer_id,status,created_at,expected_delivery_at) "
            "VALUES (:customer,'pending',now(),now())"
        ),
        {"customer": customer},
    )
    transaction.execute(
        sa.text(
            "INSERT INTO audit_events(request_id,event_type,row_count,latency_ms) "
            "VALUES (gen_random_uuid(),'request',0,0)"
        )
    )


@pytest.mark.postgres
def test_postgres_approved_downgrade_and_reupgrade(
    pg_engine: Engine, pg_settings: MigrationSettings
) -> None:
    if os.environ.get("NEXUS_M13_ALLOW_TEST_DOWNGRADE") != "1":
        pytest.skip("BLOCKED: explicit owner-approved test downgrade opt-in required")
    with pg_engine.connect() as connection:
        for table in COLUMNS:
            assert (
                connection.scalar(
                    sa.select(sa.func.count()).select_from(Base.metadata.tables[table])
                )
                == 0
            )
    command.downgrade(config(pg_settings), "base")
    with pg_engine.connect() as connection:
        assert set(sa.inspect(connection).get_table_names(schema="public")) <= {"alembic_version"}
        assert connection.execute(sa.text("SELECT count(*) FROM alembic_version")).scalar_one() == 0
    command.upgrade(config(pg_settings), "head")
    with pg_engine.connect() as connection:
        assert set(sa.inspect(connection).get_table_names(schema="public")) == set(COLUMNS) | {
            "alembic_version"
        }
        assert (
            connection.execute(sa.text("SELECT version_num FROM alembic_version")).scalar_one()
            == "0001_initial_schema"
        )
    command.check(config(pg_settings, read_only=True))
