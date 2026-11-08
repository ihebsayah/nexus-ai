# M1.4 target-scoped database security plan

Preparation only: **neither SQL file has been executed**. Deployment, credentials,
LOGIN activation and runtime privilege tests need a separate explicit owner approval.
The frozen `0001_initial_schema` revision and existing M1.3 target guards stay intact.

## Contract and choices

The database remains owned by bootstrap `postgres`. Exactly three new roles are
proposed, initially NOLOGIN, NOSUPERUSER, NOCREATEDB, NOCREATEROLE, NOINHERIT,
NOREPLICATION and NOBYPASSRLS, with no memberships in either direction:

| Role | Owned objects / effective capability in nexus_ai |
| --- | --- |
| nexus_owner | Owns public, four app tables, audit identity sequence, migration tracking and the three views; controlled migrations only. Remains NOLOGIN; no owner password. |
| nexus_tool | CONNECT, schema USAGE and SELECT on exactly the three views. No base/audit/version table or sequence privileges, schema CREATE, database CREATE/TEMP or grant options. |
| nexus_app | CONNECT, schema USAGE and INSERT on 11 audit writer columns, excluding generated id. No table SELECT, RETURNING, UPDATE/DELETE/TRUNCATE/REFERENCES/TRIGGER, sequence access, DDL or grant options. |

The audit writer columns are request_id, event_type, actor_id, tool_name,
args_hash, decision, row_count, latency_ms, model, error_code and created_at.
Normal INSERT must omit id and must not request RETURNING. A future SQLAlchemy
writer must use Core `insert(...).inline()` or explicit INSERT without RETURNING;
an ORM flush that implicitly returns an id is incompatible with this policy.
Do not add SELECT merely to accommodate an ORM convenience.

Views have the exact documented projections and schema-qualified sources:

- v_customers: id, name, email from public.customers.
- v_orders: id, customer_id, status, created_at, expected_delivery_at from public.orders.
- v_shipment_events: id, order_id, event_type, occurred_at from public.shipment_events.

They use ordinary owner-rights behavior, explicitly security_invoker=false, owned
by the non-superuser nexus_owner. security_invoker=true would require forbidden
underlying table SELECT rights. The views contain no filters and provide no
tenant/row isolation. No security barrier is needed for an unfiltered projection;
adding row filters, RLS or other policy requires a new security review. Table
owners normally bypass RLS even without BYPASSRLS; this design does not claim
future RLS protection. Simple views are automatically updatable, so runtime roles
receive no view write rights.

The email column remains visible to nexus_tool for documented exact lookup.
Omitting it from user-facing answers/logs is an application policy, not database
column or row enforcement. No extra role, RLS or security-definer function is added.

## PUBLIC, defaults and search path

The target database loses PUBLIC CONNECT/TEMP and public loses PUBLIC privileges.
Only explicit runtime CONNECT/schema USAGE and object capabilities are restored.
Both table and column ACLs are revoked before exact grants: revoking table ACLs
alone does not remove a separate column grant. Runtime membership absence is
checked explicitly; NOINHERIT alone does not prohibit PostgreSQL 16 SET ROLE rights.

Defaults apply to objects **created as nexus_owner in nexus_ai**. There are no
automatic future table/sequence grants to PUBLIC or runtime roles. PUBLIC function
EXECUTE is revoked globally for that creating role in this database: a per-schema
revoke cannot subtract a global default. Defaults do not fix existing objects or
apply to objects created as another role. Controlled future migrations must SET
LOCAL ROLE nexus_owner before object creation.

Actual runtime logins will default to search_path=pg_catalog, public. This is
defense in depth, not an immutable user setting. SQL must remain schema-qualified;
runtime CREATE/TEMP denial prevents shadow-object creation in the target database.
SET ROLE does not load role login GUC defaults, so migration sessions explicitly
set their local search path and tests must distinguish SET ROLE from real logins.

No sequence ACL is granted. PostgreSQL 16 identity generation uses an internal
NextValueExpr without a direct sequence-permission check, unlike explicit nextval.
Future live tests must prove audit INSERT omitting id succeeds and direct sequence
SELECT/nextval/setval fails; preparation does not claim these tests passed.

## Important cross-database limitation and LOGIN gate

Roles are cluster-wide. PUBLIC CONNECT/TEMP defaults in untouched postgres,
nexus_m12_verify and nexus_m13_test can still be inherited by a future LOGIN role.
Target database ACLs cannot express a per-role DENY that overrides PUBLIC elsewhere.
This is a **nexus_ai object/DDL boundary**, not cluster-wide confinement.

All roles remain NOLOGIN after apply_security.sql. **Stop before runtime LOGIN
activation unless the owner explicitly acknowledges this target-scoped limitation
or separately approves an HBA/other-database isolation plan.** No HBA modification,
other-database ACL change or credential is prepared implicitly by the SQL files.
Existing protected databases must not be altered to hide the limitation.

