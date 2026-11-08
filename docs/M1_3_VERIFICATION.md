# M1.3 — Approved installation and isolated migration verification

Date: 2026-11-08 (Africa/Tunis)
Status: **M1.3 PASS for the authorized isolated scope** — installation, static validation, migration/reversal, regressions, preservation and final independent read-only review passed. The real nexus_ai database remains unmigrated and nexus_m12_verify remains intact. No M1.4 work has begun.

## Scope and approvals

The owner authorized the three declared dependency additions and existing-lock regeneration; creation of only absent nexus_m13_test from template0 with an ownership comment; guarded upgrade/check; transactional constraint DML; and one guarded test downgrade/re-upgrade. No database drop, real-database migration, role/view/seed/API/AI integration, Docker lifecycle change or commit/push was authorized or performed.

The first installation attempt exited 2 because the sandbox denied the default uv cache. Broader access for the already-authorized package cache/registry, Docker socket and localhost test/migration connections was requested; the owner explicitly approved it before retry. No permission denial was silently bypassed.

Data-engineer schema design, backend implementation, QA test design and independent static review were completed sequentially during preparation. The static reviewer found no unresolved material issue. This report supersedes the earlier PARTIAL dependency/runtime gates with actual execution evidence; final runtime review follows below.

## Dependency installation and lock review

Exact approved command, executed from backend/:

```bash
UV_PYTHON_DOWNLOADS=never uv sync --python python3.13
```

Broader-access retry exited 0. CPython 3.13.3 was reused; no Python download or --upgrade flag. uv resolved 38 lock records and installed the new requirements/rebuilt editable backend. Historical incompatible egg-file warnings were metadata skips, not installed old packages or failed resolution.

| New lock entry | Version | Installed here |
| --- | --- | --- |
| SQLAlchemy | 2.0.57 | yes |
| Alembic | 1.20.1 | yes |
| psycopg | 3.3.8 | yes |
| psycopg-binary | 3.3.8 | yes; binary extra |
| Mako | 1.4.3 | yes; required transitive |
| MarkupSafe | 3.0.4 | yes; required transitive |
| greenlet | 3.5.6 | no; conditional lock entry |
| tzdata | 2026.6 | no; conditional lock entry |

All previous locked package versions and complete dependency records remain identical. Only the editable project's existing record changed to add the approved requirements; eight new related records were added. No old package was removed, unrelated direct dependency upgraded or frontend lock changed. Lock format/top-level fields are unchanged; artifact SHA-256 hashes are present.

Installed-version assertions pass. `UV_CACHE_DIR=/tmp/nexus-m13-uv-cache uv pip check --python backend/.venv/bin/python` exited 0: all 35 installed packages compatible. From backend/, `UV_CACHE_DIR=/tmp/nexus-m13-uv-cache UV_PYTHON_DOWNLOADS=never uv lock --check --offline` exited 0, resolving 38 records in 14ms.

Final backend lock SHA-256:

```text
fb5a65b702d8585ed795cb04e6a37984ed3ffe2c2359f0c2d2ff85bd733b109b
```

## Pre-mutation static gate

The first installed strict-mypy run found one untyped call in the offline index-DDL test (`postgresql.dialect()`). It was corrected to use SQLAlchemy's typed `URL.create("postgresql").get_dialect()` factory. No type-ignore, disabled strictness, runtime schema change or new dependency was used. PostgreSQL was not mutated until all following checks passed.

| Actual command | Exit / result |
| --- | --- |
| `NEXUS_M13_ALLOW_DB_TESTS=0 NEXUS_M13_ALLOW_TEST_DOWNGRADE=0 make backend-lint backend-typecheck backend-test` | Exit 0 after the typing fix. Ruff passes; 19 files already formatted; mypy passes 18 source files; 27 tests pass, 36 PostgreSQL cases deliberately skip, 1 existing warning, 0.74s. |
| `make migration-heads migration-history` | Exit 0. One head `0001_initial_schema`, parent base, no branches/dependencies. |
| `make --silent migration-sql > /tmp/nexus-m13-offline.sql` | Exit 0. Pure transactional PostgreSQL DDL inspected: four app tables plus Alembic tracking, eight secondary indexes, nine checks, two RESTRICT FKs and ALWAYS identity; no seeds/roles/views/extensions. |
| Python offline DDL assertions | Exit 0; counts/operations match the frozen revision and model contract. |

The initial `make -k ...` run before the typing fix exited 2 due to that single mypy error, while its tests already passed. The initial SQL capture included Make's recipe echo; it was regenerated with --silent for a pure SQL artifact. All static gates above passed before test database creation. Offline SQL generation reads no credential file and opens no database connection.

## Server identity and database creation

