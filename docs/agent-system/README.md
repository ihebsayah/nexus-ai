# NEXUS AI OpenCode Development Agent System

This document describes the **OpenCode development agents** used to build NEXUS AI. It does not describe NEXUS AI's runtime agents, which are product behavior built with LangGraph, MCP, Ollama, and pgvector.

## Purpose

The system gives NEXUS AI a small, explicit division of labor:

- One primary coordinator (`orchestrator`).
- Eight specialist subagents with narrow responsibilities.
- Eight reusable skills loaded on demand.
- Project-level permissions that require approval for risky actions.

The goal is maintainable, verifiable work on a local-first stack, not autonomous parallelism.

## Configuration layout

```text
opencode.json                  Project config: default agent, permissions, subagent depth
AGENTS.md                      Global project rules and agent map
.opencode/agents/              OpenCode agent definitions
  orchestrator.md
  architect.md
  backend.md
  frontend.md
  ai-engineer.md
  data-engineer.md
  devops.md
  qa.md
  reviewer.md
.opencode/skills/              Reusable skills
  system-design/SKILL.md
  fastapi-standards/SKILL.md
  nextjs-standards/SKILL.md
  agentic-ai/SKILL.md
  mcp-development/SKILL.md
  testing/SKILL.md
  security-review/SKILL.md
  documentation/SKILL.md
docs/agent-system/             This documentation and the verification report
```

## Agent roster

| Agent | Mode | Use it for | Default write access |
| --- | --- | --- | --- |
| `orchestrator` | primary | Planning, delegation, integration, final verification | Yes, with approval rules |
| `architect` | subagent | Architecture analysis, boundaries, ADRs, trade-offs | `docs/` only |
| `backend` | subagent | FastAPI, PostgreSQL, pgvector, API contracts, backend tests | Yes, with approval rules |
| `frontend` | subagent | Next.js App Router, React, TypeScript, UX, accessibility | Yes, with approval rules |
| `ai-engineer` | subagent | LangGraph, MCP, RAG, Ollama, evaluations | Yes, with approval rules |
| `data-engineer` | subagent | dbt, pipelines, scikit-learn, MLflow, data quality | Yes, with approval rules |
| `devops` | subagent | Docker Compose, local environments, CI, observability | Yes, with approval rules |
| `qa` | subagent | Automated tests, integration tests, security validation | Yes, with approval rules |
| `reviewer` | subagent | Independent read-only code and architecture review | No |

## Delegation model

`opencode.json` sets `subagent_depth` to `1`. This means:

- The primary `orchestrator` can invoke specialist subagents through the Task tool.
- A specialist cannot invoke another subagent.
- Delegation is explicit and sequential; there is no automatic parallel delegation.

The orchestrator's `permission.task` allows only the eight named specialists and denies everything else. Each specialist sets `task: deny`, which documents the boundary even though the depth limit already prevents nesting.

Users can still invoke any subagent directly with `@agent-name` in the TUI.

## Recommended workflow

1. **Start with the orchestrator.** It is the default primary agent.
2. **State the goal, constraints, and definition of done.** Mention the current phase if relevant.
3. **Let the orchestrator plan.** It should produce small tasks with verification steps.
4. **Delegate to one specialist per task.** The orchestrator chooses from the roster.
5. **Require evidence.** Tests, lint, typecheck, build, and evaluation results must be executed, not assumed.
6. **Review before integration.** Use `reviewer` for significant code, architecture, or security changes.
7. **Record decisions.** Use `architect` for ADRs under `docs/adr/`.
8. **Report blockers.** Incomplete verification must be stated explicitly.

### Example prompts

```text
@orchestrator Plan the Step 1 FastAPI skeleton. Do not implement yet.
@orchestrator Delegate the API contract for document ingestion to backend.
@architect Write an ADR comparing a modular monolith and separate services for NEXUS AI.
@reviewer Review the current diff read-only and report findings by severity.
@qa Add integration tests for the pgvector retrieval path and run them.
```

## Skills

Skills are loaded on demand with the native `skill` tool. The agent sees each skill's name and description, then loads the full instructions when the task matches.

| Skill | Primary users | Trigger |
| --- | --- | --- |
| `system-design` | `architect`, `orchestrator`, `reviewer` | Architecture, boundaries, ADRs, trade-offs |
| `fastapi-standards` | `backend` | FastAPI, Pydantic, SQLAlchemy, Alembic, pgvector |
| `nextjs-standards` | `frontend` | Next.js, React, TypeScript, accessibility, frontend build |
| `agentic-ai` | `ai-engineer` | LangGraph, RAG, Ollama, evaluations |
| `mcp-development` | `ai-engineer` | MCP servers, clients, tools, resources, stdio |
| `testing` | `qa`, all implementers | Test design, execution, coverage, regression |
| `security-review` | `reviewer`, `qa`, `backend`, `devops` | Auth, secrets, injection, exposure, dependencies |
| `documentation` | `architect`, `devops`, `data-engineer` | README, ADR, runbook, API docs |

