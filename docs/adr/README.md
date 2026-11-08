# Architecture Decision Records

This directory holds NEXUS AI architecture decisions. The `architect` subagent is the primary author.

## Naming

Use `NNNN-short-title.md`, for example `0001-modular-monolith.md`.

## Template

```markdown
# NNNN — Title

- **Status**: Proposed | Accepted | Superseded | Deprecated
- **Date**: YYYY-MM-DD
- **Deciders**: names or roles

## Context

What problem are we solving? What constraints and forces apply?

## Decision

What are we doing?

## Consequences

What becomes easier or harder? What risks are introduced?

## Alternatives considered

What else was viable, and why was it rejected?

## Follow-ups

What small, verifiable work remains?
```

## Index

| ADR | Status | Summary |
| --- | --- | --- |
| [0001](0001-local-first-runtime-topology.md) | Proposed | Host-native applications with containerized PostgreSQL and a modular monolith |
| [0002](0002-local-dependencies-and-trust-boundaries.md) | Proposed | Local stdio MCP server as the sole governed data-access path, with strict trust and audit boundaries |