Credential-safe read-only preflight confirmed healthy PostgreSQL 16.15 (Debian 16.15-1.pgdg12+2), exact M1.2 image digest and sole host binding 127.0.0.1:5432. The cluster system identifier is **7705524319955709990**. nexus_ai had only public and no public relations/application roles; nexus_m12_verify retained `nexus-m1.2-persistence-probe`; nexus_m13_test was absent. The catalog snapshot matched preparation. Existing container/network/volume IDs and running-state sets were saved for comparison.

The exact guarded procedure documented during preparation was executed (exit 0):

```bash
python3 - <<'CREATE_TEST_DATABASE'
import subprocess
command = [
    "docker", "compose", "--env-file", "infra/.env", "-f", "infra/compose.yaml",
    "exec", "-T", "postgres", "sh", "-ec",
    'PGPASSWORD="$POSTGRES_PASSWORD" PGCONNECT_TIMEOUT=3 '
    'psql -X --no-password -h 127.0.0.1 -U postgres -d postgres '
    '-v ON_ERROR_STOP=1 -v AUTOCOMMIT=on -qAt',
]
def sql(statement):
    result = subprocess.run(command, input=statement, text=True, capture_output=True, check=True)
    return result.stdout.strip()
if sql("SELECT 1 FROM pg_database WHERE datname='nexus_m13_test';\n"):
    raise SystemExit("Test database already exists; creation stopped without modifying it.")
sql("CREATE DATABASE nexus_m13_test TEMPLATE template0;\n"
    "COMMENT ON DATABASE nexus_m13_test IS 'nexus-ai:m1.3-disposable';\n")
print("Created owned disposable nexus_m13_test; no credential printed.")
CREATE_TEST_DATABASE
```

CREATE DATABASE was autocommit, not wrapped in a transaction; the absent-name guard and PostgreSQL refusal on an existing name prevent reuse/overwrite. The created database/comment are retained. No database was dropped. Administration connected to built-in postgres; no application object was created in nexus_ai.

A read-only host-side SQLAlchemy/psycopg connection then verified the same cluster identifier, exact test database/comment and empty public tables before upgrade. The temporary bootstrap administrator is migration/test tooling only; application runtime credentials and M1.4 roles are not introduced.

## Upgrade, constraints and single reversal

Executed from the project root with the approved local-network access:

```bash
make migration-upgrade-test
make migration-check

NEXUS_M13_ALLOW_DB_TESTS=1 \
NEXUS_M13_ALLOW_TEST_DOWNGRADE=1 \
NEXUS_MIGRATION_DATABASE=nexus_m13_test \
NEXUS_M13_ENV_FILE=infra/.env \
backend/.venv/bin/python -m pytest -c backend/pyproject.toml backend/tests/test_schema.py
```

Upgrade/check both exited 0. Alembic reported `No new upgrade operations detected`. The exact opted-in schema suite exited 0: **39 passed in 1.15s**. This includes executable metadata/offline revision validation and all 36 PostgreSQL cases; none is inferred from a static check.

All online commands require exact test name, localhost endpoint and ownership comment. Constraint records were rolled back; no seed data was inserted by the migration. Valid enum/boundary cases, invalid checks/foreign keys, lower(email) uniqueness, restricted deletes, server defaults and ALWAYS identity rejection were tested.

The single reversal case verified empty application tables, downgraded to base, verified only empty Alembic tracking could remain, then re-upgraded to head and checked schema agreement. The fixture's upgrade calls while already at head were no-ops, not extra reversals. No additional manual downgrade was run. The final test database is upgraded at `0001_initial_schema`, with all four application tables empty. Identity counters may have advanced through rolled-back tests; this is confined to the disposable database.

## Observed PostgreSQL schema

Read-only catalogs and SQLAlchemy inspection after regressions confirm exactly four application tables plus alembic_version bookkeeping, 25 application columns, nine CHECKs, two RESTRICT FKs, eight named secondary indexes, four application PK indexes and Alembic's tracking PK index. The only public sequence is audit_events_id_seq; no views or additional application schema namespace exists. The schema/model comparison returns an empty difference list.

