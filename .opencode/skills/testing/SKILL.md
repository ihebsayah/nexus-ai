---
name: testing
description: Use when planning, writing, or running tests for NEXUS AI, including pytest, frontend tests, integration tests, contract tests, and end-to-end tests. Triggers on test, pytest, unit test, integration test, e2e, fixture, coverage, regression, or verification.
license: MIT
compatibility: opencode
metadata:
  audience: qa-and-engineers
  version: "1.0"
---

# Testing

## When to use

Use when a change needs verification, a bug needs a regression test, or a test suite needs design or repair. Use the project's existing test runner and conventions; do not introduce a new framework without approval.

## Instructions

1. Inspect the existing test layout, fixtures, and commands before writing tests.
2. Choose the lowest test layer that can catch the failure: unit, integration, contract, or end-to-end.
3. Write the smallest test that fails for the intended reason, then make it pass.
4. Keep tests deterministic. Control time, randomness, network, and external services.
5. Use realistic data for integration tests, but never real credentials or production data.
6. Assert behavior and observable outcomes, not implementation details.
7. Cover success, validation failure, authorization failure, not-found, and dependency failure where relevant.
8. Avoid snapshot-only tests for logic-heavy behavior.
9. Report failures with the exact command, output, and reproduction steps.
10. Report coverage only when a coverage tool actually ran.

## Checklist

- [ ] Existing test conventions checked.
- [ ] Test layer is appropriate.
- [ ] Test fails for the intended reason before the fix.
- [ ] Time, randomness, and external dependencies are controlled.
- [ ] Success and failure paths are covered.
- [ ] No real secrets or production data are used.
- [ ] Test command was executed.
- [ ] Observed results are reported accurately.
- [ ] Coverage is reported only if measured.

## Expected output

Tests added or updated, the exact commands executed, pass/fail counts, relevant output, and any residual risk.

## Verification

- The test command was actually run.
- The reported result matches the observed output.
- A failing test is not described as passing.
- A skipped or flaky test is called out explicitly.
