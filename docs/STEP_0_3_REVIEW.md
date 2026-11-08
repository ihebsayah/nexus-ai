# Step 0.3 — Architecture consistency review

Date: 2026-11-07
Scope: documentation only. No implementation milestone is completed by this review.

## Delegation and findings

The orchestrator delegated focused read-only analysis to an architect specialist, following the repository architect role and system-design/documentation skills. The specialist found remaining inconsistencies in claim units, selector examples, audit primary keys, views-only grants, memory scenarios, existing scaffold statements, M1.1 verification and destructive-reset approval. All were corrected in the target documents. A separate reviewer performs the final read-only pass; its outcome is recorded below after review.

## Corrections

- Reconciled additive memory load (9.7–15.5 GB), required capacity with reserve (11.7–18.5 GB), and midpoint capacity (15.1 GB) across architecture and ADR-0001. Reserve is headroom, and high-end planning is not a guaranteed upper bound. Required measurements and fallbacks remain explicit.
- Retained UUID customer/order/event identifiers and typed citation prefixes; repaired the selector example and boolean claim unit. Audit-event keys remain bigint identities.
- Preserved M1 and requirement traceability while tightening M1.1–M1.5 verification: executed lint/test evidence, exact domain/audit key types, views-only access, and explicit destructive-reset approval on a disposable volume.
- Documented citation-validation limits, record/relationship binding, adversarial structured-claim evaluation, and separate human-reviewed prose support.
- Replaced unsupported current environment and empty-repository assertions with observed facts and explicit verification limits.
- Both ADRs remain Proposed; owner acceptance is outstanding.

## Environment evidence

Previous document text reported CLI 0.33.0, a stopped/unavailable server and no confirmed model. Its raw command transcript is not present in the reviewed architecture documents; preserve it as a prior reported observation, not fresh proof.

Commands actually executed during this review:

```text
command -v ollama
/opt/homebrew/bin/ollama

ollama --version
Warning: could not connect to a running Ollama instance
Warning: client version is 0.33.0
(exit 0)

ollama list
Error: Head "http://127.0.0.1:11434/": dial tcp 127.0.0.1:11434: connect: operation not permitted
(exit 1)
```

The CLI is installed and reports 0.33.0. The sandbox-blocked connection establishes neither server state nor model inventory. No server was started, no model downloaded, and no inference or benchmark run.

Read-only inventory and inspection found existing backend/frontend scaffolding (`backend/src/nexus/api/app.py`, `frontend/app/page.tsx`), a Makefile and placeholder infrastructure/test directories. These predate this work. Their tests, dependencies and milestone exit criteria were not verified; no application files were changed.

`git status --short` failed with `fatal: not a git repository (or any of the parent directories): .git` (exit 128). No Git diff or tracked-file assertion is possible in this workspace. Before-edit SHA-256 snapshots provide a narrower check of changes made during this review, excluding secret files and node_modules.

## Documentation verification

A Python standard-library check validates local Markdown link targets and anchors, parses JSON examples and UUID literals, compares all 30 MVP requirement IDs with the roadmap matrix, checks five M1 steps and Proposed ADR statuses, and compares pre-edit file hashes. The initial run identified links to this not-yet-created report. After creation, `python3 /tmp/nexus_step03_check.py` passed: 53 local links/anchors, 5 JSON blocks, 11 UUID occurrences, all 30 MVP requirement IDs in the traceability matrix, five M1 steps, two Proposed ADRs, and memory arithmetic. The non-documentation snapshot hashes remained unchanged, including OpenCode configuration, agents and skills. The helper is a temporary verification script, not an application test suite. These checks validate documents, not application behavior.

## Final reviewer outcome

The independent read-only reviewer reproduced the link, JSON, UUID, requirement-coverage and memory checks. It found ambiguous truncation wording (exactly-limit results need not be truncated), an error-envelope qualification, premature M1.1 migration/service command documentation, and an example answer containing a count absent from its structured claim. All four were corrected; the reviewer rechecked them and found no unresolved material documentation inconsistency. Verdict: **approve with comments for Step 0.3 documentation only**. Runtime tests were not run because this is a documentation review and infrastructure/model startup is outside scope.

## Unresolved decisions and readiness

Owner acceptance of ADR-0001/0002, final enums, model selection, measured memory fit, workload/performance thresholds, grounding thresholds, PII and audit retention, authentication/LAN exposure and production operations remain open as listed in the architecture.

The final reviewer gate is complete. M1.1 is ready for scoped owner authorization; it is not complete. Reconcile and verify the existing scaffold rather than assuming an empty repository. Installation, infrastructure lifecycle, destructive reset, commits and pushes retain their separate approval requirements. Big Pickle development-model configuration is untouched; the project configuration has no explicit model override, so effective external model selection was not verified. No protected configuration or skill file was edited. Stop after Step 0.3.