| Actual column | Type | Nullability | Default / identity |
| --- | --- | --- | --- |
| audit_events.id | BIGINT | NOT NULL | `GENERATED ALWAYS AS IDENTITY` |
| audit_events.request_id | UUID | NOT NULL | `none` |
| audit_events.event_type | TEXT | NOT NULL | `none` |
| audit_events.actor_id | TEXT | NOT NULL | `'local'::text` |
| audit_events.tool_name | TEXT | NULL | `none` |
| audit_events.args_hash | TEXT | NULL | `none` |
| audit_events.decision | TEXT | NULL | `none` |
| audit_events.row_count | INTEGER | NULL | `none` |
| audit_events.latency_ms | INTEGER | NULL | `none` |
| audit_events.model | TEXT | NULL | `none` |
| audit_events.error_code | TEXT | NULL | `none` |
| audit_events.created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | `now()` |
| customers.id | UUID | NOT NULL | `gen_random_uuid()` |
| customers.name | TEXT | NOT NULL | `none` |
| customers.email | TEXT | NOT NULL | `none` |
| customers.created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | `now()` |
| orders.id | UUID | NOT NULL | `gen_random_uuid()` |
| orders.customer_id | UUID | NOT NULL | `none` |
| orders.status | TEXT | NOT NULL | `none` |
| orders.created_at | TIMESTAMP WITH TIME ZONE | NOT NULL | `now()` |
| orders.expected_delivery_at | TIMESTAMP WITH TIME ZONE | NOT NULL | `none` |
| shipment_events.id | UUID | NOT NULL | `gen_random_uuid()` |
| shipment_events.order_id | UUID | NOT NULL | `none` |
| shipment_events.event_type | TEXT | NOT NULL | `none` |
| shipment_events.occurred_at | TIMESTAMP WITH TIME ZONE | NOT NULL | `none` |

Required foreign keys are orders.customer_id → customers.id and shipment_events.order_id → orders.id, both ON DELETE RESTRICT, with no added cascade behavior. Business primary keys are UUID; audit_events.id is BIGINT GENERATED ALWAYS AS IDENTITY. All five timestamps are timezone-aware. Expected-delivery/event-occurrence timestamps have no defaults.

| Observed CHECK name | PostgreSQL deparsed definition |
| --- | --- |
| ck_audit_events_decision | `decision = ANY (ARRAY['allowed'::text, 'denied'::text, 'completed'::text, 'error'::text])` |
| ck_audit_events_event_type | `event_type = ANY (ARRAY['request'::text, 'tool_decision'::text, 'grounding'::text, 'error'::text])` |
| ck_audit_events_latency_ms | `latency_ms >= 0` |
| ck_audit_events_row_count | `row_count >= 0` |
| ck_customers_email_at | `POSITION(('@'::text) IN (email)) > 1` |
| ck_customers_name_length | `length(btrim(name)) >= 1 AND length(btrim(name)) <= 200` |
| ck_orders_expected_delivery | `expected_delivery_at >= created_at` |
| ck_orders_status | `status = ANY (ARRAY['pending'::text, 'confirmed'::text, 'in_transit'::text, 'delivered'::text, 'cancelled'::text])` |
| ck_shipment_events_event_type | `event_type = ANY (ARRAY['created'::text, 'picked_up'::text, 'in_transit'::text, 'out_for_delivery'::text, 'delivered'::text, 'exception'::text])` |

| Observed secondary index | Keys / uniqueness | PostgreSQL predicate |
| --- | --- | --- |
| audit_events_created_idx | `created_at` | `none` |
| audit_events_request_idx | `request_id, created_at` | `none` |
| customers_email_lower_uidx | UNIQUE `lower(email)` | `none` |
| customers_name_lower_idx | `lower(name)` | `none` |
| orders_customer_created_idx | `customer_id, created_at DESC, id DESC` | `none` |
| orders_overdue_idx | `expected_delivery_at, id` | `(status <> ALL (ARRAY['delivered'::text, 'cancelled'::text]))` |
| orders_pending_idx | `created_at, id` | `(status = 'pending'::text)` |
| shipment_events_order_occurred_idx | `order_id, occurred_at DESC, id DESC` | `none` |

Final observed state:

```text
revision: 0001_initial_schema
customers: 0 rows
orders: 0 rows
shipment_events: 0 rows
audit_events: 0 rows
compare_metadata: []
sequence: audit_events_id_seq
views: []
```

PostgreSQL deparses IN/BETWEEN syntax into equivalent ANY/ALL/AND expressions; those textual changes are not business-rule changes. Check names plus independent frozen DDL and accepted/rejected-row tests establish the intended semantics; Alembic autogenerate agreement alone is not treated as proof of CHECK correctness.

## Post-verification regression commands

Exact command sequence, after the single reversal:

```bash
make backend-lint backend-typecheck
NEXUS_M13_ALLOW_DB_TESTS=1 \
NEXUS_M13_ALLOW_TEST_DOWNGRADE=0 \
NEXUS_MIGRATION_DATABASE=nexus_m13_test \
NEXUS_M13_ENV_FILE=infra/.env \
backend/.venv/bin/python -m pytest -c backend/pyproject.toml backend/tests
make frontend-lint frontend-typecheck frontend-test frontend-build NEXT_BUILD_FLAGS=--webpack
```

