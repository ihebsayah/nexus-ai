# M1.4 — Database roles, views and security preparation (#011)

Date: 2026-11-08 (Africa/Tunis)
Status: **preparation PASS; M1.4 PARTIAL overall**. No persistent database mutation, credential creation or Docker lifecycle action was authorized or performed.

## Discovery and baseline

Confirmed project root: `/Users/ihebsayah/Documents/my portfolio/nexus-ai`.

Read AGENTS, Architecture/Requirements/Roadmap, M1.3 evidence, both Proposed ADRs, backend migration runbook/models/revisions/tests and infrastructure. A pre-edit snapshot covers 81 non-secret files. Frozen initial revision is 0001_initial_schema; existing online migration tools remain restricted to marked nexus_m13_test. No dependency installation is required for this preparation.

Read-only PostgreSQL catalog query and selected container inspection exited 0. Observed PostgreSQL 16.15, healthy, sole binding 127.0.0.1:5432; cluster identifier 7705524319955709990. nexus_ai is empty and owned by postgres; nexus_m13_test remains owned/marked from M1.3; nexus_m12_verify retains nexus-m1.2-persistence-probe. All three target roles are absent, no related memberships exist, no custom default ACLs exist. In nexus_ai, public is owned by pg_database_owner with PUBLIC USAGE and owner USAGE/CREATE; database datacl is NULL, invoking PostgreSQL defaults including PUBLIC CONNECT/TEMP. No password or pg_authid secret column was queried.

## Proposed security/deployment plan (before implementation)

The architect pass recommended exactly three roles: nexus_owner NOLOGIN, and nexus_app/nexus_tool initially NOLOGIN, all elevated attributes disabled and no memberships. Bootstrap administration must perform privileged role creation/ownership work; controlled migrations may SET LOCAL ROLE nexus_owner. No owner password is needed. Database ownership remains with postgres; designated application objects/public namespace ownership moves to nexus_owner only in a separately approved future deployment.

The three views preserve exact Architecture §10.3 projections and use owner-rights security_invoker=false with schema-qualified sources. They belong to the non-superuser owner role. Invoker views were rejected because they require base-table privileges, defeating tool SELECT-only-on-views. No row filters/RLS/security-definer functions or extra roles are introduced. security_barrier is unnecessary for these unfiltered projections; future row policies would require review. These views project columns and expose all rows; they are not tenant isolation.

nexus_tool receives only SELECT on v_customers/v_orders/v_shipment_events and required target database CONNECT/schema USAGE. nexus_app receives only column-level INSERT on the 11 audit writer columns, excluding generated id; no SELECT/RETURNING, UPDATE/DELETE/TRUNCATE or sequence privileges. PostgreSQL16 implicit ALWAYS identity insertion does not need direct sequence USAGE; future positive insertion and denied nextval/setval/read tests must verify this rather than grant excess sequence access.

Revoke target PUBLIC CONNECT/TEMP and schema rights; grant required target access explicitly. Revoke existing runtime/PUBLIC object rights before exact grants. Default privileges are scoped to creator nexus_owner in nexus_ai, with no blanket future runtime table grants. PUBLIC function EXECUTE defaults must be removed at the creator-global-within-database level; schema-only default revocation cannot subtract global defaults. Deployment uses explicit search_path and qualified SQL; SET ROLE does not load ALTER ROLE login GUC defaults, so tests must distinguish role simulation from actual authenticated login behavior.

Email decision: retain email in v_customers for documented exact lookup. The tool role can read that column/all view rows; suppressing email in answers/logs is application policy, not an enforced database restriction.

Important pending decision: target ACLs cannot remove PUBLIC CONNECT/TEMP inherited in untouched databases. This is a nexus_ai object/DDL boundary, not cluster-wide connection/DDL isolation. Before enabling runtime LOGIN, the owner must explicitly accept that limitation or separately approve an HBA/other-database isolation plan. No protected database ACL or HBA change is silently introduced here.

Deployment source will be additive administrator SQL/bootstrap orchestration, outside ordinary restricted Alembic migrations. Preserve the frozen initial revision, existing single head and M1.3 target guard. Prepare a separate explicit initial-only application of exactly 0001_initial_schema to empty nexus_ai, followed by roles/ownership/defaults/views/grants, catalog verification and separately approved credentials/login/tests. Existing-role/object conflicts must stop, not be reused or overwritten. Recovery is fail-closed, retaining committed schema and disabled roles with forward repair; no automatic reset/drop/downgrade or REASSIGN OWNED.

## Sequential specialist work

1. architect: trust-boundary/options analysis (read-only), completed.
2. data-engineer: role/grant/view SQL and policy source, completed.
3. backend: safe deployment integration and inspection commands, completed.
4. QA: static/security test design and non-mutating validation, completed.
5. reviewer: independent read-only preparation assessment, completed (PASS for preparation).

