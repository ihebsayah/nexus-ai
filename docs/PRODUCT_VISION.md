# NEXUS AI Product Vision

- **Status:** Complete for Step 0.3
- **Date:** 2026-11-07
- **Scope:** Product direction, MVP intent, and future boundaries

## 1. Purpose

NEXUS AI exists to show how a small, local-first AI system can answer real operational questions without sacrificing privacy, correctness, or auditability.

The product is an enterprise-style logistics intelligence and automation platform. It is also a portfolio-grade demonstration of AI engineering, product engineering, data engineering, and reliable automation. Those two goals must reinforce each other: the architecture should be credible for a real operations team, and every claim about the system should be verifiable on a 16 GB Apple M1 Mac with no paid services.

## 2. Problem

Logistics operations data is usually spread across order management, customer records, and shipment event streams. Answering a simple question such as "Which orders for Acme are overdue, and what happened most recently?" often requires:

- knowing which system owns the answer;
- writing or requesting a report;
- reconciling status and event timestamps;
- checking whether an order is still active or already terminal;
- explaining the result to a colleague or customer.

Generic language models make the interface feel easier, but they introduce a worse problem: they can produce plausible business facts that were never retrieved from a system of record. In an operations context, a fabricated delivery date or shipment event is not a harmless hallucination. It can lead to a wrong customer promise, an unnecessary escalation, or a missed exception.

## 3. Users

### Primary: logistics operations analyst

Monitors open orders, overdue deliveries, and shipment exceptions. Needs fast, trustworthy answers and a clear trail back to the underlying records.

### Primary: customer support specialist

Answers "where is my order?" and "why is it late?" questions. Needs customer-scoped answers without exposing unrelated customers and without inventing shipment details.

### Secondary: operations manager

Prioritizes overdue orders and reviews recurring exceptions. Needs aggregate views, but the MVP is deliberately limited to record-level questions.

### Secondary: engineering and data stakeholder

Evaluates whether the system's architecture is realistic, testable, private, and maintainable. Needs explicit boundaries, trade-offs, and honest evidence.

## 4. Value proposition

NEXUS AI gives operations users a natural-language interface to verified operational data while keeping the system:

- **Grounded:** answers are derived from tool results, not model memory.
- **Governed:** the model can choose only from a small set of read-only tools with validated arguments.
- **Private:** business data and inference stay on the local machine.
- **Auditable:** requests, tool decisions, and record access are traceable.
- **Resource-aware:** the design is constrained by 16 GB unified memory and avoids unnecessary services.
- **Testable:** deterministic tool semantics and a synthetic evaluation set make correctness measurable before claims are made.

The MVP is not trying to be a general-purpose enterprise assistant. It is trying to prove that a narrow, governed assistant can be more useful than either a raw dashboard or an unconstrained chatbot.

## 5. Product principles

1. **Evidence before fluency.** A clear "I could not find that" is better than a polished answer with invented facts.
2. **The model proposes; the system verifies.** The model may interpret intent and choose tools, but deterministic code validates arguments, executes queries, and checks citations.
3. **Read-only until proven otherwise.** The MVP cannot change business data. Future writes require a separate approval and audit design.
4. **Local first, not local only by accident.** The architecture should make the local boundary explicit, not rely on a cloud service that happens to be optional.
5. **Small surfaces.** Four tools and three entities are enough to demonstrate the pattern. Breadth can come later.
6. **Honest evaluation.** No benchmark, memory figure, or accuracy claim is valid until it has been measured and recorded.
7. **Boring reliability.** Bounded concurrency, timeouts, explicit error states, and append-only audit are more valuable than extra agents or services.

## 6. Realistic end-to-end scenario

A customer support specialist receives a message from Acme Retail asking why two deliveries are late.

The specialist opens NEXUS AI and asks:

> "Which orders for Acme Retail are overdue, and what was the latest shipment event on each?"

The system processes the request as follows:

1. The Next.js UI sends the question to the FastAPI backend with a new request identifier.
2. LangGraph interprets the question and selects `get_overdue_orders` with a customer selector for "Acme Retail".
3. The MCP tool policy layer validates the tool name and arguments. The tool resolves the customer by exact, case-insensitive name. If more than one customer matches, it returns an ambiguity result instead of guessing.
4. The tool executes a parameterized, read-only query. It returns non-terminal orders whose `expected_delivery_at` is earlier than the database's current time, ordered by expected delivery date. Each result includes the UUID order identifier, status, expected delivery time, and the latest shipment event.
5. LangGraph asks the local model to synthesize an answer using only the returned records. The model includes citations to the UUID order identifiers and event records.
6. The grounding validator checks that every cited order and event exists in the tool result, that mentioned identifiers are present in the evidence, and that server-computed values such as days overdue match the backend calculation.
7. The API returns the answer, citations, tool-call metadata, model identifier, and latency to the UI.
8. The audit trail records the request, the selected tool, a hash of the arguments, the decision, the row count, and the latency.