Combined exit 0. Ruff/format passes; strict mypy reports no issues in 18 source files. Backend: **62 passed, 1 skipped, 1 existing warning in 1.22s**. The sole skip is intentional: the already-passed reversal flag was disabled to prevent a second destructive test. It is not an unexecuted acceptance gate; that test passed in the prior 39-test run. Across the runs, every one of the 63 distinct backend cases executed successfully.

Frontend ESLint, route type generation, TypeScript, one Vitest test and Webpack production build pass. The default Turbopack restriction and HTTPX TestClient deprecation remain existing M1.1 limitations; no unrelated upgrade was made to suppress them.

## Preservation and security

Final read-only comparison against the pre-mutation snapshot passes: nexus_ai still has public only and no application relations; no nexus_owner/app/tool roles exist; nexus_m12_verify still has its exact marker. The only expected catalog change is nexus_m13_test now existing. Cluster identifier and server version remain identical. No migration command targeted either protected database.

All pre-existing Docker container/network/volume ID sets and the running-container set are unchanged. No Docker start/stop/restart/pull/prune command ran in M1.3. Actual binding remains only 127.0.0.1:5432. Database files changed only within the authorized NEXUS cluster/test scope; no claim of hashing private unrelated volumes is made.

The private credential file remains mode0600, Git-ignored and untracked; it was never rewritten or displayed. URL creation uses components, parameters are hidden, and driver errors are suppressed. Git index is empty, with no commit/push. No comprehensive secret-scanner audit is claimed.

The approved-execution snapshot covers 81 non-secret project files. All remain present. Protected OpenCode/configuration files, existing API/scaffold test, frontend source/lockfiles, infrastructure configuration, M1.2 evidence and ADR statuses are preserved. Only the approved backend lock, the typing-only test fix and documentation change in this execution phase.

## Files changed during approved execution

```text
backend/uv.lock                  M approved additions; no old version changes
backend/tests/test_schema.py      M typed offline-dialect factory
backend/MIGRATIONS.md             M installed/executed-state guidance
README.md                        M M1.3 current status
docs/ROADMAP.md                  M current milestone gate
docs/M1_3_VERIFICATION.md         M actual commands, observations and findings
```

Prepared files from the previous phase remain: typed models/settings/wrapper; alembic.ini; frozen migration environment/template/revision; safety/schema tests; migration Make targets. No business API, seed, security role/view, authentication or runtime agent was added. Applying the real nexus_ai schema remains outside this test-only target guard and would require a separately reviewed/approved plan. No M1.4 work starts here.

## Acceptance criteria

| Criterion | Result | Supporting evidence |
| --- | --- | --- |
| Exact approved dependency versions / reviewed lock | PASS | Installed assertions, unchanged old package records, 35-package compatibility check, offline lock check. |
| Domain/audit models match architecture | PASS | Executed independent 25-column metadata and PostgreSQL tests. |
| Initial Alembic revision valid | PASS | One discovered head, frozen offline DDL, successful isolated upgrade. |
| Isolated migration/constraint tests | PASS | 39-test schema run includes all PG cases and reversal. |
| Actual PostgreSQL/model agreement | PASS | Empty comparison diff, Alembic check and final catalog assertions. |
| Indexes/defaults/identity/checks/FKs | PASS | Catalog observations and valid/invalid behavior tests above. |
| One approved test downgrade/re-upgrade | PASS | Guarded case passed once; later reversal flag disabled. |
| Real DB / M1.2 / Docker / secret preservation | PASS | Read-only before/after equality and selected resource/source/exclusion checks. |
| Backend and frontend regressions | PASS | Strict checks; 62+1 intentional skip after prior complete reversal; frontend build/test passes. |
| Independent final review | PASS | Approve with comments; no unresolved material finding in the authorized isolated scope. |

## Reviewer findings and remaining limits

The independent final reviewer approved with comments and found no unresolved material finding. It independently checked the installed pins/eight related lock additions with retained old records, single head, live 25-column/nine-check/two-FK/eight-secondary-index test schema, correct revision and zero rows. It verified current health/loopback binding, untouched nexus_ai catalog and M1.2 marker, 81 original files, 22 protected hashes, API/frontend/infrastructure preservation, ignored credentials/empty index, Proposed ADRs and 38 links. Recorded integration/reversal and regression evidence was reviewed without repeating mutating tests or the broad suite; live queries used read-only transactions and exposed no credentials.

**Verdict: approve with comments. M1.3 PASS for the authorized isolated scope.** The one static-gate defect encountered was test typing, corrected before any PostgreSQL mutation. No unresolved material runtime finding remains.

Limits: validation ran on this Apple Silicon host/PostgreSQL 16.15; no other-platform, crash-recovery, production-migration or full-stack memory benchmark is claimed. The owned test database is intentionally retained at head with zero application rows. The real application database intentionally remains empty/unmigrated. Both ADRs remain Proposed. Stop after M1.3.