## Deployment ordering and permissions (future approval only)

1. Read-only identity/preservation preflight: expected PostgreSQL 16 cluster,
   empty nexus_ai, no designated roles/views, intact M1.2 marker/M1.3 schema.
2. Separately approved, initial-only application of **exact revision 0001** to
   empty nexus_ai through a dedicated guarded entry point; retain M1.3-only guards.
3. Bootstrap administrator runs apply_security.sql as one transaction. It checks
   exact target/admin/initial head, fresh roles, known objects/owners/ACLs, no
   extra schema/functions/RLS and empty app tables. It creates disabled roles,
   transfers designated ownership, creates owner-rights views, sets defaults,
   removes broad rights and grants the exact capabilities. No password appears.
4. Run verify_security.sql inside an explicitly READ ONLY transaction. Every
   result must be true. It checks actual effective table/column privileges,
   grant options, memberships, ownership, views, default ACLs and login search
   path configuration. Runtime LOGIN status is a separate phase-specific check;
   nexus_owner must never be a LOGIN role.
5. Only under a separate credential/activation approval: use exclusive mode0600
   ignored storage, generate independent cryptographic runtime passwords without
   display, never create an owner password, and keep roles disabled during any
   partial failure. Resolve/acknowledge cross-database scope before activation.
6. Run separately approved authenticated positive/negative tests. Use actual
   connections for login defaults and authentication; SET ROLE tests cannot
   prove those properties. No security mutation/test runs during preparation.

Cluster-role creation and ownership/default changes require the documented
bootstrap administrator, not an ordinary restricted Alembic connection. The SQL
therefore remains an additive version-controlled administrator deployment asset,
outside Alembic. No new revision, head change or editing of frozen 0001 is needed.

apply_security.sql contains its own BEGIN/COMMIT and bounded lock/statement
timeouts. The orchestrator must execute the whole script as its transaction unit;
do not run statements individually in autocommit or wrap conflicting transaction
management around it. The dedicated caller must first verify the complete frozen
schema contract and server identity; SQL preflight independently rejects unknown
target state. The script aborts on existing role names, rather than reusing them.

Before commit, any error rolls the transaction back. After a lost acknowledgement,
inspect the live state read-only; never blindly rerun creation or delete roles.
After a successful commit, retain the schema and disabled roles while investigating
any failed verification. Repair forward through separately reviewed SQL. No DROP,
REASSIGN OWNED, downgrade, reset or automatic destructive rollback is provided.
Credential file/server synchronization is handled by the prepared, unexecuted
provisioner below; do not interpolate secrets into logged SQL/argv.

## Required future runtime tests

- Tool: exact view SELECT succeeds; table/audit/version reads, view writes,
  table writes, schema/TEMP creation, ownership changes, SET ROLE, membership
  escalation, grant-option operations and sequence reads/nextval/setval fail.
- App: explicit audit writer INSERT without id/RETURNING succeeds; business
  reads/writes, audit reads/update/delete/truncate, forced identity override,
  sequence use, DDL and escalation fail.
- Verify actual grants including PUBLIC/memberships/column ACLs, not just role
  names. Check owner-rights view definitions and no unexpected view write grants.
- Under separate test-mutation approval, rollback-only owner-created probes may
  verify future-object defaults. No seed rows or permanent test objects.

## PostgreSQL 16 references

