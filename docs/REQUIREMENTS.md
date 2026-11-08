# NEXUS AI Requirements

- **Status:** Complete for Step 0.3
- **Date:** 2026-11-07
- **Scope:** MVP requirements and explicitly deferred future requirements

## 1. Purpose

This document defines what the NEXUS AI MVP must do, how it will be judged, and which requirements are deliberately deferred. It separates the MVP implementation from future architecture so that planning does not quietly expand the first release.

Requirement IDs are stable references. Roadmap milestones and acceptance evidence should cite them. No requirement is considered met until its acceptance criteria have been demonstrated with actual output.

## 2. Definitions

- **Grounded answer:** An answer whose business facts are derived only from tool results returned for the current request. Each factual claim carries citations to the tool and record identifiers that support it.
- **Evidence:** The structured result of an executed read-only tool, including record identifiers, values, and query metadata.
- **Tool policy:** The server-side allowlist, argument schema, row and column limits, timeout, and read-only database role that govern tool execution.
- **Terminal order status:** `delivered` or `cancelled`. Terminal orders are not considered pending or overdue.
- **Overdue order:** A non-terminal order whose `expected_delivery_at` is earlier than the database's current time. The complete rule is in [ARCHITECTURE.md](ARCHITECTURE.md#11-business-rules).
- **Insufficient data:** A safe response indicating that the system could not find or verify enough evidence to answer. It is not an error and must not contain invented business facts.
- **Clarification:** A safe response asking the user to disambiguate the request, for example when a customer name matches more than one record.
- **Audit event:** An append-only record of a request or tool decision, including the request identifier, tool, argument hash, decision, row count, latency, and model identifier.

## 3. MVP functional requirements

