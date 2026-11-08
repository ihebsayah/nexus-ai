# NEXUS AI

NEXUS AI is a local-first, zero-paid-service logistics intelligence and automation platform. It demonstrates how a governed AI assistant can answer operational questions from verified business records without sending data to a paid cloud service.

**Current status:** M1.1 and M1.2 passed; M1.3 passed for its isolated database scope. M1.4 security source and tests are prepared; deployment and live permission tests require separate approval. The real nexus_ai database remains unmigrated, and M1.2 evidence is intact. Both ADRs remain Proposed. See [M1.3 evidence](docs/M1_3_VERIFICATION.md) and [M1.4 preparation evidence](docs/M1_4_VERIFICATION.md). No commit or push was made.

## Product overview

Logistics teams need fast answers about orders, customers, and shipments, but the data usually lives in operational systems that require reports, SQL, or manual follow-up. Generic language models can summarize a question, but they cannot be trusted to invent order statuses, delivery dates, or shipment events.

NEXUS AI takes a narrower approach:

- A user asks a natural-language question.
- A local language model selects from a small set of governed, read-only tools.
- The backend executes deterministic queries against PostgreSQL.
- The assistant answers only from the returned records and cites them.
- If the evidence is missing, ambiguous, or contradictory, the assistant says so instead of guessing.

The result is a realistic enterprise-style AI application that prioritizes privacy, auditability, testability, and resource discipline over model size or feature breadth.

## MVP at a glance

The MVP answers questions about three entities:

- `customers(id, name, email, created_at)`
- `orders(id, customer_id, status, created_at, expected_delivery_at)`
- `shipment_events(id, order_id, event_type, occurred_at)`

It exposes four read-only MCP tools:

- `list_pending_orders`
- `get_order_details`
- `get_overdue_orders`
- `get_customer_orders`

The assistant must not fabricate business facts. Every factual claim must be traceable to a tool result and a record identifier. See [docs/PRODUCT_VISION.md](docs/PRODUCT_VISION.md) and [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md).

## Architecture summary

NEXUS AI starts as a **modular monolith**, not a microservice fleet:

- **Next.js, React, TypeScript, Tailwind** provide the user interface.
- **FastAPI, Pydantic, SQLAlchemy, and Alembic** provide the API, validation, persistence, and migrations.
- **LangGraph** coordinates intent interpretation, tool selection, answer synthesis, and grounding checks.
- **MCP Python SDK** exposes the four governed tools over a local stdio server.
- **Ollama** is the planned local model runtime on Apple Metal. The initial candidate is `qwen3:4b`; no model evaluation is recorded, and the latest sandbox-blocked probe establishes neither server state nor model inventory.
- **PostgreSQL** stores synthetic operational data and the audit trail.
- **Docker Compose** is reserved for supporting services such as PostgreSQL. The application processes run on the host to preserve Apple Metal access and reduce memory overhead.

The runtime topology, component responsibilities, data flow, trust boundaries, schema, and resource estimates are in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). The two proposed decisions are [ADR-0001](docs/adr/0001-local-first-runtime-topology.md) and [ADR-0002](docs/adr/0002-local-dependencies-and-trust-boundaries.md).

## Local-first constraints

The target machine is an Apple M1 Mac with **16 GB unified memory**. That is a hard planning constraint, not a marketing claim.

The design therefore assumes:

- one local model and bounded inference concurrency;
- host-native application processes and Ollama;
- PostgreSQL as the only required supporting service;
- no Redis, Airflow, monitoring cluster, or orchestration cluster in the MVP;
- synthetic development data;
- read-only tools for the MVP;
- human approval before any future consequential write.

The memory figures in the architecture and ADRs are **planning estimates**. The additive range is roughly 11.7 GB baseline to 18.5 GB worst case, with a typical full-stack estimate near 15 GB. The worst case exceeds 16 GB, so a 16 GB fit is conditional, not guaranteed. These figures must be validated on the target machine before the project claims that the system fits.

## Roadmap

The roadmap is sequenced by dependency, not by calendar commitment. Foundation progress is recorded below; product runtime behavior and the remaining milestones are not implemented.

