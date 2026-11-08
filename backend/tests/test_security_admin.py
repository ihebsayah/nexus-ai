"""M1.4 guard behavior and policy source checks; no database is needed."""

import argparse
from pathlib import Path
from typing import cast
from unittest.mock import MagicMock

import pytest
import sqlalchemy as sa
from sqlalchemy.engine import Connection

from nexus.persistence import security_admin as admin
from nexus.persistence.migration_settings import MigrationSafetyError


def forbid(*args: object, **kwargs: object) -> None:
    pytest.fail("Offline/blocked invocation tried credential or database access")


@pytest.mark.parametrize("action", ["plan", "render"])
def test_offline_never_reads_credentials_or_connects(
    action: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(admin, "bootstrap_environment", forbid)
    monkeypatch.setattr(sa, "create_engine", forbid)
    assert admin.main([action]) == 0
    assert capsys.readouterr().out


@pytest.mark.parametrize("action", ["initial-apply", "apply"])
def test_missing_execution_flag_stops_before_secret_access(
    action: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(admin, "bootstrap_environment", forbid)
    monkeypatch.setattr(sa, "create_engine", forbid)
    assert admin.main([action]) == 2


@pytest.mark.parametrize("cluster", [None, "", "not-numeric"])
def test_invalid_cluster_stops_before_secret_access(
    cluster: str | None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(admin, "bootstrap_environment", forbid)
    args = argparse.Namespace(expected_cluster_id=cluster)
    with pytest.raises(MigrationSafetyError, match="numeric"):
        admin.run_online(args)


def test_missing_explicit_file_stops_before_secret_access(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(admin, "bootstrap_environment", forbid)
    with pytest.raises(MigrationSafetyError, match="explicit bootstrap"):
        admin.run_online(argparse.Namespace(expected_cluster_id="123", env_file=None))


@pytest.mark.parametrize("changed", [0, 1, 2, 3, 4, 5, 6])
def test_identity_mismatch_rejected_before_session_settings(changed: int) -> None:
    expected: list[object] = ["nexus_ai", "postgres", "postgres", 16, "123", True, "postgres"]
    expected[changed] = "wrong"
    connection = MagicMock()
    connection.exec_driver_sql.return_value.one.return_value = expected
    with pytest.raises(MigrationSafetyError, match="identity mismatch"):
        admin.identity(cast(Connection, connection), "123")
    assert connection.exec_driver_sql.call_count == 1


def test_identity_accepts_only_exact_contract() -> None:
    connection = MagicMock()
    connection.exec_driver_sql.return_value.one.return_value = (
        "nexus_ai",
        "postgres",
        "postgres",
        16,
        "123",
        True,
        "postgres",
    )
    admin.identity(cast(Connection, connection), "123")
    assert connection.exec_driver_sql.call_count == 4


def test_nonempty_baseline_rejected() -> None:
    connection = MagicMock()
    connection.exec_driver_sql.return_value.scalar.return_value = True
    with pytest.raises(MigrationSafetyError, match="exact fresh empty"):
        admin.empty_target(cast(Connection, connection))


def test_schema_fingerprint_detects_same_named_changed_constraint() -> None:
    connection = MagicMock()
    connection.exec_driver_sql.return_value.all.return_value = [
        ("constraint", "orders", "ck_orders_status", "CHECK (status IN ('pending'))")
    ]
    initial = admin.schema_fingerprint(cast(Connection, connection))
    connection.exec_driver_sql.return_value.all.return_value = [
        ("constraint", "orders", "ck_orders_status", "CHECK (true)")
    ]
    assert admin.schema_fingerprint(cast(Connection, connection)) != initial


@pytest.mark.parametrize("extra_revision", [False, True])
def test_changed_or_expanded_initial_revision_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, extra_revision: bool
) -> None:
    versions = tmp_path / "migrations/versions"
    versions.mkdir(parents=True)
    original = admin.ROOT / "migrations/versions/0001_initial_schema.py"
    (versions / original.name).write_bytes(original.read_bytes() if extra_revision else b"changed")
    if extra_revision:
        (versions / "0002_unapproved.py").write_text("# unapproved")
    monkeypatch.setattr(admin, "ROOT", tmp_path)
    with pytest.raises(MigrationSafetyError):
        admin.frozen_config()


@pytest.mark.parametrize(
    "error", [OSError("sensitive-test-value"), sa.exc.SQLAlchemyError("sensitive-test-value")]
)
def test_failures_redacted(
    error: Exception, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fail() -> None:
        raise error

    monkeypatch.setattr(admin, "frozen_config", fail)
    assert admin.main(["plan"]) == 1
    output = capsys.readouterr()
    assert "sensitive-test-value" not in output.out + output.err
    assert "details suppressed" in output.err


def test_security_source_exact_capabilities() -> None:
    sql = (admin.ROOT / "security/apply_security.sql").read_text()
    assert sql.count("CREATE ROLE ") == 3
    assert sql.count("NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE") == 3
    assert sql.count("WITH (security_invoker = false)") == 3
    assert (
        "GRANT SELECT ON public.v_customers, public.v_orders, "
        "public.v_shipment_events TO nexus_tool;" in sql
    )
    grant = sql.split("GRANT INSERT (", 1)[1].split(") ON public.audit_events TO nexus_app;", 1)[0]
    assert {column.strip() for column in grant.split(",")} == {
        "request_id",
        "event_type",
        "actor_id",
        "tool_name",
        "args_hash",
        "decision",
        "row_count",
        "latency_ms",
        "model",
        "error_code",
        "created_at",
    }
    statements = [line for line in sql.splitlines() if not line.lstrip().startswith("--")]
    source = "\n".join(statements)
    assert "PASSWORD" not in source and " LOGIN" not in source
    assert "DROP " not in source and "TRUNCATE " not in source
    assert "GRANT USAGE ON SEQUENCE" not in source
    assert (
        "ALTER DEFAULT PRIVILEGES FOR ROLE nexus_owner\n    REVOKE EXECUTE ON FUNCTIONS" in source
    )


def test_readonly_verifier_checks_effective_not_named_rights() -> None:
    sql = (admin.ROOT / "security/verify_security.sql").read_text()
    for function in (
        "has_table_privilege",
        "has_column_privilege",
        "has_schema_privilege",
        "has_database_privilege",
        "has_sequence_privilege",
        "pg_auth_members",
    ):
        assert function in sql
    assert "WITH GRANT OPTION" in sql
    assert "defaclnamespace = 0" in sql
    assert "pg_get_viewdef" in sql


@pytest.mark.parametrize("case", ["role-conflict", "schema-hash", "partial-check", "not-deployed"])
def test_online_preflight_stops_before_mutation(case: str, monkeypatch: pytest.MonkeyPatch) -> None:
    engine = MagicMock()
    connection = engine.connect.return_value.__enter__.return_value
    monkeypatch.setattr(sa, "create_engine", lambda *args, **kwargs: engine)
    monkeypatch.setattr(
        admin,
        "bootstrap_environment",
        lambda *args: {"NEXUS_MIGRATION_PASSWORD": "non-secret-test-value"},
    )
    monkeypatch.setattr(admin, "identity", lambda *args: None)
    monkeypatch.setattr(admin, "initial_contract", lambda *args: None)
    monkeypatch.setattr(admin, "schema_fingerprint", lambda *args: "observed-hash")
    roles = {"nexus_tool"} if case in {"role-conflict", "partial-check"} else set()
    monkeypatch.setattr(admin, "inventory", lambda *args: (roles, set()))
    args = argparse.Namespace(
        action="check" if case in {"partial-check", "not-deployed"} else "apply",
        expected_cluster_id="123",
        env_file=Path("never-read.example"),
        expected_schema_sha256="different-hash",
        execute=True,
        database="nexus_ai",
    )
    if case == "not-deployed":
        assert admin.run_online(args) == 2
    else:
        with pytest.raises(MigrationSafetyError):
            admin.run_online(args)
    statements = [call.args[0] for call in connection.exec_driver_sql.call_args_list]
    assert statements == ["SET TRANSACTION READ ONLY"]
    engine.dispose.assert_called_once()
