---
name: documentation
description: Use when writing or updating NEXUS AI documentation, including READMEs, ADRs, API docs, runbooks, agent-system docs, and architecture diagrams. Triggers on documentation, README, ADR, runbook, API docs, diagram, or onboarding guide.
license: MIT
compatibility: opencode
metadata:
  audience: all-contributors
  version: "1.0"
---

# Documentation

## When to use

Use when a change needs a README update, ADR, API reference, runbook, onboarding guide, or architecture diagram. Do not use it to generate marketing copy or unverified claims.

## Instructions

1. Identify the audience and the decision or task the document must support.
2. Put the most important information first. Prefer short sections and scannable lists.
3. Document verified commands exactly as they were run.
4. Separate current behavior from proposed behavior.
5. Use relative links for repository files and stable headings for deep links.
6. For ADRs, use: Title, Status, Context, Decision, Consequences, Alternatives, Follow-ups.
7. For runbooks, include prerequisites, commands, expected output, failure handling, and rollback.
8. For API docs, describe authentication, request/response shapes, errors, pagination, and idempotency.
9. Use Mermaid for diagrams when a visual clarifies boundaries or flow.
10. Remove or mark stale documentation rather than leaving contradictions.

## Checklist

- [ ] Audience and purpose are clear.
- [ ] Commands are copied from actual executions.
- [ ] Current and proposed behavior are separated.
- [ ] Links and paths resolve.
- [ ] Code samples are minimal and accurate.
- [ ] Security-sensitive values are not included.
- [ ] ADRs and runbooks use the required structure.
- [ ] Stale or contradictory docs are updated or marked.
- [ ] OpenCode development agents and NEXUS AI runtime agents are clearly distinguished.

## Expected output

Updated or new documentation with accurate commands, structure, and links. State which commands were executed to verify the documented behavior.

## Verification

- Every documented command was run or explicitly marked as unverified.
- Every link and file path resolves.
- No benchmark, output, or capability is invented.
- The document does not contradict `AGENTS.md` or the current code.