| Milestone | Focus | Status |
| --- | --- | --- |
| M0 | Product and architecture foundation | Documentation complete |
| M1 | Local environment and database foundation | M1.1–M1.2 PASS; M1.3 PASS (isolated database); M1.4 preparation only; M1.5 planned |
| M2 | Read-only tools and FastAPI API | Planned |
| M3 | Local LLM, LangGraph, and MCP integration | Planned |
| M4 | Next.js end-to-end MVP | Planned |
| M5 | Evaluation, hardening, and release readiness | Planned |
| M6+ | Future architecture and automation | Deferred |

Detailed deliverables, dependencies, exit criteria, and requirement traceability are in [docs/ROADMAP.md](docs/ROADMAP.md).

## Documentation map

| Document | Purpose |
| --- | --- |
| [docs/PRODUCT_VISION.md](docs/PRODUCT_VISION.md) | Problem, users, value proposition, scenario, and scope |
| [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md) | Functional and nonfunctional requirements with IDs and acceptance criteria |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Components, data flow, schema, trust boundaries, and resource budget |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Milestones, dependencies, deliverables, exit criteria, and traceability |
| [docs/adr/README.md](docs/adr/README.md) | Architecture decision record index and template |
| [docs/agent-system/README.md](docs/agent-system/README.md) | OpenCode development-agent system used to build NEXUS AI |
| [AGENTS.md](AGENTS.md) | Project rules, permission model, and current phase |

## Repository layout

```text
nexus-ai/
├── .opencode/                 OpenCode development agents and skills
├── docs/
│   ├── adr/                   Architecture decision records
│   ├── agent-system/          OpenCode agent-system documentation
│   ├── PRODUCT_VISION.md
│   ├── REQUIREMENTS.md
│   ├── ARCHITECTURE.md
│   └── ROADMAP.md
├── AGENTS.md
├── README.md
└── opencode.json
```

The workspace also contains `backend/src/nexus/`, `backend/tests/`, `frontend/app/`, `frontend/lib/`, `infra/`, `tests/`, and a root `Makefile`. Infrastructure and cross-layer tests remain placeholders. See the [M1.1 verification record](docs/M1_1_VERIFICATION.md).

## OpenCode development agents vs NEXUS AI runtime agents

This repository uses **OpenCode development agents** to plan, write, review, and verify the project. They are configured in `.opencode/agents/` and documented in [docs/agent-system/README.md](docs/agent-system/README.md).

NEXUS AI's **runtime agents** are product behavior built with LangGraph, MCP, Ollama, and PostgreSQL. They will eventually answer user questions inside the application. They are not the OpenCode development agents, and the two systems should not be conflated in code or documentation.

## Security and privacy

The MVP is designed around these boundaries:

- The browser never receives database credentials.
- The model never receives raw SQL authority.
- Only four named, read-only tools can access operational data.
- Tool arguments are validated against strict schemas.
- The tool database role cannot write.
- Tool calls and policy decisions are audited.
- Business data stays on the local machine.
- Future writes require a separate approval and audit design before implementation.

These are design intentions. They are not a claim that the system has been implemented, tested, or security-reviewed.

## Developer setup (M1.1)

The scaffold contains a process-only FastAPI `/health` route and a Next.js App Router page with TypeScript and Tailwind. It does not connect to PostgreSQL, MCP, LangGraph or Ollama. Both ADRs remain Proposed.

Toolchain baseline: Python 3.13.3 (`backend/.python-version` selects 3.13), Node 22.17.0 (`.node-version`), uv 0.8.2, Corepack 0.33.0 and pnpm 10.15.1. Backend checks use strict mypy and Ruff. Direct versions remain as declared; full resolutions are captured in `backend/uv.lock` and `frontend/pnpm-lock.yaml`. The backend is installed editable in `.venv`; frontend packages are in `node_modules`. Git is initialized with no staged files or commits.