| ID | Requirement | Acceptance criteria | Milestone |
| --- | --- | --- | --- |
| FR-001 | Accept a natural-language question about customers, orders, or shipments. | A non-empty question returns a response containing `request_id`, `status`, `answer`, `claims`, `citations`, `tool_calls`, `model`, and `latency_ms`. Empty, malformed, or over-limit input returns HTTP 422 with a stable error code and no model call. | M3, M4 |
| FR-002 | Use a local model to select only from the four governed tools. | The model can select `list_pending_orders`, `get_order_details`, `get_overdue_orders`, or `get_customer_orders`. Any other tool name is rejected before execution, audited, and never executed. At most one repair attempt is allowed before a safe fallback. | M3 |
| FR-003 | Implement `list_pending_orders`. | Returns only orders with `status = 'pending'`. Supports an optional customer selector and a limit of 1–50 (default 20). Results are ordered by `created_at ASC, id ASC`. The response includes order identifiers and an always-present truncation flag, true only when an additional matching row exists beyond the requested limit. | M2 |
| FR-004 | Implement `get_order_details`. | Requires an `order_id`. Returns the order, its customer summary, and shipment events ordered by `occurred_at DESC, id DESC`, with a bounded event limit. An unknown order returns a controlled `NOT_FOUND` result and no invented fields. | M2 |
| FR-005 | Implement `get_overdue_orders`. | Returns non-terminal orders with `expected_delivery_at < now()`. Supports an optional customer selector and a limit of 1–50 (default 20). Each row includes the order, its customer summary, the latest shipment event, `is_overdue = true`, and server-computed `overdue_seconds` and `days_overdue`. Results are ordered by `expected_delivery_at ASC, id ASC`. | M2 |
| FR-006 | Implement `get_customer_orders`. | Requires exactly one customer selector. Supports an optional order status and a limit of 1–50 (default 20). Results are ordered by `created_at DESC, id DESC`. An ambiguous customer returns candidate identifiers and no orders. | M2 |
| FR-007 | Resolve customers deterministically. | Exactly one of `customer_id`, `customer_email`, or `customer_name` may be supplied. Email and name matching are exact and case-insensitive. Zero matches return `NOT_FOUND`; more than one match returns `AMBIGUOUS_CUSTOMER` with candidate identifiers and names. Fuzzy matching is not used in the MVP. | M2 |
| FR-008 | Produce grounded answers with citations. | Every factual business claim in `claims` carries at least one `tool + record_id` citation and must use an allowed structured claim type and field. All claims and top-level citations must be a subset of the evidence returned for the request. Order, customer, and event identifiers mentioned in the answer must be UUIDs present in the evidence. Server-computed numbers must match the backend calculation. If validation fails, no unverified answer is returned. | M3, M5 |
| FR-009 | Handle ambiguity and insufficient evidence safely. | Ambiguous or unsupported requests return `clarification_required` with a focused question and optional candidate identifiers. Requests with no tool call, no rows, or insufficient evidence return `insufficient_data`. Neither response may contain invented business facts. Ambiguous intent must not trigger an arbitrary database query. | M3, M4 |
| FR-010 | Enforce deterministic tool contracts. | Each tool has a JSON schema, validated arguments, row and column limits, a statement timeout, and a read-only database role. Raw SQL from the model is never executed. Unknown arguments and invalid types are rejected before query execution. | M1.4–M1.5, M2 |
| FR-011 | Handle errors explicitly. | The API implements the response and error contract in section 5. Database timeouts, model timeouts, model unavailability, saturation, grounding failure, and audit failure each return a defined status and error code. No error path returns a partial answer. | M2, M3 |
| FR-012 | Maintain an append-only audit trail. | Each request and tool decision records `request_id`, actor or local-session identifier, tool name, normalized argument hash, decision, row count, latency, model identifier, and timestamp. The application role cannot update or delete audit events. If the audit write fails, the request fails closed. | M1.4–M1.5, M2 |
| FR-013 | Make requests traceable. | The response includes `request_id`, `tool_calls`, `model`, and `latency_ms`. Structured logs use the same request identifier. Tool-call metadata never exposes credentials or raw PII beyond the documented response fields. | M2, M4 |
| FR-014 | Provide schema migrations and synthetic data. | Alembic migrations create the initial schema, constraints, and indexes. A deterministic, idempotent seed script loads synthetic customers, orders, and shipment events. The seed contains no real personal data. | M1.3, M1.5 |
| FR-015 | Provide health and readiness endpoints. | `/health` returns 200 when the API process is alive. `/ready` returns 200 only when the database is reachable and the schema is usable. Model readiness is reported separately and does not make the API fail liveness. | M2 |
| FR-016 | Provide a truthful evaluation harness. | A synthetic question set covers the four tools, ambiguity, empty results, error paths, and seeded adversarial invalid claims. The harness records actual selected tools, citations, schema validity, claim-field support, unsupported claims, hallucinated identifiers and numbers, grounding-check outcomes, safe fallback, false refusal, latency, and resource notes. No metric is reported before it is produced by an executed run. | M3, M5 |

## 4. MVP nonfunctional requirements

