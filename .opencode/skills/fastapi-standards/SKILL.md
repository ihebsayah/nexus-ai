---
name: fastapi-standards
description: Use when implementing or reviewing FastAPI endpoints, Pydantic models, PostgreSQL access, pgvector queries, migrations, or OpenAPI contracts in NEXUS AI. Triggers on FastAPI, Pydantic, SQLAlchemy, Alembic, API endpoint, request validation, or database migration.
license: MIT
compatibility: opencode
metadata:
  audience: backend
  version: "1.0"
---

# FastAPI Standards

## When to use

Use for backend API work: new endpoints, request/response models, database access, migrations, error handling, and OpenAPI changes. Do not use for frontend data fetching.

## Instructions

1. Inspect the existing app structure, dependency versions, and conventions before adding libraries or patterns.
2. Keep routers thin: validation in Pydantic models, business logic in services, persistence in repositories or data-access modules.
3. Use typed request and response models. Never return raw ORM objects or unvalidated dictionaries.
4. Use dependency injection for sessions, settings, and authentication.
5. Use explicit HTTP status codes and a consistent error envelope with stable error codes.
6. Use async I/O consistently. Do not mix blocking database calls into async handlers.
7. Use parameterized queries or ORM bindings. Never interpolate user input into SQL.
8. For pgvector, define the embedding dimension and distance operator explicitly; index only after measuring the query pattern.
9. Use expand-and-contract migrations for schema changes that must be zero-downtime.
10. Add tests for success, validation failure, authorization failure, and not-found paths.

## Checklist

- [ ] Existing dependencies and conventions checked.
- [ ] Request and response models are typed.
- [ ] Error responses are consistent and do not leak internals.
- [ ] Authentication and authorization are enforced at the boundary.
- [ ] SQL is parameterized; no string-built queries.
- [ ] Database session lifecycle is correct.
- [ ] Migration has a rollback or recovery path.
- [ ] OpenAPI schema is accurate.
- [ ] Tests cover success and failure paths.
- [ ] Test, lint, and typecheck commands were executed.

## Expected output

Endpoint or service change, typed models, migration notes when applicable, and tests. Report the exact commands run and their observed results.

## Verification

- `pytest` (or the project's configured test command) was executed and its output reported.
- Lint and typecheck commands were executed if configured.
- OpenAPI output or schema was inspected when the contract changed.
- No secret values appear in code, fixtures, logs, or examples.
