"""No real credential generation, file creation or database connection in these tests."""

import secrets
from pathlib import Path

import pytest

from nexus.persistence import runtime_credentials as credentials


def arguments(path: Path) -> list[str]:
    return [
        "provision",
        "--database",
        "nexus_ai",
        "--expected-cluster-id",
        "123",
        "--env-file",
        "never-read.example",
        "--runtime-env-file",
        str(path),
    ]


def forbid(*args: object, **kwargs: object) -> None:
    pytest.fail("Guarded command attempted provisioning or real randomness")


@pytest.mark.parametrize("flags", [[], ["--execute"], ["--acknowledge-target-scope"]])
def test_credential_approval_and_scope_gates(
    flags: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(credentials, "provision", forbid)
    monkeypatch.setattr(secrets, "token_urlsafe", forbid)
    assert credentials.main(arguments(credentials.RUNTIME_FILE) + flags) == 2


def test_fixed_runtime_path_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(credentials, "provision", forbid)
    assert (
        credentials.main(
            arguments(Path("different.example")) + ["--execute", "--acknowledge-target-scope"]
        )
        == 2
    )


def test_existing_file_not_overwritten(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    existing = tmp_path / "existing.example"
    existing.write_text("non-secret-existing-content")
    monkeypatch.setattr(credentials, "RUNTIME_FILE", existing)
    monkeypatch.setattr(credentials, "provision", forbid)
    assert credentials.main(arguments(existing) + ["--execute", "--acknowledge-target-scope"]) == 2
    assert existing.read_text() == "non-secret-existing-content"


def test_credential_driver_failure_is_redacted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    future = tmp_path / "absent.example"
    monkeypatch.setattr(credentials, "RUNTIME_FILE", future)

    def fail(*args: object) -> None:
        raise RuntimeError("sensitive-test-value")

    monkeypatch.setattr(credentials, "provision", fail)
    assert credentials.main(arguments(future) + ["--execute", "--acknowledge-target-scope"]) == 1
    output = capsys.readouterr()
    assert "sensitive-test-value" not in output.out + output.err
    assert "details suppressed" in output.err
    assert not future.exists()
