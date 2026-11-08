# M1.2 — PostgreSQL execution and verification

Date: 2026-11-07 (Africa/Tunis)
Status: **M1.2 PASS** — runtime and regression criteria passed; independent final read-only reviewer approved with comments and no unresolved material finding. No M1.3 work has begun. PostgreSQL remains running; no shutdown is implied by milestone completion.

## Scope, preparation and authorization

Confirmed root: `/Users/ihebsayah/Documents/my portfolio/nexus-ai`.

The prepared single-service Compose configuration, lifecycle commands and runbook passed devops implementation, narrow backend validation, QA and independent preparation review. Static validation and the full M1.1 Webpack regression command passed. Preparation-review documentation findings (stale roadmap wording and missing explicit network/name conflict inventory) were corrected and independently rechecked.

The owner explicitly authorized the documented credential creation, exact image/platform pull, conflict-gated PostgreSQL startup, runtime checks, isolated verification database/marker and **one normal restart**. Broader Docker access was requested after restricted startup failed; the owner reported starting the daemon manually and confirmed continuation. A separate broader local-network permission was requested after the host probe was denied and explicitly approved before retry. No permission denial was bypassed silently.

No existing credential file, container, network, volume or verification database was overwritten or deleted. No application table/schema, migration, role, view, MCP/LangGraph/Ollama integration, dependency change, destructive reset, prune, commit or push was introduced. Both ADRs remain **Proposed**.

## Versions and image identity

| Component | Observed result |
| --- | --- |
| Docker CLI | 29.1.2, build 890dcca |
| Docker Compose | v2.40.3-desktop.1 |
| Docker Engine | 29.1.2, Linux/aarch64 |
| Selected platform | linux/arm64/v8 |
| Image architecture/OS | arm64 / linux, from selected image inspect fields |
| PostgreSQL server | 16.15 (Debian 16.15-1.pgdg12+2) |
| Full SQL build identity | PostgreSQL 16.15 on aarch64-unknown-linux-gnu, gcc Debian 12.2.0-14+deb12u1, 64-bit |

Exact approved and pulled reference:

```text
postgres:16.15-bookworm@sha256:5264710be20f409750ac6dc4e5706dcef929c87e241605463f0f9aefa932a8d9
```

