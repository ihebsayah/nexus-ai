# Local PostgreSQL infrastructure (M1.2)

The owner authorized initial credential creation, the pinned image pull, PostgreSQL startup and one normal restart. Those runtime actions have executed; see the verification record for observed results and the completed independent review. Future lifecycle changes still require explicit approval. No schema, migration, application role, view or runtime integration is part of M1.2.

## Image and Apple Silicon

Pinned reference:

```text
postgres:16.15-bookworm@sha256:5264710be20f409750ac6dc4e5706dcef929c87e241605463f0f9aefa932a8d9
```

The [official image list](https://raw.githubusercontent.com/docker-library/official-images/master/library/postgres) lists this patch and arm64v8. [Published image metadata](https://raw.githubusercontent.com/docker-library/repo-info/master/repos/postgres/remote/16.15-bookworm.md) gives the immutable index above and arm64/v8 transfer size 153,139,332 bytes (153.1 MB compressed). Compose explicitly selects `linux/arm64/v8`. These are remote metadata observations, not a pull or local runtime verification.

The Bookworm variant follows the documented architecture while avoiding an unpinned major-only tag. A digest is reproducible but does not receive later security rebuilds automatically; review patch/digest updates separately. Alpine is smaller but changes libc/base behavior; native PostgreSQL avoids Docker VM overhead but sacrifices this Compose-based reproducibility. Neither alternative is introduced here.

## Prerequisites and credentials

- Docker CLI and Compose v2; Docker engine must be available. Do not assume it is started.
- Host port `127.0.0.1:5432` free; inspect existing project containers and volume before execution. If names or data already exist, stop and report the conflict.
- After explicit owner approval, create a new `infra/.env` with restricted permissions and **only** `NEXUS_DB_NAME=nexus_ai` and a fresh `NEXUS_DB_ADMIN_PASSWORD`. Use exclusive creation so an existing file is never overwritten. Do not copy the whole root example or print the password.
- `.env.example` contains a `replace-me` placeholder, which must never be used as a real password. `.gitignore` already excludes `infra/.env`; verify with `git check-ignore infra/.env`.

Compose requires the database name and password, with no default password. It initializes only the built-in `postgres` superuser and the empty development database. Do not use that superuser for the future application. Future `nexus_owner`, `nexus_app` and `nexus_tool` privileges belong to M1.4. [Official image environment behavior](https://hub.docker.com/_/postgres) applies initialization settings only to an empty data directory; changing the file does not rotate an existing database password.

Do not display full `docker compose config`, `docker inspect` or environment output: they may contain the password. Use `config --quiet` and narrowly selected inspect fields. `pg_isready` establishes server readiness, not successful password authentication. Verify authenticated SQL separately after approval; do not put the password in command arguments or recorded output.

## Controlled execution commands

Run from the project root. Each state-changing operation needs approval; target existence does not authorize execution.

```bash
# Only if explicitly approved and Docker Desktop is not already running:
docker desktop start --timeout 60

# Reinspect the now-available engine before changing project resources:
docker ps -a --filter label=com.docker.compose.project=nexus-ai
docker ps -a --filter name=nexus-ai-postgres-1
docker network ls --filter name=nexus-ai_default
docker volume ls --filter name=nexus-ai-postgres-data
lsof -nP -iTCP:5432 -sTCP:LISTEN

# After separate explicit approval: create credentials exclusively, never print them.
python3 - <<'ENV_SETUP'
import os
import secrets

fd = os.open("infra/.env", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, "w") as file:
    file.write("NEXUS_DB_NAME=nexus_ai\n")
    file.write("NEXUS_DB_ADMIN_PASSWORD=" + secrets.token_hex(32) + "\n")
print("Created ignored infra/.env with mode 0600; password omitted.")
ENV_SETUP

# Configuration validation suppresses resolved credentials:
make db-config

# Separately approved image download, selecting native Apple Silicon:
docker pull --platform linux/arm64/v8 postgres:16.15-bookworm@sha256:5264710be20f409750ac6dc4e5706dcef929c87e241605463f0f9aefa932a8d9

# Separately approved startup; no automatic image pull or build:
make db-up

# Read-only status/log/readiness checks:
make db-status
make db-logs
make db-ready

# Only with explicit approval for a normal restart/persistence check:
docker compose --env-file infra/.env -f infra/compose.yaml restart --timeout 60 postgres

# Only with shutdown approval; retains the named volume:
make db-down
```

The Docker Desktop startup affects the local engine, which may make existing unrelated resources active according to their own restart policies. Recheck those resources after startup. Project startup creates `nexus-ai-postgres-1`, network `nexus-ai_default` and named volume `nexus-ai-postgres-data`; it publishes TCP only at `127.0.0.1:5432`. Existing resources cannot be assumed absent while the engine is unavailable. Routine shutdown removes this project's container/network, retains data and does not delete the image. There is deliberately no destructive reset target. Volume deletion, pruning, forced cleanup and reset commands are outside this milestone and require a separate explicit owner decision.

## Resources and persistence

Configured limits are 512 MiB memory, 1 CPU and 128 MiB shared memory, with `shared_buffers=128MB`, 20 connections, bounded container logs (10 MB × 3), a 60-second graceful stop period and no automatic restart. The health probe runs every 5 seconds with a 3-second timeout, 12 retries and a 10-second start period; startup wait is bounded at 90 seconds. These are development defaults, not measured performance guarantees. Docker VM overhead is additional and belongs in the host's 16 GB budget.

Image download is about 153.1 MB compressed when uncached; actual samples now include engine-reported image Size, aggregate data-directory usage and container stats in the verification report. Unpacked image/VM physical disk growth and peak workload use remain unmeasured. Reserve at least 2 GB free disk as a planning allowance for this small development environment, then record actual image/volume/VM usage after approval. The named volume has no disk quota and can grow; no capacity claim is made before measurement.

The volume mounts at `/var/lib/postgresql/data`, the required PostgreSQL 16 data path. After approved startup, record server version, health, loopback port mapping, native architecture, volume attachment and resource observations using narrow output. An approved isolated verification record may test persistence without creating the M1.3 application schema. A normal restart must be separately approved before using it as persistence evidence. Leave the isolated verification database in place under the approved plan; do not run a destructive database reset.

## Current verification

See [M1.2 verification evidence](../docs/M1_2_VERIFICATION.md). Quiet runtime validation, PostgreSQL 16.15 health/authenticated SQL, loopback binding, named-volume attachment and the isolated marker across one approved normal restart have been observed. The direct host protocol probe passed after explicit permission confirmation. All required runtime checks passed and the independent final review approved with comments: **M1.2 PASS**. See the report for point-in-time resource observations; configuration limits are not benchmarks.

## Runtime verification commands

The commands below are the controlled verification reference. Actual executions and exit codes are recorded in the report; do not rerun state changes without approval. Marker creation and the single restart were explicitly approved. They do not install a host SQL client or add backend dependencies.

Host protocol reachability, with bounded connect/read timeouts:

```bash
python3 - <<'HOST_PROBE'
import socket
import struct

with socket.create_connection(("127.0.0.1", 5432), timeout=3) as connection:
    connection.settimeout(3)
    connection.sendall(struct.pack("!II", 8, 80877103))
    if connection.recv(1) not in (b"S", b"N"):
        raise SystemExit("Unexpected PostgreSQL SSLRequest response")
print("PostgreSQL protocol responds on host 127.0.0.1:5432")
HOST_PROBE
```

The SSLRequest reply proves PostgreSQL protocol reachability from the host, not successful password authentication or TLS security. Separately authenticate over TCP inside the container and record its server version (the password is expanded only inside the container, never printed):

```bash
docker compose --env-file infra/.env -f infra/compose.yaml exec -T postgres \
  sh -ec 'PGPASSWORD="$POSTGRES_PASSWORD" PGCONNECT_TIMEOUT=3 \
  psql -X --no-password -h 127.0.0.1 -U postgres -d "$POSTGRES_DB" \
  -v ON_ERROR_STOP=1 -Atc "SHOW server_version"'
```

For the separately approved persistence test, create an isolated verification database and a non-secret comment marker. No application table, migration, view or role is created. `psql` processes stdin statements with autocommit; database creation fails if that name already exists, preserving unknown data. This object will be left in place; no destructive cleanup is part of M1.2.

```bash
docker compose --env-file infra/.env -f infra/compose.yaml exec -T postgres \
  sh -ec 'PGPASSWORD="$POSTGRES_PASSWORD" PGCONNECT_TIMEOUT=3 \
  psql -X --no-password -h 127.0.0.1 -U postgres -d "$POSTGRES_DB" \
  -v ON_ERROR_STOP=1 -v AUTOCOMMIT=on' <<'PERSISTENCE_PROBE'
CREATE DATABASE nexus_m12_verify;
COMMENT ON DATABASE nexus_m12_verify IS 'nexus-m1.2-persistence-probe';
SELECT shobj_description(oid, 'pg_database')
FROM pg_database WHERE datname = 'nexus_m12_verify';
PERSISTENCE_PROBE

# Only after explicit approval for this normal restart:
docker compose --env-file infra/.env -f infra/compose.yaml restart --timeout 60 postgres
make db-ready

# Repeat this query after readiness, compare with the exact marker recorded above:
docker compose --env-file infra/.env -f infra/compose.yaml exec -T postgres \
  sh -ec 'PGPASSWORD="$POSTGRES_PASSWORD" PGCONNECT_TIMEOUT=3 \
  psql -X --no-password -h 127.0.0.1 -U postgres -d "$POSTGRES_DB" \
  -v ON_ERROR_STOP=1' <<'PERSISTENCE_READ'
SELECT shobj_description(oid, 'pg_database')
FROM pg_database WHERE datname = 'nexus_m12_verify';
PERSISTENCE_READ
```

Record success only if the query returns exactly `nexus-m1.2-persistence-probe` both before and after the approved restart. `make db-ready` checks current readiness once; after restart, repeat it with a bounded wait of at most 90 seconds before concluding readiness failed.

Read-only runtime inspection reference (actual selected commands and outcomes are recorded in the verification report):

```bash
docker inspect nexus-ai-postgres-1 --format '{{.State.Health.Status}}'
docker inspect nexus-ai-postgres-1 --format '{{json .HostConfig.PortBindings}}'
docker inspect nexus-ai-postgres-1 --format '{{json .Mounts}}'
docker image inspect postgres:16.15-bookworm@sha256:5264710be20f409750ac6dc4e5706dcef929c87e241605463f0f9aefa932a8d9 --format 'Arch={{.Architecture}} SizeBytes={{.Size}}'
docker stats --no-stream --format '{{.Name}} memory={{.MemUsage}} cpu={{.CPUPerc}}' nexus-ai-postgres-1
docker system df
lsof -nP -iTCP:5432 -sTCP:LISTEN
```

Inspect only the selected fields shown, not `.Config.Env`. Check that the data mount is the named volume and that the sole published binding is `127.0.0.1:5432`. `docker system df` covers shared Docker resources; do not attribute its total to NEXUS AI. Host/VM memory and disk estimates remain separate from per-container observations.
