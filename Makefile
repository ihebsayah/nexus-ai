# Verification uses installed local executables only; it never installs dependencies.
.DEFAULT_GOAL := help
.NOTPARALLEL:

# Set NEXT_BUILD_FLAGS=--webpack when the host restricts Turbopack worker ports.
NEXT_BUILD_FLAGS ?=

DB_COMPOSE = docker compose --env-file infra/.env -f infra/compose.yaml

.PHONY: help test lint typecheck build verify backend-test backend-lint backend-typecheck frontend-test frontend-lint frontend-typecheck frontend-build

help:
	@echo "Verification: make test lint typecheck build (or make verify)"
	@echo "Missing local tools are BLOCKED. See README.md for approval-required setup."

test: backend-test frontend-test

lint: backend-lint frontend-lint

typecheck: backend-typecheck frontend-typecheck

build: frontend-build

verify: lint typecheck test build

backend-test:
	@test -x backend/.venv/bin/python || { echo "BLOCKED: backend environment missing; approve setup first."; exit 2; }
	cd backend && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest

backend-lint:
	@test -x backend/.venv/bin/ruff || { echo "BLOCKED: local Ruff missing; approve backend setup first."; exit 2; }
	cd backend && .venv/bin/ruff check .
	cd backend && .venv/bin/ruff format --check .

backend-typecheck:
	@test -x backend/.venv/bin/mypy || { echo "BLOCKED: local mypy missing; approve backend setup first."; exit 2; }
	cd backend && .venv/bin/mypy

frontend-test:
	@test -x frontend/node_modules/.bin/vitest || { echo "BLOCKED: local Vitest missing; approve frontend setup first."; exit 2; }
	cd frontend && node_modules/.bin/vitest run

frontend-lint:
	@test -x frontend/node_modules/.bin/eslint || { echo "BLOCKED: local ESLint missing; approve frontend setup first."; exit 2; }
	cd frontend && node_modules/.bin/eslint .

frontend-typecheck:
	@test -x frontend/node_modules/.bin/next || { echo "BLOCKED: local Next.js missing; approve frontend setup first."; exit 2; }
	@test -x frontend/node_modules/.bin/tsc || { echo "BLOCKED: local TypeScript missing; approve frontend setup first."; exit 2; }
	cd frontend && CI=1 NEXT_TELEMETRY_DISABLED=1 node_modules/.bin/next typegen
	cd frontend && node_modules/.bin/tsc --noEmit

frontend-build:
	@test -x frontend/node_modules/.bin/next || { echo "BLOCKED: local Next.js missing; approve frontend setup first."; exit 2; }
	cd frontend && CI=1 NEXT_TELEMETRY_DISABLED=1 node_modules/.bin/next build $(NEXT_BUILD_FLAGS)

# Database lifecycle targets require explicit owner approval before invocation.
# db-up never pulls an image; the separately approved pull is documented in infra/README.md.
.PHONY: db-up db-down db-status db-logs db-ready db-config

db-config:
	$(DB_COMPOSE) config --quiet

db-up:
	$(DB_COMPOSE) up -d --no-build --pull never --wait --wait-timeout 90 postgres

db-down:
	$(DB_COMPOSE) down --timeout 60

db-status:
	$(DB_COMPOSE) ps --all

db-logs:
	$(DB_COMPOSE) logs --tail 50 postgres

db-ready:
	$(DB_COMPOSE) exec -T postgres sh -ec 'pg_isready -h 127.0.0.1 -p 5432 -U postgres -d "$$POSTGRES_DB" -t 3'

# M1.3 inspection never installs packages. Online targets are test-database-only.
MIGRATION_CLI = backend/.venv/bin/python -m nexus.persistence.migrate
MIGRATION_ENV_FILE ?= infra/.env
.PHONY: migration-tools migration-heads migration-history migration-sql migration-current migration-check migration-upgrade-test migration-downgrade-test

migration-tools:
	@test -x backend/.venv/bin/python || { echo "BLOCKED: backend environment missing."; exit 2; }
	@backend/.venv/bin/python -c 'import importlib.util; raise SystemExit(not all(importlib.util.find_spec(name) for name in ("sqlalchemy", "alembic", "psycopg")))' || { echo "BLOCKED: approve migration dependency installation first."; exit 2; }

migration-heads: migration-tools
	$(MIGRATION_CLI) heads

migration-history: migration-tools
	$(MIGRATION_CLI) history

migration-sql: migration-tools
	$(MIGRATION_CLI) sql

migration-current: migration-tools
	$(MIGRATION_CLI) current --database nexus_m13_test --env-file "$(MIGRATION_ENV_FILE)"

migration-check: migration-tools
	$(MIGRATION_CLI) check --database nexus_m13_test --env-file "$(MIGRATION_ENV_FILE)"

# Execution requires separate explicit owner approval. No database is auto-created.
migration-upgrade-test: migration-tools
	$(MIGRATION_CLI) upgrade --database nexus_m13_test --env-file "$(MIGRATION_ENV_FILE)"

# Destructive to the disposable schema ONLY; never nexus_ai or nexus_m12_verify.
migration-downgrade-test: migration-tools
	$(MIGRATION_CLI) downgrade --database nexus_m13_test --env-file "$(MIGRATION_ENV_FILE)"

# M1.4 offline source inspection. No deployment/credentials/lifecycle target is implicit.
SECURITY_CLI = backend/.venv/bin/python -m nexus.persistence.security_admin
.PHONY: security-plan security-sql
security-plan: migration-tools
	$(SECURITY_CLI) plan

security-sql: migration-tools
	$(SECURITY_CLI) render