| ID | Requirement | Acceptance criteria | Milestone |
| --- | --- | --- | --- |
| NFR-001 | Local-first operation with no paid runtime services. | The MVP requires no paid API, cloud service, hosted database, or paid observability. Business data and inference remain local. Any optional model download is explicit and approved. | M0–M5 |
| NFR-002 | Treat 16 GB unified memory as a hard planning constraint. | The architecture records baseline, typical, and worst-case additive estimates (roughly 11.7, 15.1, and 18.5 GB), acknowledges that the worst case exceeds 16 GB, and defines the required measurements. The design uses one loaded model, inference concurrency 1, API concurrency 2–4 with queueing, and a bounded tool-call count. No claim of measured fit is made before validation. | M0, M3, M5 |
| NFR-003 | Meet provisional performance targets after validation. | Targets are provisional and must be measured in M5: p95 end-to-end latency under 30 seconds for a defined single-user light workload, and database tool latency under 2 seconds for the synthetic dataset. The 30–45 second total request deadline is a timeout, not the p95 target. These are targets, not measured results. | M3, M5 |
| NFR-004 | Protect privacy and prevent unintended data egress. | PostgreSQL and Ollama are planned local dependencies. The MVP does not send business records to an external API. Logs redact or omit secrets and minimize PII. No credentials or real `.env` values are committed. | M1.1–M1.5, M2, M3 |
| NFR-005 | Apply least-privilege security controls. | Tools use a read-only database role over exposed views only; no base-table access. Queries are parameterized. Tool access is deny-by-default. If CORS is configured, it is limited to the local UI origin. The browser receives no database credentials. | M1.2, M1.4–M1.5, M2, M5 |
| NFR-006 | Make consequential activity auditable. | Audit events are append-only and correlated by request identifier. The application role cannot mutate or delete audit history. A written retention and deletion policy is produced by M5 and is consistent with append-only grants. | M1.4–M1.5, M2, M5 |
| NFR-007 | Prefer deterministic system behavior over model discretion. | Tool policies, query semantics, sorting, limits, and business calculations are deterministic. The model may interpret intent and synthesize text, but it does not perform authoritative calculations or write SQL. Low-temperature settings and structured output are used where supported. | M1.3, M2, M3 |
| NFR-008 | Be testable at every layer. | The roadmap includes domain unit tests, PostgreSQL integration tests, MCP tool contract tests, API tests, end-to-end tests, and an evaluation harness. Tests are executed before results are claimed. | M1.1, M1.5, M2–M5 |
| NFR-009 | Provide minimal local observability. | Structured logs include request identifiers, tool decisions, row counts, latency, and model identifier. The audit table provides a durable record. The MVP does not add a paid observability service or an unnecessary monitoring stack. | M2, M5 |
| NFR-010 | Preserve modular-monolith maintainability. | The backend uses explicit modules with one-way dependencies. No microservice split is introduced in the MVP. Cross-module access goes through defined interfaces, and extraction is allowed only at existing module seams. | M0, M1.1 |
| NFR-011 | Make the local environment reproducible. | Versions are pinned when implementation begins. PostgreSQL runs through Docker Compose with a named volume, migrations, and seed data. Commands are documented only after they have been executed. | M1.1–M1.5 |
| NFR-012 | Make the answer and its evidence understandable. | The UI displays the answer, citations, tool-call metadata, loading state, error state, and empty state. Citation and clarification controls are keyboard accessible and visually clear. | M4 |
| NFR-013 | Isolate failures and fail closed. | Model, database, and tool calls have bounded timeouts and retries. Saturation returns 429 with retry guidance. Grounding or audit failure prevents an unverified answer from being returned. | M2, M3 |
| NFR-014 | Report only truthful evaluation results. | The evaluation harness records executed commands and actual outcomes. No benchmark, accuracy, latency, or memory figure is published without the corresponding run. Model selection is based on recorded evaluation, not assumption. | M0, M3, M5 |

## 5. Response and error contract

### 5.1 Success and safe-fallback envelope

```json
{
  "request_id": "00000000-0000-4000-8000-000000000000",
  "status": "answered",
  "answer": "Order 00000000-0000-4000-8000-000000000002 is overdue for Acme Retail.",
  "claims": [
    {
      "claim_type": "overdue_calculation",
      "subject": { "type": "order", "id": "00000000-0000-4000-8000-000000000002" },
      "field": "is_overdue",
      "operator": "eq",
      "value": true,
      "unit": "boolean",
      "text": "Order 00000000-0000-4000-8000-000000000002 is overdue for Acme Retail.",
      "citations": [
        { "tool": "get_overdue_orders", "record_id": "customer:00000000-0000-4000-8000-000000000001" },
        { "tool": "get_overdue_orders", "record_id": "order:00000000-0000-4000-8000-000000000002" }
      ]
    }
  ],
  "citations": [
    { "tool": "get_overdue_orders", "record_id": "customer:00000000-0000-4000-8000-000000000001" },
    { "tool": "get_overdue_orders", "record_id": "order:00000000-0000-4000-8000-000000000002" }
  ],
  "tool_calls": [
    { "tool": "get_overdue_orders", "decision": "allowed", "row_count": 1 }
  ],
  "model": "qwen3:4b",
  "latency_ms": 0
}
```

