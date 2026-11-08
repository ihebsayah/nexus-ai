# NEXUS AI — Project Instructions

## What this project is

NEXUS AI is a local-first, zero-paid-service enterprise AI and automation platform. It is built and run on an Apple Silicon Mac with 16 GB unified memory.

Planned stack: Next.js, TypeScript, FastAPI, PostgreSQL, pgvector, Ollama, LangGraph, MCP, Temporal, dbt, and Docker Compose.

## OpenCode development agents vs NEXUS AI runtime agents

This repository uses OpenCode **development agents** to build NEXUS AI. They are configured in `.opencode/agents/` and are described in `docs/agent-system/README.md`.

NEXUS AI's **runtime agents** are product behavior built with LangGraph, MCP, Ollama, and pgvector. They are not the same thing as the OpenCode agents. When documenting or discussing either system, say which one you mean.

## Global rules

1. **No paid services.** Do not add paid APIs, cloud services, subscriptions, hosted vector databases, paid CI, or paid observability. Prefer local, open-source, self-hosted components.
2. **Local-first and resource-aware.** Optimize for Apple Silicon and 16 GB unified memory. Prefer smaller local models, bounded concurrency, explicit memory limits, and simple architectures.
3. **Maintainable over clever.** Prefer testable, readable solutions over unnecessary abstraction or complexity.
4. **Small, verifiable tasks.** Break work into independently verifiable units. Each unit should have a clear check.
5. **No false verification.** Never claim tests, builds, lints, benchmarks, or commands passed unless they were executed and the output was observed. Never invent command output, documentation, or benchmark results.
6. **Approval required.** Do not commit, push, install dependencies, start/stop infrastructure, run destructive commands, or change credentials without explicit user approval. Editing `AGENTS.md`, `opencode.json`, or files under `.opencode/` also requires explicit approval.
7. **Secrets stay out of source control.** Do not write credentials, tokens, private keys, or real `.env` values into tracked files, logs, fixtures, examples, or documentation.
8. **Explain trade-offs.** Significant architectural decisions must state alternatives, consequences, and risks.
9. **Report blockers.** If a task cannot be completed or verified, say so explicitly and state what remains.
10. **Respect the boundary.** Application code belongs to NEXUS AI. OpenCode configuration belongs in `.opencode/`, `opencode.json`, and `AGENTS.md`.

## Agent system

Default primary agent: `orchestrator`.

| Agent | Mode | Purpose |
| --- | --- | --- |
| `orchestrator` | primary | Planning, delegation, integration, final verification |
| `architect` | subagent | Architecture boundaries, trade-offs, ADRs |
| `backend` | subagent | FastAPI, PostgreSQL, pgvector, API design |
| `frontend` | subagent | Next.js, React, TypeScript, UX |
| `ai-engineer` | subagent | LangGraph, MCP, RAG, Ollama, evaluations |
| `data-engineer` | subagent | dbt, pipelines, scikit-learn, MLflow |
| `devops` | subagent | Docker, local environments, CI, observability |
| `qa` | subagent | Automated tests, integration tests, security validation |
| `reviewer` | subagent | Independent read-only code and architecture review |

Delegation is explicit: the orchestrator invokes a specialist through the Task tool. `subagent_depth` is `1`, so specialists cannot delegate further. Do not assume automatic parallel delegation.

## Skills

Reusable skills live in `.opencode/skills/`:

- `system-design`
- `fastapi-standards`
- `nextjs-standards`
- `agentic-ai`
- `mcp-development`
- `testing`
- `security-review`
- `documentation`

Load the relevant skill before starting work in its domain. Skills are guidance; `AGENTS.md` and explicit user instructions take precedence.

## Permission model

- Global `task` is `deny`. Only the orchestrator has an explicit specialist allowlist; specialists deny delegation.
- `read` and `edit` ask for `.env*` files (except `.env.example`), private keys, credentials, secrets directories, and common credential files.
- `edit` also asks for `AGENTS.md`, `opencode.json`, `opencode.jsonc`, and files under `.opencode/`.
- Paths containing `..` are denied for `read` and `edit` to reduce path-traversal risk.
- Bash allows common read-only and non-destructive development commands. Approval is required for installs, service lifecycle changes, commits, and pushes. Shell composition is set to `ask` as a fail-safe, but OpenCode may allow a chain when every parsed command is allowed (confirmed with `pwd && ls`). Destructive commands are denied.
- Permissions are **not** a filesystem sandbox. They gate OpenCode tool calls; they do not provide runtime isolation. Use separate OS-level isolation if that is required.

## Verification commands

Run the narrowest relevant command and report its actual output:

```bash
opencode --version
opencode agent list
opencode debug skill
opencode debug agent orchestrator
opencode debug agent architect
opencode debug agent reviewer
```

`opencode debug config` is intentionally `ask` because its resolved output can include provider configuration. Request approval before running it.

Application-level commands will be added once the stack is initialized. Until then, do not invent test or build commands.

## Current phase

Step 0.1 only: OpenCode development-agent configuration, hardened permissions, skills, project instructions, and documentation. Do not initialize the application or begin coding NEXUS AI until the user explicitly requests it.