If Acme Retail has no overdue orders, the response states that no matching orders were found, returns `insufficient_data`, and includes an empty citation list. The system does not invent an order.

If the customer name is ambiguous, the assistant asks a clarifying question and shows the candidate customer identifiers. It does not query orders for an arbitrary match.

If the database is unavailable, the user receives a retryable service error. The system does not return a partial or guessed answer.

This scenario is the MVP's definition of a successful end-to-end interaction. The grounding validator checks citation validity, identifier format, and structured claim/value consistency; it does not prove full semantic entailment of arbitrary prose. The detailed request sequence, failure handling, and trust boundaries are in [ARCHITECTURE.md](ARCHITECTURE.md).

## 7. MVP scope

### In scope

- Natural-language questions about the three initial entities.
- A single local model accessed through Ollama.
- Four governed, read-only MCP tools.
- Deterministic PostgreSQL queries over synthetic data.
- Grounded answers with record-level citations.
- Clarification for ambiguous or unsupported questions.
- Explicit error handling for model, database, policy, and grounding failures.
- Request and tool-call audit records.
- A minimal Next.js interface.
- A synthetic evaluation harness that records actual results.
- Local-first operation with no paid runtime dependency.

### Out of scope for the MVP

- Creating, updating, or deleting customers, orders, or shipment events.
- Autonomous actions, background workflows, or scheduled automation.
- Multi-tenant authentication and authorization.
- Real customer data or production data migration.
- Vector search, document RAG, or pgvector retrieval.
- Temporal workflows, dbt models, ML training, or MLflow experiments.
- Production deployment, high availability, or horizontal scaling.
- A general-purpose chat assistant, web browsing, or external API calls.
- Business intelligence dashboards or aggregate analytics beyond the four tools.

## 8. Future direction

The future architecture may add:

- **Consequential writes with human approval:** a proposal, policy check, approval record, short-lived authorization token, idempotent execution, and audit trail.
- **pgvector and local embeddings:** retrieval over operational documents such as carrier notes and exception reports, with the same citation discipline.
- **Temporal:** durable workflows for long-running follow-ups and escalations.
- **dbt Core:** local transformation models and data-quality tests over synthetic or replicated data.
- **scikit-learn and MLflow:** local experimentation for exception prediction or prioritization, with no paid tracking service.
- **Multi-user identity and roles:** local authentication and actor-aware audit.

These are directions, not commitments. Each significant addition should have an ADR and a milestone with verifiable exit criteria.

## 9. Success signals

The MVP will be judged on evidence, not on marketing claims. The evaluation harness should record:

- whether the selected tool matches the expected tool for a synthetic question;
- whether the answer cites only records returned by the tool;
- whether identifiers and server-computed numbers in the answer match the evidence;
- how often the system returns a safe clarification or insufficient-data response instead of a fabricated answer;
- end-to-end latency and resource use on the target Mac;
- whether every request and tool decision is auditable.

No numeric targets or accuracy results are claimed in this document. Targets and baselines will be defined and measured in the evaluation milestone. Until then, any number would be an invention.

## 10. Assumptions and open questions

### Assumptions

- The MVP serves a single local user on one Mac.
- Synthetic data is sufficient to demonstrate the product pattern.
- Exact customer matching by identifier, email, or name is adequate; fuzzy matching is not required.
- The four tools cover the initial question set.
- The model can produce structured tool selections reliably enough to be validated, but this is unproven.
- PostgreSQL in Docker Compose is an acceptable local dependency.
- A host-native application and Ollama are preferable to running everything in containers, subject to measured memory fit.
- A 16 GB fit is conditional: the planning typical estimate is near 15 GB and the worst case exceeds 16 GB, so measured reserve and fallbacks are required.

### Open questions

- What is the final order-status enum and event-type enum?
- Should the MVP bind only to localhost, or also to the local network?
- What PII fields may appear in answers and logs?
- How long should audit records be retained?
- What is the acceptable end-to-end latency target for a single-user local workload?
- Which model should be selected after evaluating `qwen3:4b` and any approved alternatives?
- How should the UI present citations and clarification candidates?
- When should the project introduce authentication and actor-aware authorization?

These questions are carried into [REQUIREMENTS.md](REQUIREMENTS.md) and [ARCHITECTURE.md](ARCHITECTURE.md) rather than being silently resolved.

## 11. Related documents

- [README](../README.md)
- [Requirements](REQUIREMENTS.md)
- [Architecture](ARCHITECTURE.md)
- [Roadmap](ROADMAP.md)
- [ADR-0001: Local-first runtime topology](adr/0001-local-first-runtime-topology.md)
- [ADR-0002: Local dependencies and trust boundaries](adr/0002-local-dependencies-and-trust-boundaries.md)