Skills do not repeat the global rules in `AGENTS.md`; those rules always apply.

## Permission model

The project config sets a conservative baseline. Permission patterns use OpenCode's simple wildcards (`*`, `?`); the last matching rule wins.

- `read` allows normal files, but asks for `.env*` (except `.env.example`), private keys, credentials, secrets directories, and common credential files. Paths containing `..` are denied.
- `edit` allows application source files, but asks for `AGENTS.md`, `opencode.json`, `opencode.jsonc`, `*.opencode/*`, the same secret patterns, and paths containing `..`.
- `glob`, `grep`, `list`, `lsp`, `skill`, `question`, and `todowrite` are allowed. `grep`, `glob`, and LSP are not path-scoped by the permission rules; do not store secrets in the workspace.
- Web fetch, web search, external directories, and doom-loop recovery require approval.
- Bash commands require approval by default. Common read-only commands, test/lint/typecheck/build commands, and safe verification commands are allowed. Shell composition (`;`, `&&`, `||`, `|`, backticks, `$(`, redirection, background `&`) requires approval.
- Commits, pushes, dependency installations, container lifecycle commands, and package-manager installs require approval.
- Destructive commands (`rm -rf`, `git reset --hard`, `git clean`, `git push --force`, `docker system prune`, `docker volume prune`, `sudo`, `doas`) are denied.
- `opencode debug config` requires approval because its resolved output can include provider configuration. `opencode --version`, `opencode agent list`, `opencode debug skill`, and `opencode debug agent *` are allowed.

The `architect` can write only under `docs/`, with secret-pattern asks under `docs/` and a trailing `*..*` deny. The `reviewer` cannot edit files, cannot use the web, and can run only read-only Git commands.

### Important limitation

Permissions are **not** a filesystem sandbox. They gate OpenCode tool calls, not arbitrary behavior inside a shell command. The `bash` tool is the main escape hatch, which is why risky commands require approval or are denied. `cat`, `grep`, `find`, and `rg` are intentionally not allowlisted in bash; use the dedicated read/search tools so `.env` approvals still apply. OpenCode documents bash matching against parsed commands; a safe chain (`pwd && ls`) was allowed in a fresh session, while shell composition is also explicitly set to `ask` as a fail-safe. A denied command inside a chain was not tested. `grep`, `glob`, and LSP are not path-scoped and may still expose secret file names or contents. Do not describe this configuration as hard isolation.

## Adding an agent

1. Create `.opencode/agents/<name>.md`.
2. Add frontmatter with `description`, `mode`, `temperature`, and `permission`.
3. Keep the body focused on scope, workflow, output contract, and boundaries.
4. If the orchestrator should delegate to it, add the name to `permission.task` in `.opencode/agents/orchestrator.md`.
5. Run `opencode agent list` and `opencode debug agent <name>`.
6. Restart OpenCode after config changes.

## Adding a skill

1. Create `.opencode/skills/<name>/SKILL.md`.
2. Use frontmatter with `name`, `description`, `license`, `compatibility`, and `metadata`.
3. Make `name` match the directory and use lowercase hyphenated words.
4. Include when to use, instructions, checklist, expected output, and verification.
5. Run `opencode debug skill` and confirm the skill is listed.
6. Restart OpenCode after changes.

## Validation

Run these from the project root:

```bash
opencode --version
opencode agent list
opencode debug skill
opencode debug agent orchestrator
opencode debug agent architect
opencode debug agent reviewer
```

`opencode debug config` requires approval because its resolved output can include provider configuration.

The observed results are recorded in `docs/agent-system/verification.md`.

## Known limitations

- OpenCode 1.19.4 has no `opencode skill` subcommand; skill discovery is validated with `opencode debug skill`.
- `subagent_depth` defaults to `1`; this configuration makes it explicit but does not add parallel orchestration.
- Agent permissions are not a hard sandbox.
- Bash file inspection is intentionally narrow; use the dedicated read/search tools.
- Shell-operator matching relies on OpenCode's documented parsed-command behavior. A safe chain (`pwd && ls`) was allowed in a fresh session; a denied command inside a chain was not tested. Shell composition is also set to `ask` as a fail-safe.
- `grep`, `glob`, and LSP are not path-scoped by the permission rules and may still expose secret file names or contents. Do not store secrets in the workspace.
- The global OpenCode configuration may contain unrelated agents and skills. They remain visible unless explicitly disabled; this project does not disable them.
- Model selection is inherited from the active OpenCode model. No model IDs are hardcoded in this project, so the configuration does not assume a provider.
- Application-level lint, test, and build commands do not exist yet. They must be added when the stack is initialized.
- OpenCode may auto-create `.opencode/package.json`, `.opencode/package-lock.json`, and `.opencode/node_modules/` for plugin support. These are gitignored; do not remove them without approval.

## Current phase

Step 0.1 only: OpenCode development-agent configuration, hardened permissions, skills, project instructions, and documentation. Do not initialize the application or begin coding NEXUS AI until the user explicitly requests it.