`status` is one of:

- `answered` — the answer is grounded in evidence.
- `clarification_required` — the system needs a disambiguation or missing parameter.
- `insufficient_data` — the system has no verifiable evidence for a factual answer.
- `error` — a system or validation failure occurred.

`claims` is required for `answered`; every claim must carry at least one citation. Each claim contains the structured fields used by the grounding validator plus a `text` rendering. The top-level `citations` array is the union of claim citations. Within this success/safe-fallback envelope, `citations` and `claims` may be empty only for `clarification_required` and `insufficient_data`; the separate error envelope in section 5.2 omits these fields. `request_id` is a UUID assigned by the API. All customer, order, and shipment-event identifiers are UUIDs; citation `record_id` values use `<entity>:<uuid>` (`customer:`, `order:`, or `event:`), while tool arguments use bare UUIDs. For example, an event citation uses `event:00000000-0000-4000-8000-000000000003`. The example uses placeholder UUIDs and `latency_ms: 0`; production responses contain generated identifiers and an actual measured latency.

### 5.2 Error envelope

```json
{
  "request_id": "00000000-0000-0000-0000-000000000000",
  "status": "error",
  "error": {
    "code": "DB_TIMEOUT",
    "message": "The database did not respond in time.",
    "retryable": true
  }
}
```

| Code | HTTP | Retryable | Meaning |
| --- | ---: | --- | --- |
| `INVALID_INPUT` | 422 | No | Empty, malformed, or over-limit question |
| `UNSUPPORTED_QUESTION` | 200 | No | Returned as `clarification_required`, not an error envelope |
| `INVALID_TOOL_ARGS` | 200 | No | Model produced invalid tool arguments after one repair; return `insufficient_data` and audit |
| `TOOL_POLICY_DENIED` | 200 | No | Model requested a non-allowlisted tool; return `insufficient_data` and audit |
| `NOT_FOUND` | 200 | No | Tool found no matching record; return `insufficient_data` with no invented facts |
| `AMBIGUOUS_CUSTOMER` | 200 | No | Return `clarification_required` with candidate identifiers |
| `DB_TIMEOUT` | 503 | Yes | Database statement or connection timed out |
| `DB_ERROR` | 503 | Yes | Database is unavailable or returned an unexpected error |
| `MODEL_TIMEOUT` | 503 | Yes | Local model did not respond within the deadline |
| `MODEL_UNAVAILABLE` | 503 | Yes | Ollama or the selected model is unavailable |
| `RATE_LIMITED` | 429 | Yes | Request queue or inference concurrency is saturated |
| `GROUNDING_FAILED` | 502 | No | Draft answer failed citation or consistency validation; no partial answer returned |
| `AUDIT_WRITE_FAILED` | 503 | Yes | Audit event could not be written; request fails closed |

Internal policy denials and invalid tool arguments are audited even when the user receives a safe `insufficient_data` response. The table intentionally separates user-facing status from internal decision codes. Tool result status values are lowercase; the API maps `not_found` to `NOT_FOUND`, `ambiguous_customer` to `AMBIGUOUS_CUSTOMER`, and `error` to the appropriate retryable database or model code. Tool statuses are not returned verbatim.

## 6. Grounding and evidence rules

1. Tool results are the only source of business facts for an answer.
2. The model may not use parametric knowledge to fill missing order statuses, delivery dates, customer details, or shipment events.
3. The backend computes authoritative counts, overdue durations, and row totals. The model may describe them but may not recalculate them.
4. Every citation must reference a `tool + record_id` pair present in the evidence for the current request.
5. Any order, customer, or event identifier in the answer must appear in the evidence.
6. An empty result, missing tool call, or policy denial produces `insufficient_data`, not a guess. A failed grounding validation after synthesis always returns non-retryable `502 GROUNDING_FAILED`.
7. The grounding validator enforces claim-to-citation coverage, allowed structured claim types and fields, citation compatibility per tool, identifier presence, and numeric consistency. It does not prove full semantic entailment of every sentence; that limitation must be stated in evaluation reports.
8. The evaluation harness measures groundedness on a synthetic question set and records actual outcomes. Compare structured values and entity relationships against seeded expectations; test valid citations attached to wrong facts, swapped entities, causal or negative prose, and false completeness under truncation. Separately record human-reviewed prose support and unsupported claims. Passing citation checks or a finite evaluation set does not guarantee semantic truth of arbitrary generated text.

