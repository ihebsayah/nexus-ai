# M1.3 migration tooling

The owner authorized M1.3 installation and isolated execution; both completed successfully. nexus_m13_test is retained at revision 0001_initial_schema with zero application rows after one approved test downgrade/re-upgrade. nexus_ai and nexus_m12_verify remain untouched. Future mutation/reversal runs require new explicit approval; the initial M1.3 approval is not a standing reset permission.

## Schema contract

[Architecture section 10.2](../docs/ARCHITECTURE.md#102-initial-schema) is authoritative. The four mappings preserve its 25 columns, UUID business keys versus bigint audit identity, nine checks, two `ON DELETE RESTRICT` foreign keys and eight named functional/composite/partial indexes. All timestamps use `DateTime(timezone=True)`; only the documented `created_at` fields default to server `now()`. Expected delivery and event occurrence times have no defaults. There are no native enums, Python defaults, ORM delete cascades, seed rows, extensions, roles, views or application endpoint changes.

Initial revision: `0001_initial_schema`; `down_revision=None`; no branches or dependencies. Revision operations are frozen and never import current models. Upgrade creates customers, orders, shipment_events and audit_events in foreign-key order; downgrade reverses dependencies and removes only those objects/indexes. An empty `alembic_version` table may remain after downgrade to base; it is migration bookkeeping, not an application table.

## Installed migration dependencies

- [SQLAlchemy 2.0.57](https://pypi.org/project/SQLAlchemy/2.0.57/): explicit 2.0 line instead of introducing the newer 2.1 API line.
- [Alembic 1.20.1](https://pypi.org/project/alembic/1.20.1/): versioned PostgreSQL DDL.
- [psycopg 3.3.8](https://pypi.org/project/psycopg/3.3.8/) with the [binary extra](https://pypi.org/project/psycopg-binary/3.3.8/): migration/test driver without installing a host libpq toolchain.

Official release metadata was checked and the exact versions are now installed. Approved resolution added eight related lock records while retaining every old dependency record/version; 35 installed packages pass compatibility checking. The lock is updated and consistent. No SQLAlchemy stubs package or async runtime integration is introduced.

Initial approved installation command, **executed successfully**, from `backend/`:

```bash
UV_PYTHON_DOWNLOADS=never uv sync --python python3.13
```

This updated the existing lock with the three declared additions and required/conditional transitives, and synchronized the local environment/editable backend without --upgrade. No old dependency version changed. Actual download total was not measured. Future installation/resolution still requires explicit approval.

## Offline inspection

From the project root, after approved dependency installation:

```bash
make migration-heads
make migration-history
make migration-sql
```

These targets use only installed local executables and never install dependencies. Heads/history discover the fixed migration directory; SQL renders the upgrade without connecting or loading a credential file. Offline SQL is review output, not evidence of an applied schema. Heads/history and pure offline SQL generation executed successfully after installation. The dependency guard remains in place for an unprepared environment.

Alembic paths are relative to `backend/alembic.ini`, not the caller's working directory. Online code sets `search_path` to public and verifies the selected database identity before running migrations. No additional PostgreSQL schema namespace is created; application tables are created in public only by an explicitly approved disposable upgrade.

## Disposable target and credentials

All online commands are hard-guarded to database **nexus_m13_test**, host **127.0.0.1**, port **5432**, and database comment **nexus-ai:m1.3-disposable**. The guard applies to direct Alembic entry as well as the wrapper. Neither nexus_ai nor nexus_m12_verify can be upgraded/downgraded through this M1.3 environment. No database is auto-created or dropped.

Before approved database creation, query the catalog and confirm that nexus_m13_test is absent. Stop on an existing name; never reuse or drop an unknown database. The initial approved creation statements (executed once after an absent-name guard) were:

```sql
CREATE DATABASE nexus_m13_test TEMPLATE template0;
COMMENT ON DATABASE nexus_m13_test IS 'nexus-ai:m1.3-disposable';
```

Run as separate autocommit statements, not a single transaction. This marker is disposable-test ownership metadata, not a business schema rule. Database creation/comment are persistent mutations and need explicit approval.

`make` targets explicitly pass `--env-file infra/.env`. Only an explicit online command or opted-in PostgreSQL fixture reads that selected file; imports and tests without PostgreSQL opt-in do not load private files. The parser accepts plain key/value lines without shell evaluation. It uses the bootstrap administrator password, ignores the file's `NEXUS_DB_NAME=nexus_ai`, and always supplies the fixed test target. Existing generated credentials are consumed but never rewritten. The admin connection is migration/test tooling only, not an application runtime default or grant design. Future runtime credentials/roles are M1.4 work.

Alternatively supply explicit `NEXUS_MIGRATION_DATABASE`, `NEXUS_MIGRATION_USER`, `NEXUS_MIGRATION_PASSWORD` environment components to Alembic. Host/port default to the guarded local endpoint. Do not put a URL or actual password in `alembic.ini`, command arguments, output or source. URL construction uses SQLAlchemy `URL.create`; driver errors are suppressed rather than serializing secrets, and SQL parameters are hidden.

## Online command reference

```bash
# Test-only inspection. Connections are wrapped in a read-only transaction.
make migration-current
make migration-check

# Requires specific owner approval for the disposable test database:
make migration-upgrade-test
make migration-check

# Reference only: this manual downgrade was NOT run. The single approved automated reversal already completed.
# Any future destructive test requires new approval; real/M1.2 databases remain forbidden:
make migration-downgrade-test
make migration-upgrade-test
make migration-check
```

Current/check may fail on an uninitialized or out-of-date database; they are not upgrade operations. Read-only transaction mode prevents accidental writes during inspection. PostgreSQL catalog tests must independently inspect check definitions/identity/FKs/indexes: Alembic autogenerate comparison alone does not establish all check-constraint semantics.

Integration-test inserts must run only in the marked disposable database and roll back their fixture transactions. They are test mutations requiring approval; they are not a seed script. After approved test execution, compare nexus_ai catalogs and the nexus_m12_verify marker with the pre-test baseline. Never downgrade, reset or drop the real database or remove the M1.2 evidence.

This milestone does not propose applying the revision to nexus_ai. An eventual real application upgrade needs a separately reviewed/approved target-enablement change and migration plan. Stop after M1.3; do not start M1.4.

## Automated test entry points

Currently executable without the new packages (from backend/):

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/test_scaffold.py tests/test_migration_safety.py
```

During pre-install preparation, 24 pure safety/legacy tests passed. After approved installation, executable metadata/offline-Alembic tests and strict typing pass as recorded in the verification report.

The following exact command ran once with explicit installation/database/DML/reversal approval, from the **project root** (keeping the relative credential path correct). It passed 39 tests. **Do not rerun this reversal-enabled form under the spent initial approval.**

```bash
NEXUS_M13_ALLOW_DB_TESTS=1 \
NEXUS_M13_ALLOW_TEST_DOWNGRADE=1 \
NEXUS_M13_ENV_FILE=infra/.env \
NEXUS_MIGRATION_DATABASE=nexus_m13_test \
backend/.venv/bin/python -m pytest -c backend/pyproject.toml backend/tests/test_schema.py
```

Without PostgreSQL opt-in, integration fixtures skip before any credential-file read or connection. With opt-in, the fixture verifies the database marker before upgrade, then tests catalog/model agreement and transactional constraint cases. The reversal needs its separate flag and verifies empty tables before downgrade; it re-upgrades to head. No database is created or dropped by pytest. The owner approved initial absent-database creation/comment and the isolated execution, as recorded in [M1.3 evidence](../docs/M1_3_VERIFICATION.md#server-identity-and-database-creation). That database now exists and must never be overwritten, dropped or recreated to resolve a conflict.


Final regression used NEXUS_M13_ALLOW_TEST_DOWNGRADE=0 to avoid repeating the completed reversal: 62 backend tests passed, the already-verified reversal intentionally skipped, and frontend lint/type/test/Webpack build passed. No seed rows remain. Full executed commands, catalogs, lock review, preservation and final reviewer outcome are in [M1.3 verification](../docs/M1_3_VERIFICATION.md).

Final independent read-only review approved with comments and no unresolved material finding: **M1.3 PASS for the authorized isolated scope**. The real nexus_ai database remains unmigrated and M1.4 has not begun.
