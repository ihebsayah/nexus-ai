# M1.4 prepared security tests

No runtime tests have run during preparation. Default discovery skips every
`security_runtime` case before reading files or connecting. No fixture provisions
credentials, creates roles/schema, seeds data, or touches the M1.2/M1.3 databases.

Static verification from the repository root:

```sh
NEXUS_M13_ALLOW_DB_TESTS=0 NEXUS_M13_ALLOW_TEST_DOWNGRADE=0 NEXUS_M14_ALLOW_DB_TESTS=0 make backend-lint backend-typecheck backend-test
(cd backend && .venv/bin/mypy --strict security/migrations/env.py)
```

Pure tests cover offline/no-secret/no-connection behavior, exact target/cluster
identity, initial source freezing, empty target conflicts, catalog fingerprints
including same-named changed checks, partial deployment, role conflicts, secret
error redaction, credential gates and exact grant/view policy source. Source
assertions do not prove PostgreSQL syntax or effective deployed behavior.

After separate approval and completed deployment/credential provisioning only:

```sh
NEXUS_M13_ALLOW_DB_TESTS=0 NEXUS_M13_ALLOW_TEST_DOWNGRADE=0 \
NEXUS_M14_ALLOW_DB_TESTS=1 NEXUS_M14_ACK_TARGET_SCOPE=1 \
NEXUS_M14_DATABASE=nexus_ai \
NEXUS_M14_EXPECTED_CLUSTER_ID=7705524319955709990 \
NEXUS_M14_ADMIN_ENV_FILE="$PWD/infra/.env" \
NEXUS_M14_RUNTIME_ENV_FILE="$PWD/infra/.env.runtime" \
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 backend/.venv/bin/python -m pytest backend/tests/test_security_runtime.py -q
```

The runtime fixture requires exact target/cluster, mode0600 non-symlink runtime
credentials, already enabled runtime logins and all effective read-only catalog
checks. It stops on incomplete grants rather than continuing test mutations.
Actual app/tool connections prove authentication and login search paths; SET ROLE
alone cannot prove these. The owner role must remain NOLOGIN.

Positive tests check all three view projections and explicit audit INSERT without
RETURNING. Negative statements must fail with SQLSTATE `42501`; a syntax, missing
object or constraint error is not accepted as a permission denial. Tests cover
base/audit/migration reads, view/base writes, runtime DDL, role switching and grant
escalation, sequence reads and nextval, audit mutation, forced identity and RETURNING.
No permanent seed rows are needed for permission checks.

Transactions/savepoints roll back DML and unexpected DDL, including a mistakenly
successful forbidden operation. **Audit identity INSERT consumes a sequence value
even after rollback.** A mistakenly authorized nextval can also consume a value.
Separate execution approval must cover those sequence effects. No direct setval
negative statement is executed: a grant regression could reset persistent state
and rollback would not undo it. Its forbidden sequence UPDATE privilege is checked
by the effective read-only verifier instead. No DROP, database reset, downgrade or
sequence reset is a recovery step. A failed negative test is a security failure;
retain state and inspect before any separately approved forward repair.

Tests do not prove tenant isolation (views are unfiltered), all future database
objects/defaults, cloud security, audit retention, or cross-database confinement.
The SQL verifier checks creating-role global function defaults and absence of
runtime future-object default grants; an actual future-object default probe would
need separately reviewed owner DDL and is not included in this suite. Email remains
visible in the customer view. Retention remains an M5 policy gate.