Initial dependency installations and `git init` were executed with explicit owner approval. For future approved setup, use the following **locked repeat-install commands** from the stated directories. These exact repeat-install forms have not been executed as clean installations here; the initial installation and lockfile checks are recorded in the verification report.

```bash
# From backend/: use the existing local Python; do not download a toolchain.
UV_PYTHON_DOWNLOADS=never uv sync --locked --python python3.13

# From frontend/: use the pinned manager and preserve the lockfile.
corepack pnpm install --frozen-lockfile
```

Installations still require explicit approval. Do not regenerate or overwrite a lockfile without explaining the change. No model or infrastructure setup belongs to M1.1.

From the project root, the supported checks are:

| Command | Check |
| --- | --- |
| `make test` | Backend HTTP smoke tests and frontend Vitest tests |
| `make lint` | Ruff lint/format and ESLint |
| `make typecheck` | Strict mypy; Next route-type generation and TypeScript |
| `make build` | Next.js production build; telemetry disabled |
| `make verify` | All checks sequentially for the 16 GB host |

Individual targets are `backend-test`, `backend-lint`, `backend-typecheck`, `frontend-test`, `frontend-lint`, `frontend-typecheck`, and `frontend-build`. Checks invoke local environment executables directly and return `BLOCKED` if a tool is absent; they never invoke uv/Corepack or install automatically. `make` alone prints help. `make verify NEXT_BUILD_FLAGS=--webpack` passed in this environment; default Turbopack builds were blocked by worker-port permissions, including a broader-access retry. The explicit Webpack flag keeps the default Next build configuration available without changing package versions. Generated `next-env.d.ts` is ignored and recreated by the typecheck/build commands. These Next invocations set `CI=1` locally so missing TypeScript packages fail instead of triggering Next auto-installation; this does not use a hosted CI service. Actual executed results and remaining blockers are recorded in [M1_1_VERIFICATION.md](docs/M1_1_VERIFICATION.md); this command list does not imply a pass.

`.env.example` contains placeholders and future dependency settings only. Do not copy real credentials into source; M1.1 does not load the example automatically. The future BFF upstream is server-only. OpenCode development configuration remains unchanged; Ollama is a future NEXUS AI runtime dependency. M1.1 is complete; the M1.2 infrastructure scope and approval gate are described below.

## Local PostgreSQL setup (M1.2)

The prepared [Compose configuration](infra/compose.yaml) contains only PostgreSQL 16.15 Bookworm, pinned by digest for native ARM64. It publishes `127.0.0.1:5432`, stores data in named volume `nexus-ai-postgres-data`, and limits the container to 512 MiB RAM and one CPU. These settings are not measured resource results.

Prerequisites: Docker CLI/Compose v2, an available Docker engine, free host port 5432, and explicit approval for credentials setup, image pull and service startup. Docker Engine is now available. Initial conflict checks found no NEXUS resource or active-port conflict; unrelated existing resources were preserved. Reinspect resource identity and port use before future lifecycle changes.

The [infrastructure runbook](infra/README.md) contains exact controlled commands for Docker startup, an exclusive mode-0600 `infra/.env` containing a generated password, the pinned native image pull, startup and the separately approved isolated persistence/restart test. Do not use the example password or display resolved environment/configuration output. The bootstrap `postgres` administrator is for infrastructure only; application roles are deferred to M1.4.

From the project root:

| Command | Behavior and approval |
| --- | --- |
| `docker compose --env-file .env.example -f infra/compose.yaml config --quiet` | Executed static validation with placeholders; no runtime readiness claim. |
| `make db-config` | Quiet validation using ignored local `infra/.env`; exclusive credential setup completed with approval. |
| `make db-up` | Approval required; bounded startup wait, no automatic image pull/build. |
| `make db-down` | Approval required; removes the project container/network while retaining the named volume. |
| `make db-status` | Read-only project status. |
| `make db-logs` | Bounded project logs; never dump environment variables. |
| `make db-ready` | One bounded readiness probe; does not prove password authentication. |

