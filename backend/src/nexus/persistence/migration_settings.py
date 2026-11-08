"""Explicit migration-only settings; this module never loads secrets on import."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

TEST_DATABASE = "nexus_m13_test"
TEST_DATABASE_MARKER = "nexus-ai:m1.3-disposable"


class MigrationSafetyError(ValueError):
    """A migration target or credential source did not meet the safety contract."""


@dataclass(frozen=True)
class MigrationSettings:
    database: str
    user: str
    password: str = field(repr=False)
    host: str = "127.0.0.1"
    port: int = 5432

    def __post_init__(self) -> None:
        if self.database != TEST_DATABASE:
            raise MigrationSafetyError(
                "Online migrations require the exact disposable test database."
            )
        if self.host != "127.0.0.1" or self.port != 5432:
            raise MigrationSafetyError(
                "M1.3 migrations require the documented local PostgreSQL endpoint."
            )
        if not self.user or not self.password or self.password == "replace-me":
            raise MigrationSafetyError(
                "Explicit non-placeholder migration credentials are required."
            )


def settings_from_environment(environment: Mapping[str, str]) -> MigrationSettings:
    """Build components without accepting a secret-bearing connection URL."""
    try:
        return MigrationSettings(
            database=environment["NEXUS_MIGRATION_DATABASE"],
            user=environment["NEXUS_MIGRATION_USER"],
            password=environment["NEXUS_MIGRATION_PASSWORD"],
            host=environment.get("NEXUS_MIGRATION_HOST", "127.0.0.1"),
            port=int(environment.get("NEXUS_MIGRATION_PORT", "5432")),
        )
    except (KeyError, ValueError) as error:
        if isinstance(error, MigrationSafetyError):
            raise
        raise MigrationSafetyError("Valid explicit migration settings are required.") from None


def bootstrap_environment(environment: Mapping[str, str], path: Path) -> dict[str, str]:
    """Consume an explicitly selected bootstrap file without evaluating shell syntax.

    Call only for an approved online command. This is not runtime application wiring.
    The generated M1.2 file has simple unquoted KEY=value lines. Its database name
    is deliberately ignored so it can never redirect migrations to nexus_ai.
    """
    try:
        password: str | None = None
        for line in path.read_text().splitlines():
            if not line or line.lstrip().startswith("#"):
                continue
            key, separator, value = line.partition("=")
            if not separator:
                raise MigrationSafetyError("Bootstrap file must contain plain KEY=value lines.")
            if key == "NEXUS_DB_ADMIN_PASSWORD":
                if password is not None:
                    raise MigrationSafetyError("Duplicate bootstrap credential entry.")
                password = value
        if not password:
            raise MigrationSafetyError("Bootstrap credential entry is missing.")
    except OSError:
        raise MigrationSafetyError("Explicit bootstrap credential file cannot be read.") from None
    result = dict(environment)
    result["NEXUS_MIGRATION_PASSWORD"] = password
    result.setdefault("NEXUS_MIGRATION_USER", "postgres")
    return result