- [View privileges and security_invoker](https://www.postgresql.org/docs/16/sql-createview.html)
- [View owner-rights security](https://www.postgresql.org/docs/16/rules-privileges.html)
- [Role membership and SET rights](https://www.postgresql.org/docs/16/role-membership.html)
- [SET ROLE and role settings](https://www.postgresql.org/docs/16/sql-set-role.html)
- [Column/table privileges](https://www.postgresql.org/docs/16/ddl-priv.html)
- [Creating-role default privileges](https://www.postgresql.org/docs/16/sql-alterdefaultprivileges.html)
- [Identity expression construction](https://github.com/postgres/postgres/blob/REL_16_STABLE/src/backend/rewrite/rewriteHandler.c)
- [Identity execution](https://github.com/postgres/postgres/blob/REL_16_STABLE/src/backend/executor/execExprInterp.c)
- [Sequence ACL checks](https://github.com/postgres/postgres/blob/REL_16_STABLE/src/backend/commands/sequence.c)

Security deployment evidence is source-only: no DDL/DCL execution, login/credential creation,
effective live grant test or persistent security change has been performed here.

## Prepared backend entry points

Use from the project root. These two commands are offline and do not read secrets:

```sh
make security-plan
make security-sql
backend/.venv/bin/python -m nexus.persistence.security_admin --help
```

The following commands are **proposed and unexecuted**. Each mutating command
needs separate owner approval; `--execute` is an operator acknowledgement, not a
substitute for approval. No command creates a database or starts infrastructure.
The expected cluster identifier below is the observed M1.2 cluster; a mismatch
must stop for investigation rather than substituting a freshly queried identifier.

```sh
# Read-only: NOT_DEPLOYED/exit 2 on current empty target; no credential output.
backend/.venv/bin/python -m nexus.persistence.security_admin check --database nexus_ai --expected-cluster-id 7705524319955709990 --env-file infra/.env
# Future initial schema transaction only: exact frozen 0001, empty target only.
backend/.venv/bin/python -m nexus.persistence.security_admin initial-apply --database nexus_ai --expected-cluster-id 7705524319955709990 --env-file infra/.env --execute
# Future separate security transaction; leaves all three roles NOLOGIN.
backend/.venv/bin/python -m nexus.persistence.security_admin apply --database nexus_ai --expected-cluster-id 7705524319955709990 --expected-schema-sha256 "$APPROVED_INITIAL_SCHEMA_SHA256" --env-file infra/.env --execute
# Then repeat the read-only check above; all assertions must pass.
```

The separate initial-only Alembic environment reuses the original version location,
requires the frozen file SHA256 and exactly one revision, accepts only revision
0001_initial_schema through the guarded caller, and offers no downgrade route.
The existing disposable-only Alembic configuration/environment is unchanged.
Both future mutation stages check target/administrator/cluster identity first.
Initial-only application requires no public relations/functions/types, extra user
schema, custom defaults or designated roles and the observed fresh database/schema
ACLs; it repeats this check inside the migration transaction. Security application checks metadata types,
defaults, indexes and foreign keys through Alembic and named check constraints,
then the SQL independently checks owners, object inventory, ACLs and empty tables.
The initial-only application emits a non-secret catalog SHA256; record it only
after successful commit and set APPROVED_INITIAL_SCHEMA_SHA256 to that reviewed
value for security application. This fingerprint covers deparsed check/FK/PK
bodies, columns/types/nullability/defaults/identity and indexes, and security apply
refuses any mismatch. Named-check comparison alone does not prove equivalence.
Review any external schema mutation before deployment. Do not treat these checks
as protection against a concurrent trusted administrator changing the cluster.

Exit codes: 0 successful source command/all catalog assertions true; 1 suppressed
connection/SQL failure or failed catalog assertion; 2 safety refusal or NOT_DEPLOYED.
Driver errors and connection URLs are never printed. The read-only checker first
requires all designated roles and relations, avoiding unsafe missing-role lookups
inside the post-deployment SQL. Partial state stops for manual read-only inspection.

## Future credential procedure — execution approval gate

The prepared `runtime_credentials` module is **unexecuted**. Import/help and mocked
unit tests do not create credentials. Do not activate LOGIN by adapting deployment
commands or typing password-bearing ALTER ROLE statements. After successful catalog
verification and separate explicit approval, the exact proposed command is:

```sh
# Persistent secret file plus both runtime PASSWORD/LOGIN changes; UNEXECUTED.
backend/.venv/bin/python -m nexus.persistence.runtime_credentials provision --database nexus_ai --expected-cluster-id 7705524319955709990 --env-file infra/.env --runtime-env-file infra/.env.runtime --acknowledge-target-scope --execute
```

It repeats identity/catalog checks, proves runtime roles
are disabled with no live runtime sessions, requires target-scope acknowledgement,
and generates two independent
`secrets.token_urlsafe(48)` values in process. It uses `os.open` with O_CREAT|O_EXCL,
O_NOFOLLOW and mode 0600 for ignored infra/.env.runtime; write only app/tool
credentials and fixed local target settings, with no owner credential. Never
replace an existing file, display values, put them in argv, source shell text or
print an environment. A failure before commit rolls back both password/LOGIN changes; retain any created
file and inspect roles read-only. A lost commit acknowledgement has unknown outcome:
do not assert NOLOGIN or blindly retry. Never regenerate/overwrite to hide a
synchronization issue. A pre-existing file causes refusal before credential loading.

Before any password operation, the prepared tool rejects extensions other than
plpgsql and any preload libraries, then suppresses statement, duration, sampling,
error-statement, debug-plan and parameter logging for its transaction. It sets SCRAM
password encryption. Fixed generic failure messages omit driver exceptions. Utility
PASSWORD clauses use psycopg SQL composition through the driver, avoiding SQLAlchemy
exception rendering of secret SQL. These are source controls awaiting runtime proof. Server
logging outside session controls, privileged monitoring, trusted administrators and
OS/process-memory access remain residual risks. LOGIN must remain disabled until
catalog verification passes and the owner accepts PUBLIC CONNECT/TEMP exposure in
untouched databases (or separately approves isolation). Password assignment and
LOGIN enabling share one controlled transaction for both runtime roles. The secret
file is outside that transaction and is deliberately retained after any failure.
NOLOGIN does not terminate already authenticated sessions; recovery must inspect
connections and request separate approval for any termination. No owner password,
HBA change, other-database ACL change or destructive rollback is authorized.