Initial authorized setup and runtime verification have executed; actual results and the completed independent review are recorded in the report. `make db-down` has not been run; PostgreSQL remains running. Docker startup may activate unrelated pre-existing resources according to their own policies; conflict checks must precede project creation. Uncached image transfer is about 153.1 MB per official image metadata; a container sample observed 17.81 MiB / 512 MiB and aggregate data-directory usage about 68.9 MiB. Unpacked image size, physical Docker VM disk growth and peak workload use remain unmeasured. The original 2 GB free-disk allowance was a planning estimate. See [M1_2_VERIFICATION.md](docs/M1_2_VERIFICATION.md) for actual evidence and unresolved gates.

Normal shutdown does not delete volumes. There is no reset target; destructive reset, volume deletion and pruning are outside this milestone. Restart requires explicit approval. Stop after M1.2; do not create the M1.3 application schema.

## Domain schema and migrations (M1.3)

Mappings and revision `0001_initial_schema` follow [Architecture §10.2](docs/ARCHITECTURE.md#102-initial-schema). They create no business data, roles, views or runtime API integration. SQLAlchemy 2.0.57, Alembic 1.20.1 and psycopg[binary] 3.3.8 are installed at the approved pins; the backend lock now includes them and required transitives without changing any old dependency version.

The [migration runbook](backend/MIGRATIONS.md) explains installation, target guards and commands. Offline inspection targets are `make migration-heads`, `make migration-history` and `make migration-sql`; they never connect to a database or load credentials. All three inspection targets executed successfully after approved installation.

Online `migration-current` and `migration-check` use read-only transactions on the owned test database. `migration-upgrade-test` and `migration-downgrade-test` mutate only exact database `nexus_m13_test` on `127.0.0.1:5432`, with required ownership comment `nexus-ai:m1.3-disposable`. They consume the existing ignored credential file only on explicit invocation and never rewrite it. A target guard is a tooling safeguard, not a substitute for database privileges; the temporary bootstrap administrator is not a future application runtime account.

The owner explicitly approved initial installation/lock regeneration, disposable database creation/comment, test DML, upgrade and one destructive test-only downgrade/re-upgrade; these completed successfully. Future state-changing runs still require approval. No database is auto-created. Real `nexus_ai` and M1.2 evidence are excluded from this migration environment. Both remain unchanged; applying the real schema would require a separately reviewed and approved plan. See [M1_3_VERIFICATION.md](docs/M1_3_VERIFICATION.md) for actual results and remaining gates. M1.4 preparation is described below; execution requires separate approval.

## Known limitations

- Backend/frontend scaffolding exists; MVP logistics behavior has not been verified.
- The Ollama CLI reports 0.33.0. The latest server probe was blocked by sandbox permissions, so server state and model inventory remain unverified; no model evaluation is recorded.
- No memory, latency, or throughput measurement has been taken.
- The status and event-type enums are initial assumptions, not finalized business contracts.
- Authentication, multi-user authorization, PII masking, and LAN exposure are unresolved.
- The grounding validator can enforce citation validity, identifier format, and structured claim/value consistency; it cannot prove full semantic entailment.
- The MVP does not include writes, vector retrieval, durable workflows, dbt models, or ML experiments.

Resolved decisions and open questions are tracked in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#assumptions-and-unresolved-decisions) and the ADRs.


## Database security preparation (M1.4)

M1.4 is **PARTIAL overall: preparation only**. Read the [security plan](backend/security/README.md),
[prepared test instructions](backend/security/TESTING.md) and [verification evidence](docs/M1_4_VERIFICATION.md).
`make security-plan` and `make security-sql` inspect source offline. They do not apply
migrations, roles, views, grants or credentials. Normal verification skips live security tests.

The proposed owner remains NOLOGIN. Runtime roles start disabled; tool SELECT is
limited to three unfiltered views, and app INSERT is limited to audit writer columns
without id/RETURNING or direct sequence access. Customer email remains visible in the
lookup view. The proposal protects nexus_ai objects; runtime LOGIN requires an explicit
cross-database PUBLIC access decision. Actual grants and authenticated positive/negative
tests remain unexecuted, pending separate approval. Both ADRs remain Proposed. Stop
before M1.5.