## Evidence and approval boundaries

Role/view creation, real initial migration, grants/ownership/default-privilege changes, credential generation/rotation/LOGIN activation and runtime privilege test writes are all unexecuted and require separate approval. Existing M1.3 test schema must not be downgraded or altered by this preparation. Static code/assertion and read-only evidence will be recorded below; no runtime privilege test will be marked PASS unless executed under a later authorization.

## Prepared deployment assets

- `backend/security/apply_security.sql`: administrator transaction with fresh-state guards, three NOLOGIN roles, ownership/default ACL policy, exact views and runtime grants.
- `backend/security/verify_security.sql`: read-only effective table/column/database/schema/sequence rights, memberships, ownership, view projections/options and default ACL assertions.
- `backend/src/nexus/persistence/security_admin.py`: offline plan/render; read-only deployment check; separately guarded future initial-only schema application and security transaction.
- `backend/security/migrations/env.py`: isolated initial-only Alembic environment reusing frozen 0001; original M1.3 environment remains unchanged.
- `backend/src/nexus/persistence/runtime_credentials.py`: unexecuted provisioning source with explicit execution/scope gates, fixed exclusive ignored mode0600 runtime file, two generated runtime passwords and atomic password/LOGIN transaction. No owner password.
- `backend/security/README.md`: exact proposed commands, scope, permissions, ordering and recovery.
- Makefile: additive offline `security-plan` / `security-sql` targets. No deployment is implicit in normal checks.
- `.env.example`: removes obsolete owner-password placeholder because the owner stays NOLOGIN. No real credential is included.

The CLI freezes the initial migration SHA256 and accepts no downgrade or new revision. Initial application requires the observed fresh target and no extra user relations/functions/types/schemas/defaults/roles. A catalog fingerprint recorded after successful initial deployment must match before the security stage; it includes check bodies, FK/PK/index definitions, columns/types/nullability/defaults/identity. This supplements Alembic comparisons, which alone do not compare check semantics. A trusted concurrent administrator is outside these guard guarantees.

## Separate future execution proposal — DO NOT EXECUTE NOW

