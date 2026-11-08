---
name: security-review
description: Use when reviewing or designing security for NEXUS AI, including authentication, authorization, input validation, secrets, injection, local network exposure, containers, dependencies, and PII. Triggers on security review, auth, secrets, vulnerability, injection, SSRF, CVE, container security, or threat model.
license: MIT
compatibility: opencode
metadata:
  audience: reviewers-and-engineers
  version: "1.0"
---

# Security Review

## When to use

Use for security-sensitive changes, architecture reviews, authentication and authorization work, container or network exposure, secret handling, and dependency risk. Do not use it as a substitute for an actual scanner when one is required.

## Instructions

1. Identify assets, actors, trust boundaries, and entry points.
2. Check authentication and authorization at every boundary. Do not rely on UI hiding.
3. Validate input at the server boundary. Use allowlists where possible.
4. Check for injection: SQL, command, template, prompt, and path traversal.
5. Check secret handling: no secrets in source, logs, errors, fixtures, or client bundles.
6. Check local network exposure: bind services to localhost by default; do not publish ports unnecessarily.
7. Check container configuration: non-root where practical, pinned images, minimal privileges, no secrets in image layers.
8. Check dependencies for known issues using an actual tool when available. Do not invent CVE identifiers.
9. Check logging and telemetry for PII or credential leakage.
10. Report findings by severity with `file_path:line_number` and a concrete fix.

## Checklist

- [ ] Assets and trust boundaries are identified.
- [ ] Authentication and authorization are enforced server-side.
- [ ] Input validation is present at boundaries.
- [ ] Injection paths are checked.
- [ ] Secrets are absent from source, logs, and client bundles.
- [ ] Services bind locally by default.
- [ ] Container privileges and image pinning are reviewed.
- [ ] Dependency risk was checked with a real tool when available.
- [ ] Logs and telemetry do not leak sensitive data.
- [ ] Findings include evidence and a fix.

## Expected output

A findings list sorted by severity: `path:line` — severity — problem — evidence — fix. Include verification gaps and residual risk.

## Verification

- Each finding is supported by code, configuration, or tool output.
- No CVE, scanner result, or exploit is fabricated.
- Fixed findings are re-checked.
- Unverified areas are explicitly marked.
