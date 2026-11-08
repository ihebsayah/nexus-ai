# ADR-0002 — Local dependencies and trust boundaries

- **Status**: Proposed
- **Date**: 2026-11-05
- **Deciders**: Project owner (approval required); architect (proposal author); backend, ai-engineer, qa, security, and reviewer inputs

## Context

NEXUS AI allows a local language model to help answer questions about operational data. The model is useful for interpreting intent and writing an answer, but it is not a trusted authority. A fluent answer can contain invented orders, dates, or shipment events. The system therefore needs a narrow data path, strict tool policy, and an audit trail.

The MVP is single-user and read-only. It has no authentication, no write tools, and no external runtime dependency. Those choices must be explicit, not accidental.

The relevant forces are:

- local-first data and inference;
- four read-only tools over PostgreSQL;
- a model that may propose tools but must not execute arbitrary SQL;
- least-privilege database access;
- evidence-based answers and citations;
- append-only audit;
- a future path to consequential writes with human approval;
- no paid services.

## Decision

Use a local stdio MCP server as the sole governed data-access path for LLM-driven reads.

### Runtime boundary

```text
Browser
  → Next.js UI and same-origin BFF proxy
  → FastAPI
  → LangGraph
  → local stdio MCP server
  → read-only PostgreSQL role over exposed views
```

The model never receives database credentials and never emits SQL for execution. The MCP server owns the tool registry, validates arguments, and executes parameterized queries. The MCP server is a local subprocess managed by the FastAPI process and communicates over stdio.

### Local dependencies

- PostgreSQL 16 runs in Docker Compose, bound to `127.0.0.1:5432`.
- Ollama is planned to run natively on the host at `127.0.0.1:11434`. The previously documented observation reported CLI 0.33.0 and an unavailable server, with no confirmed model. On 2026-11-07 CLI 0.33.0 was confirmed but sandbox permissions blocked the server probe; current server state and model inventory remain unverified. See the [review evidence](../STEP_0_3_REVIEW.md#environment-evidence).
- Next.js and FastAPI run natively on the host.
- No paid API, hosted database, hosted vector store, or paid observability is used.
- pgvector, Temporal, dbt, scikit-learn, and MLflow are deferred.

### Tool policy

- Deny by default; only four tools are allowlisted:
  - `list_pending_orders`
  - `get_order_details`
  - `get_overdue_orders`
  - `get_customer_orders`
- Tool names come from a server-side registry, never from arbitrary model text.
- Arguments are validated against strict JSON schemas.
- Customer selectors require exactly one of identifier, email, or name.
- Queries are parameterized and limited by row, column, and statement-duration caps.
- The tool role has `SELECT` only on `v_customers`, `v_orders`, and `v_shipment_events`.
- The tool role has no access to base tables, migrations, or audit events.
- Tool results contain only the fields required for the answer and citations.

### Trust boundaries

1. **Browser:** untrusted; no database credentials; no direct database or FastAPI access.
2. **Next.js BFF:** local trusted proxy; no business logic; forwards the request.
3. **FastAPI:** validates input, enforces deadlines, orchestrates the graph, and writes audit events.
4. **Model:** untrusted output; may propose a tool and produce text, but cannot bypass policy.
5. **MCP server:** policy enforcement point and the only component executing business queries.
6. **PostgreSQL:** system of record with separate roles for migration ownership, read-only tool access, and append-only audit insertion.

### Authorization and audit

- The proposed MVP default is single-user and localhost-only; it does not claim authentication or multi-user authorization. Any local-network exposure remains an open decision pending owner approval.
- `nexus_tool` is read-only over exposed views.
- `nexus_app` may insert audit events but may not update or delete them.
- Audit events record the request identifier, tool name, normalized argument hash, decision, row count, latency, model identifier, and error code.
- Raw arguments and raw customer PII are not stored in audit by default.
- If the audit write fails, the request fails closed.
- Structured logs use the same request identifier and do not include secrets.

### PII and data minimization

- The customer summary defaults to `customer_id` and `name`; email is accepted for lookup but is not returned by default.
- Synthetic data is used for development and evaluation.
- Logs and audit use hashes or redacted values for lookup arguments.
- A PII minimization, masking, and retention policy remains an unresolved decision before any real data is considered.

### Future writes

The MVP has no write tools. Any future consequential write must use:

```text
propose → policy check → human approval record → short-lived approval token
→ idempotent execution → append-only audit
```

The proposer and approver must be separate responsibilities. No write tool may exist without an approval record, a short-lived authorization, and an audit path. A future write design requires a new ADR.

## Consequences

### Positive

- One narrow, testable policy point for all LLM-driven reads.
- The model cannot execute arbitrary SQL or access database credentials.
- The read-only role is enforced by PostgreSQL grants, not only by application convention.
- Every request and tool decision has a durable audit path.
- The same MCP interface can later move to a standalone process without changing the tool contract.
- Local-first dependencies keep business data and inference on the machine.

### Negative

- The MCP server shares the API process lifecycle and failure domain.
- stdio is less observable and less independently scalable than a network service.
- The MVP has no authentication; localhost binding and a single-user assumption are compensating constraints, not a complete security model.
- Host-level access can still read local files and database volumes; the design does not protect against a compromised local account.
- Audit retention and deletion policy remain unresolved.
- Grounding validation reduces but does not eliminate semantic error.

### Risks

- A policy bug could expose a broader query surface than intended.
- A compromised local process could bypass the intended boundary.
- Audit volume or retention could become a local operational issue.
- The future write path is materially more dangerous and must not reuse read-only assumptions.
- The stdio server's lifecycle coupling may make long-running or concurrent requests harder to isolate.

## Alternatives considered

### Direct SQL tool inside LangGraph

Rejected. It would be simpler in the short term but gives the model or graph a dangerous authority and makes deterministic testing, least privilege, and audit much harder.

### Separate MCP server over HTTP in a container

Viable later. It offers process isolation and independent deployment, but adds a port, container overhead, network failure modes, and another trust boundary. The MVP does not need that complexity.

### MCP server as a separate host-native process over HTTP

Viable later. It keeps native execution and isolates the process, but adds lifecycle and transport management. The stdio subprocess is simpler for a single-user MVP and preserves the same tool interface.

### LangChain SQL agent or unrestricted ORM access

Rejected. It weakens the policy boundary, encourages model-authored queries, and makes grounding and audit less predictable.

### Cloud-hosted MCP or hosted database

Rejected by local-first, privacy, and zero-paid-service constraints.

## Follow-ups

- Implement the three PostgreSQL roles and view grants, and test them with actual `INSERT`/`UPDATE`/`DELETE` denial checks.
- Add tool-policy tests for non-allowlisted tools, unknown arguments, and SQL-injection-shaped strings.
- Add audit fail-closed tests.
- Complete a focused threat model before M5, including local-account compromise and local-network exposure.
- Decide the authentication and local-network exposure model before any shared or remote use.
- Define audit retention and PII policy before using non-synthetic data.
- Revisit process isolation if concurrency, observability, or failure containment becomes a measured problem.
- Require a new ADR before implementing any consequential write path.