## 7. Future requirements (not in the MVP)

These requirements are explicitly deferred. They must not be implemented during the MVP without a new approved milestone and, where material, an ADR.

| ID | Requirement | High-level acceptance criteria |
| --- | --- | --- |
| FR-F-001 | Consequential writes with human approval. | Proposal, policy check, approval record, short-lived authorization token, idempotent execution, and audit. No write occurs without an approval record. |
| FR-F-002 | Local vector retrieval with pgvector. | Approved local embedding model, local vector storage, citation-bearing retrieval, and no paid vector database. |
| FR-F-003 | Durable workflows with Temporal. | Long-running follow-up or escalation workflows, retries, visibility, and a local development profile. |
| FR-F-004 | Local transformations with dbt Core. | Versioned models, data-quality tests, and reproducible local runs without a paid warehouse. |
| FR-F-005 | Local ML experiments with scikit-learn and MLflow. | Reproducible experiments, local tracking, and no paid experiment service. |
| FR-F-006 | Multi-user identity and roles. | Local authentication, actor-aware authorization, and audit events that identify the actor. |

## 8. Traceability

The milestone mapping for every MVP requirement is recorded in [ROADMAP.md](ROADMAP.md#11-requirements-traceability). Every FR and NFR in this document must appear in that matrix before the roadmap is considered complete.

## 9. Assumptions and unresolved decisions

### Assumptions

- Single local user for the MVP; no multi-tenant isolation.
- Synthetic data is sufficient for development and evaluation.
- Exact customer matching is sufficient; fuzzy matching is deferred.
- The order statuses are `pending`, `confirmed`, `in_transit`, `delivered`, and `cancelled`.
- The initial shipment event types are `created`, `picked_up`, `in_transit`, `out_for_delivery`, `delivered`, and `exception`.
- `expected_delivery_at` is required for MVP orders; a future nullable source would require an explicit handling rule.
- The model can produce valid structured tool selections often enough to be validated; this is unproven.
- All customer, order, and shipment-event identifiers are UUIDs; citations use typed `record_id` values and tool arguments use bare UUIDs. Human-readable order numbers are not part of the MVP.
- PostgreSQL in Docker Compose and Ollama natively on macOS are acceptable local dependencies, subject to measured memory fit.
- A 16 GB fit is conditional: the planning typical estimate is near 15 GB and the worst case exceeds 16 GB, so measured reserve and fallbacks are required.

### Unresolved decisions

- Final status and event-type enums.
- Authentication, actor identity, and local-network exposure.
- PII minimization and masking policy.
- Audit retention and deletion policy.
- Exact performance targets and reference workload.
- Model selection after evaluating `qwen3:4b` and any approved alternatives.
- Grounding validator depth and evaluation thresholds.
- UI presentation of citations and clarification candidates.
- Production deployment and backup strategy.

## 10. Out of scope for the MVP

- Writes or autonomous actions.
- Real customer data.
- Multi-user authentication and authorization.
- Vector search, document RAG, or pgvector.
- Temporal, dbt, scikit-learn, or MLflow.
- Paid APIs, cloud services, hosted databases, or paid observability.
- High availability, horizontal scaling, or production deployment.
- General web browsing or external data retrieval.

## 11. Related documents

- [README](../README.md)
- [Product vision](PRODUCT_VISION.md)
- [Architecture](ARCHITECTURE.md)
- [Roadmap](ROADMAP.md)
- [ADR-0001: Local-first runtime topology](adr/0001-local-first-runtime-topology.md)
- [ADR-0002: Local dependencies and trust boundaries](adr/0002-local-dependencies-and-trust-boundaries.md)
