---
name: system-design
description: Use when designing or reviewing NEXUS AI architecture, service boundaries, data flow, ADRs, or significant technical trade-offs. Triggers on architecture, boundaries, ADR, design review, scalability, reliability, observability, or local-first resource constraints.
license: MIT
compatibility: opencode
metadata:
  audience: architects
  version: "1.0"
---

# System Design

## When to use

Use for architecture analysis, new component boundaries, cross-service contracts, ADRs, reliability design, or any decision that is expensive to reverse. Do not use for routine implementation details.

## Instructions

1. State the problem, the forces at play, and the constraints.
2. Identify affected components and their boundaries: Next.js UI, FastAPI services, PostgreSQL/pgvector, Ollama, LangGraph, MCP, Temporal, dbt, Docker Compose.
3. Map data flow, trust boundaries, failure modes, and operational ownership.
4. Consider the local-first constraint: Apple Silicon, 16 GB unified memory, no paid services. Prefer the simplest design that fits.
5. Present at least two viable options with trade-offs.
6. Recommend one option and state the consequences.
7. Record significant decisions as an ADR.

## Checklist

- [ ] Problem and scope are explicit.
- [ ] Assumptions and unknowns are listed.
- [ ] Component responsibilities and boundaries are clear.
- [ ] Data ownership and flow are documented.
- [ ] Failure modes, retries, timeouts, and fallbacks are considered.
- [ ] Security and trust boundaries are identified.
- [ ] Observability and operability are addressed.
- [ ] Resource budget is plausible for 16 GB unified memory.
- [ ] Alternatives and trade-offs are recorded.
- [ ] Follow-up tasks are small and verifiable.

## Expected output

An ADR or design note with: Title, Status, Context, Decision, Consequences, Alternatives considered, and Follow-ups. Include a simple diagram when boundaries or data flow are non-obvious.

## Verification

- Every architectural claim is either sourced, reasoned, or marked as an assumption.
- The decision names its trade-offs and rejected alternatives.
- Boundaries do not require a paid service or an unverified capability.
- Follow-ups can be verified independently.