The pull exited 0 and reported that same digest. Selected image inspection reports `postgres@sha256:5264710be20f409750ac6dc4e5706dcef929c87e241605463f0f9aefa932a8d9`. No substitute image, tag upgrade or foreign-architecture fallback was used. [Official image metadata](https://raw.githubusercontent.com/docker-library/repo-info/master/repos/postgres/remote/16.15-bookworm.md) previously reported a 153,139,332-byte ARM64 compressed transfer; this estimate is distinct from observed image/disk metrics below.

## Preflight and resource conflicts

Initial restricted engine inspection exited 1 because the Docker socket was absent. `docker desktop start --timeout 60` exited 1 with a context deadline after log-directory permission denials. Restricted `docker desktop status` exited 1. Subsequent restricted inventory attempts encountered socket permission denials. The owner then manually started the daemon and approved broader Docker access; no second desktop-start command was executed.

Authorized broader read-only inspection found 45 existing containers (all stopped), 12 networks and 116 volumes. There were no NEXUS project-label, exact container-name, network-name or volume-name conflicts. `lsof -nP -iTCP:5432 -sTCP:LISTEN` initially exited 1 without output; no listener was observed. A second resource/port conflict check immediately before startup was also clear. No existing resource was assumed disposable.

Host free space at preflight was 76,264,759,296 bytes (71.03 GiB). Shared pre-existing `docker system df` output was: 76 images/156.3GB, 45 containers/11.95GB, 116 volumes/65.72GB and 466 build-cache records/73.16GB. These are shared Docker accounting figures, not NEXUS usage or an additive filesystem-total measurement.

Existing resource IDs were recorded outside the project. After execution, all original IDs remain. Exactly one container, one network and one named volume were added; only NEXUS PostgreSQL was running. Counts were 46 containers, 13 networks and 117 volumes. No pre-existing Docker resource was modified or deleted to resolve a conflict.

## Executed commands and outcomes

All commands below ran from the confirmed project root unless stated otherwise. Selected fields and password-free results were logged; no full resolved environment/configuration or full container inspection was printed.

| Command/check | Exit / observed outcome |
| --- | --- |
| Docker engine/container/network/volume inventory and `docker system df` | Exit 0 with approved broader access; conflict checks described above pass. Restricted failures are recorded in preflight. |
| Exclusive credential bootstrap from [runbook](../infra/README.md#controlled-execution-commands), followed by mode/ignore assertions | Exit 0. Created only new `infra/.env` with `NEXUS_DB_NAME=nexus_ai` and a cryptographically random 64-hex-character password, mode 0600. No password printed. |
| `make db-config` | Exit 0; actual ignored credential file consumed, resolved values suppressed. Synthetic quiet validation also passed separately. |
| `docker pull --platform linux/arm64/v8 postgres:16.15-bookworm@sha256:5264710be20f409750ac6dc4e5706dcef929c87e241605463f0f9aefa932a8d9` | Exit 0; exact digest downloaded. |
| `make db-up` | Exit 0. Creates only `nexus-ai-postgres-1`, network `nexus-ai_default` and volume `nexus-ai-postgres-data`; bounded startup wait reaches Healthy. Uses `--pull never --no-build`. |
| `make db-ready` | Exit 0; `127.0.0.1:5432 - accepting connections` inside the container. Rechecked after continuation; healthy. |
| Authenticated version/system SQL using runbook container-TCP command | Exit 0. Server 16.15, current user postgres, database nexus_ai, client 127.0.0.1. All observed host authentication rules use scram-sha-256. |
| Selected container/image inspect assertions | Exit 0. Healthy, native ARM64, exact digest, sole loopback binding, expected named mount, 512 MiB/1 CPU/128 MiB shared-memory limits. |
| Host Python SSLRequest probe, 3-second connect/read timeouts | Restricted attempt exit 1 (`PermissionError`). After explicit broader-network approval, retry exit 0; response `N`, PostgreSQL protocol reachable at host 127.0.0.1:5432. |
| `lsof -nP -iTCP:5432 -sTCP:LISTEN` after startup | Exit 0; Docker backend listening only on TCP 127.0.0.1:5432 (IPv4). |
| Isolated database-existence check, marker creation and before-marker assertion | Exit 0. Name absent; created nexus_m12_verify and non-secret database comment, no application table/role/view. Exact marker matched. |
| `docker compose --env-file infra/.env -f infra/compose.yaml restart --timeout 60 postgres` | Exit 0; exactly one normal restart command executed. No down, replacement, reset or cleanup. |
| Bounded post-restart readiness, health, marker and identity assertions | Exit 0. First check already healthy; observed verification wait 0.65s within the 90s cap. Same container ID, same named mount and exact marker. This is not a startup-performance benchmark. |
| `docker stats --no-stream ... nexus-ai-postgres-1`; container `du -sk` and `df -Pk` | Exit 0; point-in-time resource evidence below. |
| `make verify NEXT_BUILD_FLAGS=--webpack` after database restart | Exit 0. Both linters, formatting, both typecheckers, 4 backend tests (0.35s), 1 frontend test and production build pass. |
| Git exclusions, mode, empty-index and preservation assertions | Exit 0; mode0600 credential file ignored/untracked; all 69 pre-execution files preserved; protected/application hashes match. |

The exact authenticated SQL and persistence command forms are in the [runtime verification reference](../infra/README.md#runtime-verification-commands). SQL invocations expand `PGPASSWORD="$POSTGRES_PASSWORD"` **inside the container**, never putting the actual password into host command arguments or logged output. `PGCONNECT_TIMEOUT=3`, `psql -X --no-password`, and `ON_ERROR_STOP=1` bound/fail commands appropriately. The container TCP authentication check is not described as authenticated SQL from the host; the separate host protocol probe establishes host reachability only. Its `N` reply does not establish TLS security.

`make db-down` and `make db-logs` were not executed. They remain documented operational targets, not claimed execution evidence. No new dependency or host SQL client was installed.

## Health, network and storage evidence

Actual health: **healthy**, including after the approved restart and at the resumed final readiness check.

Actual published ports:

```json
{"5432/tcp":[{"HostIp":"127.0.0.1","HostPort":"5432"}]}
```

No all-interface or IPv6 published binding appears. Host lsof independently observed only 127.0.0.1:5432. This establishes the observed host binding, not protection against a compromised local account or all possible future configuration changes.

Actual data mount: type `volume`, name `nexus-ai-postgres-data`, driver `local`, writable destination `/var/lib/postgresql/data`. Mount identity is unchanged across the normal restart.

Authenticated SQL found zero non-system tables in nexus_ai and no roles named nexus_owner, nexus_app or nexus_tool. Only the official bootstrap administrator is used; application permissions and migrations remain deferred.

## Persistence evidence

A read-only database-existence query returned no nexus_m12_verify database. `CREATE DATABASE` therefore proceeded; it would have failed on an existing name. With autocommit and `ON_ERROR_STOP=1`, a non-secret COMMENT marker was written to that isolated database, avoiding application tables/schema or a persistent function/view.

```text
Before: nexus-m1.2-persistence-probe
After:  nexus-m1.2-persistence-probe
```

Container ID is unchanged. Observed start times changed from `2026-11-07T20:09:46.063895804Z` to `2026-11-07T20:11:33.779021798Z` (21:09:46 → 21:11:33 Africa/Tunis). The latest readiness check retains that second start time. The named mount and marker remained identical.

This proves persistence across the **one approved normal restart**, not container replacement, crash recovery, backup restore or disaster recovery. The isolated verification database/comment is intentionally left in place. No DROP, reset, down-with-volume-deletion or prune command ran.

## Actual resource observations

| Observation | Result and interpretation |
| --- | --- |
| Engine-reported memory capacity | 8,217,731,072 bytes, 8 CPUs; VM capacity, not actual host/VM RSS. |
| Configured PostgreSQL memory/CPU/shared memory | 536,870,912 bytes / 1,000,000,000 NanoCPUs / 134,217,728 bytes. |
| Docker stats sample after restart | 17.81 MiB / 512 MiB, 3.48% memory, 0.04% CPU, 6 PIDs, block I/O 0B / 17MB. A single sample, not a peak or workload benchmark. |
| Data-directory usage | `du -sk`: 70,516 KiB (about 68.9 MiB), after isolated database creation. Includes cluster/WAL storage, not just business data. |
| Guest data-filesystem `df -Pk` | 1,055,761,844 KiB total; 226,767,920 used; 775,290,500 available; 23% usage. Logical guest filesystem capacity/free space is not physical host free space; Docker disk growth remains host-constrained. |
| Docker-reported image Size | 153,159,624 bytes. Engine accounting value, not a claimed unpacked filesystem or total VM disk measurement. |
| Host preflight free space | 71.03 GiB, measured before image pull. |

No memory-fit claim for the complete 16 GB MVP stack is made. Ollama and other infrastructure were not started; full-stack measurements remain future work.

## Secret and source preservation

The secret file was absent at preflight and created with `O_EXCL` and mode0600. Subsequent stat and `git check-ignore --quiet --no-index infra/.env` assertions pass. `git ls-files` is empty: nothing tracked/staged, and no commit/push occurred. No real credential value appears in source examples, this report or verification output. No comprehensive secret-scanner audit is claimed.

The pre-execution snapshot covers 69 non-secret/non-generated files. All remain present. All 22 protected OpenCode/configuration/support files and 27 backend/frontend source/configuration/lockfiles retain their hashes. No private credential content was read for review; Compose and container-local tools consumed it only as required for the approved execution.

Only initial NEXUS resources were added; all 45 prior containers, 12 networks and 116 volumes retain their IDs. Only NEXUS PostgreSQL was running at the preservation check. No unrelated service was started or stopped by project commands.

## Files and local state changed

This execution phase changes documentation and creates the approved ignored secret/runtime state; it does not modify application code, dependency pins, lockfiles, Compose configuration or OpenCode configuration.

```text
nexus-ai/
├── infra/.env                   A ignored mode0600 local credential file; never committed
├── infra/README.md              M executed-state guidance and verification reference
├── README.md                    M current M1.2 status/evidence
└── docs/
    ├── M1_2_VERIFICATION.md     M actual commands, results, limitations and review
    └── ROADMAP.md               M M1.2 runtime completion status
```

Prepared M1.2 files remain: infra/compose.yaml, database Makefile targets and placeholder-only .env.example. Docker state added: exact approved image, one container, one network, one named volume and isolated verification database/comment. PostgreSQL remains running. No extra restart or shutdown was performed after continuation.

## Exit criteria

| Criterion | Result | Evidence |
| --- | --- | --- |
| Compose configuration valid | PASS | Actual local-file quiet validation exit0; prior normalized synthetic assertions. |
| PostgreSQL 16 running and healthy | PASS | Startup wait, readiness and selected actual health checks. |
| Authenticated database connectivity | PASS | Container TCP SQL succeeds; observed host rules use SCRAM. |
| Host database reachability | PASS | Approved direct host SSLRequest probe received PostgreSQL reply N. |
| Localhost-only published port | PASS | Actual inspect port map plus host lsof. |
| Named-volume attachment | PASS | Correct named writable data mount before/after restart. |
| Data survives approved normal restart | PASS | Exact marker, container identity and named mount preserved across one restart. |
| Actual resource observations | PASS | Single Docker stats, image accounting, du/df and capacity observations labeled above. |
| No secrets committed / excluded locally | PASS | Exclusive mode0600 file, Git ignore, empty index, no commit. |
| M1.1 regression checks | PASS | Post-restart complete Webpack suite exit0; 4 backend + 1 frontend tests. |
| Source/OpenCode/ADR/milestone boundary | PASS | Snapshot assertions; Proposed ADRs; no M1.3 implementation. |
| Documentation and final independent review | PASS | Independent reviewer approved with comments; no unresolved material finding. |

No unexecuted check is marked PASS. The default Turbopack sandbox limitation and existing HTTPX TestClient deprecation warning remain M1.1 limitations; the supported Webpack production build passed. No dependency was upgraded to suppress warnings.

## Final independent reviewer

The independent reviewer verified current healthy PostgreSQL 16.15, sole localhost binding, authenticated SQL persistence-marker access and zero application tables. It independently checked all 69 original files, 22 protected and 27 application hashes, credential mode0600/ignore/untracked status, empty Git index, Proposed ADRs and 34 local links/anchors. It reviewed recorded host-probe, one-restart persistence, resource and regression evidence without repeating the broad suite. Documentation cleanup was rechecked.

**Verdict: approve with comments; no unresolved material finding. M1.2 PASS.** Limits remain single resource samples, normal-restart-only persistence testing and existing M1.1 warnings; none is presented as broader verification. PostgreSQL remains running and the isolated verification database is retained. No further infrastructure mutation was performed for review. Stop before M1.3.
