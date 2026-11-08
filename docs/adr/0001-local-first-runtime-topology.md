# ADR-0001 — Local-first runtime topology

- **Status**: Proposed
- **Date**: 2026-11-05
- **Deciders**: Project owner (approval required); architect (proposal author); backend, frontend, devops, and ai-engineer reviewers

## Context

NEXUS AI must run on a single Apple M1 Mac with 16 GB of unified memory and no paid services. The MVP needs a Next.js interface, a FastAPI backend, a local language model, a PostgreSQL database, and a governed tool path. It also needs to remain testable and reproducible enough to demonstrate engineering quality.

The main forces are:

- Apple Metal access for Ollama inference;
- memory overhead from Docker's Linux VM;
- reproducibility of PostgreSQL and migrations;
- a small operational surface for a single user;
- clear module boundaries without premature distribution;
- a later path to pgvector, Temporal, dbt, and MLflow without rewriting the core.

Pre-existing backend/frontend scaffolding is present; MVP behavior and resource fit have not been verified. Memory figures in this record are planning estimates.

The previously documented observation reported Ollama CLI 0.33.0 and an unavailable server, with no confirmed model. On 2026-11-07 the CLI reported 0.33.0, but sandbox permissions blocked the server probe: current server state and model inventory remain unverified. No services were started for this review. See the [review evidence](../STEP_0_3_REVIEW.md#environment-evidence).

## Decision

Use host-native application processes with containerized PostgreSQL:

| Component | Runtime | Port |
| --- | --- | --- |
| Next.js UI and BFF proxy | Host-native | `3000` |
| FastAPI application | Host-native, single uvicorn worker | `8000` |
| MCP tool server | Local stdio subprocess managed by FastAPI | stdio |
| PostgreSQL 16 | Docker Compose, bound to `127.0.0.1` | `5432` |
| Ollama | Native host, Apple Metal | `11434` |

The backend is a modular monolith with one-way dependencies:

- `api/` — HTTP boundary;
- `application/` — use cases and orchestration;
- `domain/` — pure business rules;
- `ports/` — protocols and shared schemas for persistence, tools, model, and audit;
- `persistence/` — SQLAlchemy models, repositories, migrations;
- `tools/` — governed registry, MCP server, read-only queries;
- `llm/` — Ollama client, prompts, LangGraph nodes, structured output;
- `audit/` — append-only audit events.

Allowed imports: `domain` imports no other NEXUS module; `ports` imports only `domain` types and shared contracts; `application` imports `domain` and `ports`; the adapters (`persistence`, `tools`, `llm`, `audit`) import `domain` and `ports`, not `api` or each other's internals; `api` wires adapters at the composition root. The `llm` module never imports `persistence` and never emits SQL.

Docker Compose is limited to supporting services. PostgreSQL is the only required service in the MVP. Future services such as Temporal or dbt may be added through opt-in profiles, not in the default profile. pgvector is deferred and is not part of the initial PostgreSQL schema.

The MVP runs one API worker. This keeps the in-process request queue and inference semaphore meaningful; multiple workers would require a different shared-concurrency design.

## Consequences

### Positive

- Ollama keeps native Apple Metal access.
- No Docker VM overhead for the application or model.
- The local setup is simpler to inspect and debug.
- PostgreSQL remains reproducible and isolated through Compose.
- The modular monolith keeps deployment and tests simple while preserving extraction seams.
- A single user and single machine are a realistic operating model for the MVP.

### Negative

- Host toolchains must be installed and pinned carefully.
- The host environment is less isolated than running every component in containers.
- One API process is a single failure domain and is not horizontally scalable.
- Module boundaries must be enforced through imports, tests, and review; they are not enforced by process isolation.
- Docker still adds VM overhead for PostgreSQL.
- The local machine's available memory remains a hard constraint.

### Risks

- The additive planning range is 11.7–18.5 GB. The worst case exceeds 16 GB, so a 16 GB fit is conditional on measurement and may require a fallback.
- Ollama model behavior and memory use are unverified until M3; current server state and model inventory are unverified because the latest probe was sandbox-blocked.
- Host-specific setup can drift from documentation if versions are not pinned.
- A later multi-user or shared deployment would require a topology change.

## Alternatives considered

### All services in Docker Compose

Rejected for the MVP. It offers stronger environment parity and isolation, but Docker's VM overhead and containerized Metal access work against the 16 GB and inference goals. It also adds operational complexity before the core flow is proven.

### PostgreSQL installed natively on macOS

Viable as a fallback. It avoids Docker overhead and may be faster, but it is harder to reproduce and cleanly reset. PostgreSQL in Compose is the better default for demonstration and repeatability.

### Microservices from the start

Rejected. The MVP has one user, four tools, and one model. Service boundaries would add network failure modes, deployment overhead, and distributed tracing needs without a proven scaling requirement.

### Fully managed or cloud-hosted runtime

Rejected by the project's zero-paid-service and local-first constraints. It would also undermine the privacy and data-egress story.

## Memory planning scenarios

The same additive scenarios as [Architecture section 14](../ARCHITECTURE.md#14-resource-budget-for-16-gb) apply:

| Scenario | Estimated load | Required reserve | Required capacity |
| --- | ---: | ---: | ---: |
| Baseline (low-end full stack) | 9.7 GB | 2 GB | 11.7 GB |
| Typical (line-item midpoints) | 12.6 GB | 2.5 GB | 15.1 GB |
| Worst-case planning scenario (high ends) | 15.5 GB | 3 GB | 18.5 GB |

Reserve is headroom, not consumed memory. These are estimates, not benchmarks or exhaustive upper bounds. Baseline does not mean idle host memory. Measure idle host usage, total host pressure/swap/compression, Docker and PostgreSQL usage without double counting, application RSS, and loaded model/context usage during representative requests in M3 and the complete UI stack in M5. Record context, quantization, concurrency, workload and sampling method. A sampled peak establishes only the tested workload, not a guaranteed worst case. Apply a recorded fallback if less than 2 GB headroom remains or sustained memory pressure occurs.

## Follow-ups

- Measure baseline, typical, and worst-case memory on the target Mac in M3 and M5, using observed process and model memory, and record whether at least 2 GB reserve remains. Apply and record a fallback if it does not.
- Select the local model only after a recorded evaluation; `qwen3:4b` is a candidate, not a decision.
- Set and document conservative Compose resource expectations for PostgreSQL after measuring.
- Add import-boundary checks or tests when the backend package exists.
- Decide whether the MVP binds only to `127.0.0.1` or also to the local network; default to localhost until reviewed.
- Revisit this ADR if measured memory pressure requires a smaller model, native PostgreSQL, or a different process topology.
- Add an ADR before introducing pgvector, Temporal, dbt, or MLflow into the default runtime.
