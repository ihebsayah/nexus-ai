"""Credential/target guards and revision source checks requiring no new package."""

import ast
from pathlib import Path

import pytest

from nexus.persistence.migration_settings import (
    MigrationSafetyError,
    MigrationSettings,
    bootstrap_environment,
    settings_from_environment,
)

BACKEND = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "database", ["nexus_ai", "nexus_m12_verify", "postgres", "NEXUS_M13_TEST", ""]
)
def test_online_settings_reject_non_test_databases(database: str) -> None:
    with pytest.raises(MigrationSafetyError):
        MigrationSettings(database, "postgres", "unit-test-value")


@pytest.mark.parametrize("host,port", [("localhost", 5432), ("0.0.0.0", 5432), ("127.0.0.1", 5433)])
def test_online_settings_reject_other_endpoints(host: str, port: int) -> None:
    with pytest.raises(MigrationSafetyError):
        MigrationSettings("nexus_m13_test", "postgres", "unit-test-value", host, port)


@pytest.mark.parametrize(
    "user,password", [("", "unit-test-value"), ("postgres", ""), ("postgres", "replace-me")]
)
def test_settings_require_explicit_non_placeholder_credentials(user: str, password: str) -> None:
    with pytest.raises(MigrationSafetyError):
        MigrationSettings("nexus_m13_test", user, password)


def test_settings_hide_password_in_repr() -> None:
    settings = MigrationSettings("nexus_m13_test", "postgres", "unit-test-value")
    assert "unit-test-value" not in repr(settings)
    assert settings.database == "nexus_m13_test"


@pytest.mark.parametrize(
    "values",
    [
        {},
        {
            "NEXUS_MIGRATION_DATABASE": "nexus_m13_test",
            "NEXUS_MIGRATION_USER": "postgres",
            "NEXUS_MIGRATION_PASSWORD": "unit-test-value",
            "NEXUS_MIGRATION_PORT": "not-a-port",
        },
    ],
)
def test_environment_errors_do_not_include_values(values: dict[str, str]) -> None:
    with pytest.raises(MigrationSafetyError, match="Valid explicit migration settings"):
        settings_from_environment(values)


def test_explicit_bootstrap_does_not_redirect_database_or_evaluate_shell(tmp_path: Path) -> None:
    source = tmp_path / "bootstrap.example"
    source.write_text("NEXUS_DB_NAME=nexus_ai\nNEXUS_DB_ADMIN_PASSWORD=$(never-evaluate-this)\n")
    original = {"NEXUS_MIGRATION_DATABASE": "nexus_m13_test"}
    result = bootstrap_environment(original, source)
    assert result["NEXUS_MIGRATION_DATABASE"] == "nexus_m13_test"
    assert result["NEXUS_MIGRATION_USER"] == "postgres"
    assert result["NEXUS_MIGRATION_PASSWORD"] == "$(never-evaluate-this)"
    assert "NEXUS_MIGRATION_PASSWORD" not in original
    assert settings_from_environment(result).database == "nexus_m13_test"


@pytest.mark.parametrize(
    "contents",
    [
        "BROKEN",
        "NEXUS_DB_NAME=nexus_ai\n",
        "NEXUS_DB_ADMIN_PASSWORD=x\nNEXUS_DB_ADMIN_PASSWORD=y\n",
    ],
)
def test_bootstrap_rejects_malformed_or_duplicate_credentials(
    tmp_path: Path, contents: str
) -> None:
    source = tmp_path / "bootstrap.example"
    source.write_text(contents)
    with pytest.raises(MigrationSafetyError):
        bootstrap_environment({}, source)


def test_bootstrap_missing_file_is_sanitized(tmp_path: Path) -> None:
    with pytest.raises(MigrationSafetyError, match="cannot be read"):
        bootstrap_environment({}, tmp_path / "absent.example")


def test_revision_is_frozen_single_initial_revision_without_seed_operations() -> None:
    revisions = list((BACKEND / "migrations" / "versions").glob("*.py"))
    assert len(revisions) == 1
    tree = ast.parse(revisions[0].read_text())
    assignments = {
        node.target.id: ast.literal_eval(node.value)
        for node in tree.body
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.value is not None
    }
    assert assignments["revision"] == "0001_initial_schema"
    assert assignments["down_revision"] is None
    assert assignments["branch_labels"] is None
    assert assignments["depends_on"] is None
    imports = [node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
    assert not any(name.startswith("nexus") for name in imports)
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    calls = [
        node.func.attr
        for node in ast.walk(functions["upgrade"])
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "op"
    ]
    assert calls.count("create_table") == 4
    assert calls.count("create_index") == 8
    assert set(calls) == {"create_table", "create_index"}