Exact command lines live in [the deployment runbook](../backend/security/README.md#prepared-backend-entry-points) and [credential procedure](../backend/security/README.md#future-credential-procedure--execution-approval-gate). All target `127.0.0.1:5432`, exact database `nexus_ai`, observed cluster `7705524319955709990`; bootstrap administration uses the existing private file without displaying it.

| Order / operation | Proposed command | Expected mutations / permission | Preconditions, stop and recovery |
| --- | --- | --- | --- |
| 1. Catalog/identity baseline | `backend/.venv/bin/python -m nexus.persistence.security_admin check --database nexus_ai --expected-cluster-id 7705524319955709990 --env-file infra/.env` | Read-only; bootstrap catalog access | Current NOT_DEPLOYED/exit 2 is expected. Unexpected partial state or identity mismatch stops; preserve M1.2/M1.3. |
| 2. Frozen initial schema | Same CLI `initial-apply --database nexus_ai --expected-cluster-id 7705524319955709990 --env-file infra/.env --execute` | Creates four domain/audit tables, tracking table, constraints/indexes/identity sequence; bootstrap DDL | Empty fresh target, frozen source, no roles. Transaction failure rolls back; lost acknowledgement requires inspection. Retain committed schema; record emitted fingerprint only after successful commit. No downgrade/reset. |
| 3. Roles, ownership, defaults, views and grants | Same CLI `apply --database nexus_ai --expected-cluster-id 7705524319955709990 --expected-schema-sha256 "$APPROVED_INITIAL_SCHEMA_SHA256" --env-file infra/.env --execute` | Three cluster roles NOLOGIN, target ownership/ACL/defaults, three views, login search-path settings; superuser administrator | Fingerprint from successful step 2; fresh role names, exact empty schema/ACLs. SQL owns one BEGIN/COMMIT. Conflict stops without reuse. Before commit rollback; after commit retain disabled roles and repair forward through reviewed SQL. |
| 4. Effective policy and ownership | Repeat exact step 1 command | Read-only assertions; no mutation | All assertions true required. Failure keeps activation blocked; inspect rather than rerun creation blindly. Includes owner, view contract, defaults, PUBLIC and column ACLs. |
| 5. Credentials and runtime LOGIN | `backend/.venv/bin/python -m nexus.persistence.runtime_credentials provision --database nexus_ai --expected-cluster-id 7705524319955709990 --env-file infra/.env --runtime-env-file infra/.env.runtime --acknowledge-target-scope --execute` | Exclusively creates ignored mode0600 file; sets two SCRAM passwords and enables both runtime LOGIN roles in one transaction; bootstrap superuser | Separate approval must explicitly accept target-scoped cross-database limitation or replace this step with reviewed isolation. Effective policy passes, both roles NOLOGIN/no sessions, file absent, Git ignores path, no unreviewed extensions/preload hooks. No owner password. Failure retains any file; commit-ack loss leaves unknown outcome requiring read-only inspection. Never overwrite/rotate/reset automatically. |
| 6. Real authenticated positive/negative tests | Exact opt-in pytest command recorded with test source below | Only separately approved rollback-scoped probes; audit identity advancement persists across rollback | Deployed policy, successful credentials/LOGIN, cluster/target guards and explicit test approval. All live tests are unexecuted here. Any unexpected permission succeeds -> stop; no automatic grants/reset to make tests pass. |

The credential transaction suppresses statement/duration/sampling/error/debug/parameter logs before password SQL; unknown extensions or preload hooks refuse execution. Values stay out of argv, stdout, driver error text and examples. Session controls do not protect against trusted administrators, external server/OS monitoring or process memory. No claim of absolute secret invisibility is made. NOLOGIN does not terminate established sessions; termination would need separate approval. A nontransactional file may remain after failed database changes; preserve it and inspect, never silently regenerate.

## Initial observed static/read-only results

- `make migration-heads migration-history migration-sql security-plan`: exit 0; single head `0001_initial_schema`; offline schema SQL rendered; plan explicitly excludes implicit deployment/credentials.
- Read-only `security_admin check` command in step 1: exit 2, `NOT_DEPLOYED: nexus_ai is empty and designated roles are absent.` This is expected baseline evidence, **not** a deployed security PASS.
- `make frontend-lint frontend-typecheck frontend-test frontend-build NEXT_BUILD_FLAGS=--webpack`: exit 0. ESLint, generated route types/TypeScript, one Vitest test and Next.js 16.4.5 production build passed; `/` and `/_not-found` generated. Build output is local ignored generated material.
- `runtime_credentials --help`: exit 0; help only, no credential generation or connection.
- Read-only preservation probe (two PostgreSQL transactions through existing Docker socket): exit 0; captured nexus_ai/database comments/ACLs/roles/defaults and M1.3 revision/relations/owners/ACLs/zero app row counts exactly equal pre-edit snapshots. M1.2 marker remains `nexus-m1.2-persistence-probe`.
- `git check-ignore infra/.env infra/.env.runtime backend/.venv frontend/node_modules frontend/.next frontend/tsconfig.tsbuildinfo`: exit 0; every listed path ignored. Runtime file is not created.

SQL files have been rendered/source-checked only. PostgreSQL has not parsed or executed their DDL/DCL; preparation cannot establish deployed grants or runtime behavior. Remaining backend/security checks and final review follow below.

## Backend and prepared-test evidence

`NEXUS_M13_ALLOW_DB_TESTS=0 NEXUS_M13_ALLOW_TEST_DOWNGRADE=0 NEXUS_M14_ALLOW_DB_TESTS=0 make backend-lint backend-typecheck backend-test` exited 0: Ruff check/format passed (26 Python files), strict mypy passed (23 source files), pytest **61 passed, 82 skipped**, one existing Starlette deprecation warning. Separate `(cd backend && .venv/bin/mypy --strict security/migrations/env.py)` exited 0 (one file). Early local formatting findings were corrected before the successful checks; no failed iteration is represented as a pass.

New test modules: `test_security_admin.py`, `test_runtime_credentials.py`, `test_security_runtime.py`; pytest adds the `security_runtime` marker only. Pure tests use fake secrets/mocks, generate no real credentials and exercise no database state. Future tests are independently gated, exact-target/cluster authenticated checks and require actual effective policy before any probes.

Skipped counts: 36 existing M1.3 PostgreSQL tests and 46 new M1.4 runtime tests. All 46 live permission tests remain **BLOCKED / unexecuted** in this preparation phase. [Testing runbook](../backend/security/TESTING.md) records the exact future opt-in command and expected effects. Positive audit INSERT is rolled back but advances the identity sequence; an unexpectedly permitted nextval can also advance it. A direct setval test is deliberately omitted because rollback cannot undo a reset; effective sequence UPDATE denial is catalog-checked instead. No runtime probe or future-object default DDL was executed.

## Final preparation verdict

| Gate / M1.4 exit criterion | Status | Evidence / limitation |
| --- | --- | --- |
| Discovery, proposed design and sequential specialist preparation | PASS | Architect → data-engineer → backend → QA → independent reviewer, sequential. |
| Additive roles/views/security/deployment/test source | PASS for preparation | Guarded source and concrete execution proposal exist; frozen M1.3 revision unchanged. |
| Non-mutating lint, strict types, pure tests, offline migrations and frontend regressions | PASS | Executed commands above; no live test substituted for a skip. |
| Effective least-privilege grants enforced in PostgreSQL | BLOCKED | No roles/views/grants deployed; current read-only checker reports NOT_DEPLOYED. |
| Append-only audit insertion proven for application role | BLOCKED | Prepared authenticated tests unexecuted; no runtime role exists. |
| Owner limitations, email exposure and retention documented | PASS for documentation | Owner/superuser can alter audit; email/all rows visible to tool; retention/deletion policy remains M5. |
| Credential provisioning/login and positive/negative permission tests | BLOCKED | Source only. Separate execution approval and cross-database scope decision required. |
| Preservation of M1.2/M1.3 and protected development configuration | PASS for observed catalog baseline | Exact captured catalog/marker/revision/row counts unchanged; source hash review below. |
| Independent final review | PASS for preparation | No material source-level finding; independent narrow tests 34 passed / 46 skipped, exit 0. |

Overall **M1.4 PARTIAL: preparation completed and independently reviewed; runtime execution gates remain BLOCKED**. This does not mark roadmap runtime exit criteria complete. No M1.5 work is authorized or started.


## Independent reviewer findings and corrections

Reviewer verdict: **PASS for preparation; PARTIAL overall**, no unresolved material source-level findings. Reviewed role/view privileges, PUBLIC/default/column ACL handling, migration ordering and target guards, credential storage/logging/failure lifecycle, negative-test intent and actual-versus-unexecuted evidence. Independently ran narrow pytest: **34 passed, 46 skipped**, exit 0; live tests remain blocked. No runtime mutation or secret generation occurred during review.

Material issues resolved during preparation before final review:

- Initial empty-target checks now include functions/types/relations/custom schemas/defaults and expected baseline ACLs, repeated inside the initial transaction.
- Named checks alone were insufficient to detect changed semantics; the initial deployment now records a catalog fingerprint required before security application.
- A credential plan with only a nonexistent future interface was replaced by concrete guarded source. It remains entirely unexecuted and requires separate approval.
- Removed the obsolete owner-password placeholder; nexus_owner is NOLOGIN with no password.
- Kept direct setval probes out of live tests because a failed security boundary could reset state irreversibly; catalog UPDATE denial is prepared instead.

Reviewer comments retained as explicit limitations: cross-database PUBLIC access, visible customer email, absent row isolation, password/commit acknowledgement uncertainty, and SQL/runtime behavior awaiting real execution. No reviewer approval is presented as permission to deploy.

## File and state preservation

A Python SHA256 comparison against the pre-edit 81-file snapshot exited 0: all originals still exist; only six intended original files changed: Makefile, README.md, .env.example, backend/pyproject.toml (marker only), docs/ARCHITECTURE.md and docs/ROADMAP.md. Eleven new source/test/runbook/evidence files were added. All 22 protected configuration/skill files, frozen initial revision, original migration environment/settings, models, application scaffolds, both lockfiles, infrastructure configuration and M1.2/M1.3 reports are unchanged. Independent reviewer repeated the source/snapshot comparisons.

Existing infra/.env remains mode0600 and ignored; infra/.env.runtime does not exist. Git status exited 0 and reports the pre-existing untracked repository layout (there are no tracked/staged files); git ls-files remains empty. No commit or push was performed. Both ADR status checks show Proposed. A local Markdown file-link check exited 0 for 54 links (anchor fragments not checked by that script).

Additions:

```text
backend/
  security/
    README.md
    TESTING.md
    apply_security.sql
    verify_security.sql
    migrations/env.py
  src/nexus/persistence/
    security_admin.py
    runtime_credentials.py
  tests/
    test_security_admin.py
    test_runtime_credentials.py
    test_security_runtime.py
docs/M1_4_VERIFICATION.md
```

No schema, roles, views, credentials, application data, MCP/LangGraph/Ollama integration, dependency installation or Docker lifecycle change was introduced in PostgreSQL/runtime. Big Pickle and OpenCode configuration remain unchanged. This concludes **M1.4 preparation only**, with no M1.5 work. Separate approval must cover each future persistent operation and the credential activation scope decision before execution.


Final repeat limitation: after review, the final source-preservation check exited 0
(all 81 originals retained, only six intended originals changed, runtime credentials
absent, existing secret mode0600, empty index). A redundant repeat of the read-only
Docker/PostgreSQL comparison was **not executed**: automatic permission review
did not finish before its deadline. This is an approval-review timeout, not a
database test failure. The earlier executed comparison exited 0 with exact matching
before/after catalogs; the independent reviewer checked those saved snapshots. No
database-changing command ran afterward. No success is claimed for the timed-out
repeat, and no broader permission retry or additional execution is needed for this
preparation-only result.
