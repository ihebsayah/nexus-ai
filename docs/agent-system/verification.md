# Agent System Verification Report

Date: 2026-11-05
Platform: macOS 26.0.1 (arm64, Apple M1), zsh
OpenCode: 1.19.4

This report records commands that were actually executed and the output that was observed. No application code was generated. No commits, pushes, or infrastructure changes were performed. OpenCode later auto-created plugin support files under `.opencode/`; see section 12.

> Sections 1–11 record the original Step 0 validation and smoke test. Section 12 records Step 0.1 hardening and supersedes the Step 0 permission counts, the `docs/**` architect rule, and related limitations where noted.

## 1. Environment and OpenCode version

Commands:

```bash
uname -m
sw_vers -productVersion
sysctl -n machdep.cpu.brand_string
opencode --version
```

Observed:

```text
arm64
26.0.1
Apple M1
1.19.4
```

## 2. Project config syntax and resolution

Command:

```bash
opencode debug config
```

Observed, after parsing the emitted JSON:

```text
default_agent: orchestrator
subagent_depth: 1
project_agents: ['ai-engineer', 'architect', 'backend', 'data-engineer', 'devops', 'frontend', 'orchestrator', 'qa', 'reviewer']
permission_keys: ['bash', 'doom_loop', 'edit', 'external_directory', 'glob', 'grep', 'list', 'lsp', 'question', 'read', 'skill', 'task', 'todowrite', 'webfetch', 'websearch']
bash_rules: 54
```

Result: the project config loaded and resolved. The default agent is a primary agent. `subagent_depth` is explicitly `1`.

Additional check:

```bash
python3 -m json.tool opencode.json
```

Observed: valid JSON.

## 3. Agent discovery

Command:

```bash
opencode agent list
```

The full output was captured to a temporary file because it is verbose. A parser matched lines of the form `name (primary|subagent|all)` and found 16 simple-name entries:

```text
build: primary
compaction: primary
explore: subagent
general: subagent
plan: primary
summary: primary
title: primary
ai-engineer: subagent
architect: subagent
backend: subagent
data-engineer: subagent
devops: subagent
frontend: subagent
orchestrator: primary
qa: subagent
reviewer: subagent
```

All nine project agents are present. The parser does not count global agents whose names contain spaces; that is a limitation of the parser, not evidence that those agents are missing.

Per-agent resolution:

```bash
opencode debug agent <name>
```

Observed:

```text
orchestrator: mode=primary permission_rules=106 description=yes
architect: mode=subagent permission_rules=113 description=yes
backend: mode=subagent permission_rules=98 description=yes
frontend: mode=subagent permission_rules=98 description=yes
ai-engineer: mode=subagent permission_rules=98 description=yes
data-engineer: mode=subagent permission_rules=98 description=yes
devops: mode=subagent permission_rules=98 description=yes
qa: mode=subagent permission_rules=98 description=yes
reviewer: mode=subagent permission_rules=113 description=yes
```

Result: all nine agents resolve with a mode and description.

## 4. Skill discovery

OpenCode 1.19.4 has no `opencode skill` subcommand. The supported discovery command is `opencode debug skill`.

Command:

```bash
opencode debug skill
```

Observed:

```text
total: 17
duplicates: none
project_skills: ['fastapi-standards', 'agentic-ai', 'mcp-development', 'system-design', 'documentation', 'testing', 'security-review', 'nextjs-standards']
```

All eight project skills are discovered. No duplicate skill names were found across the loaded locations.

## 5. Skill frontmatter validation

A local validation script checked each `.opencode/skills/*/SKILL.md` for:

- frontmatter present
- `name` matches the containing directory
- `name` matches `^[a-z0-9]+(-[a-z0-9]+)*$`
- name length 1–64
- description length 1–1024
- `license`, `compatibility`, and `metadata` present
- unique names

Observed:

```text
.opencode/skills/agentic-ai/SKILL.md: OK
.opencode/skills/documentation/SKILL.md: OK
.opencode/skills/fastapi-standards/SKILL.md: OK
.opencode/skills/mcp-development/SKILL.md: OK
.opencode/skills/nextjs-standards/SKILL.md: OK
.opencode/skills/security-review/SKILL.md: OK
.opencode/skills/system-design/SKILL.md: OK
.opencode/skills/testing/SKILL.md: OK
ALL_SKILLS_VALID
```

## 6. Agent frontmatter validation

A local validation script checked that each agent file uses only documented top-level frontmatter fields.

Observed:

```text
ai-engineer.md: fields=['description', 'mode', 'temperature', 'color', 'permission'] unknown=none
architect.md: fields=['description', 'mode', 'temperature', 'color', 'permission'] unknown=none
backend.md: fields=['description', 'mode', 'temperature', 'color', 'permission'] unknown=none
data-engineer.md: fields=['description', 'mode', 'temperature', 'color', 'permission'] unknown=none
devops.md: fields=['description', 'mode', 'temperature', 'color', 'permission'] unknown=none
frontend.md: fields=['description', 'mode', 'temperature', 'color', 'permission'] unknown=none
orchestrator.md: fields=['description', 'mode', 'temperature', 'color', 'permission'] unknown=none
qa.md: fields=['description', 'mode', 'temperature', 'color', 'permission'] unknown=none
reviewer.md: fields=['description', 'mode', 'temperature', 'color', 'permission'] unknown=none
```

Result: no undocumented agent frontmatter fields were used.

## 7. Permission and delegation boundary inspection

The resolved `opencode debug agent` output was inspected for the relevant rules. Because the last matching rule wins, the agent-specific rules appended after the global baseline are the effective ones.

Observed effective rules:

- `orchestrator`: `task` denies `*` and then allows `architect`, `backend`, `frontend`, `ai-engineer`, `data-engineer`, `devops`, `qa`, and `reviewer`.
- Every specialist: `task` denies `*`, so it cannot delegate.
- `architect`: `edit` denies `*` and allows `docs/**` in Step 0 (superseded in Step 0.1 by `docs/*`, secret asks, and a trailing `*..*` deny); `bash` denies `*` and allows `ls` plus read-only Git commands.
- `reviewer`: `edit` denies `*`; `task` denies `*`; `webfetch` and `websearch` deny `*`; `bash` denies `*` and allows only read-only Git commands.
- Global baseline: risky bash commands require approval; destructive commands are denied.

Result: the intended delegation and read-only boundaries are present in the resolved configuration.

## 7.1 Conflict and consistency review

Manual review of the written configuration and prompts found:

- `AGENTS.md`, `docs/agent-system/README.md`, and `opencode.json` agree that `orchestrator` is the default primary agent.
- The orchestrator's delegation matrix matches its `permission.task` allowlist exactly.
- Every specialist sets `task: deny`, consistent with the documented `subagent_depth: 1` boundary.
- The architect prompt says docs/ADRs only; its Step 0 `edit` permission allowed only `docs/**` (superseded in Step 0.1).
- The reviewer prompt says read-only; its `edit`, `task`, `webfetch`, and `websearch` permissions deny access, and its bash access is limited to read-only Git commands.
- Agent prompts reference only skills that exist in `.opencode/skills/`.
- No project agent name duplicates another project agent name.
- No skill name duplicates another loaded skill name.
- No agent prompt introduces a paid service or contradicts the global rules in `AGENTS.md`.

## 8. Final configuration tree

```text
nexus-ai/
├── .opencode/
│   ├── agents/
│   │   ├── ai-engineer.md
│   │   ├── architect.md
│   │   ├── backend.md
│   │   ├── data-engineer.md
│   │   ├── devops.md
│   │   ├── frontend.md
│   │   ├── orchestrator.md
│   │   ├── qa.md
│   │   └── reviewer.md
│   ├── skills/
│   │   ├── agentic-ai/
│   │   │   └── SKILL.md
│   │   ├── documentation/
│   │   │   └── SKILL.md
│   │   ├── fastapi-standards/
│   │   │   └── SKILL.md
│   │   ├── mcp-development/
│   │   │   └── SKILL.md
│   │   ├── nextjs-standards/
│   │   │   └── SKILL.md
│   │   ├── security-review/
│   │   │   └── SKILL.md
│   │   ├── system-design/
│   │   │   └── SKILL.md
│   │   └── testing/
│   │       └── SKILL.md
│   └── .gitignore
├── docs/
│   ├── adr/
│   │   └── README.md
│   └── agent-system/
│       ├── README.md
│       └── verification.md
├── AGENTS.md
└── opencode.json
```

The `.opencode/.gitignore` file was present and was preserved.

## 9. Limitations and verification gaps

1. **Restart required.** OpenCode loads configuration, agents, and skills at startup. The current session may not see the new skills or agents until OpenCode is restarted.
2. **No `opencode skill` subcommand.** Skill discovery was verified with `opencode debug skill`, the supported command in this version.
3. **Permissions are not a hard sandbox.** They gate OpenCode tool calls. The `bash` tool is the main escape hatch; risky commands require approval or are denied, but this is not filesystem isolation.
4. **No nested delegation.** `subagent_depth` is `1`. Specialists cannot invoke other subagents. There is no automatic parallel delegation.
5. **Architect edit restriction was not exercised with a live write.** Step 0 used `docs/**`; Step 0.1 replaced it with `docs/*`, secret-pattern asks under `docs/`, and a trailing `*..*` deny. Effective rules were inspected, but no live write to a secret-like file was attempted.
6. **Bash permission matching was not exercised with a risky command.** The resolved rules were inspected, but no commit, install, or destructive command was run to trigger an approval prompt or denial.
7. **Global agents and skills remain visible.** Unrelated global OpenCode agents and external skills are still loaded. They were not disabled because that would change the user's global environment.
8. **No model IDs are pinned.** Agents inherit the active OpenCode model. Per-agent models can be added after a provider and local model are chosen.
9. **Application-level commands do not exist yet.** There is no application test, lint, typecheck, or build command to run at Step 0. Do not invent them.
10. **Bash file inspection is intentionally narrow.** `cat`, `grep`, `find`, and `rg` are not allowlisted in bash. Agents should use the dedicated `read`, `grep`, `glob`, and `list` tools. Step 0.1 also adds explicit `read`/`edit` asks for `.env*`, private keys, credentials, and secrets paths.
11. **Global provider config was not changed.** The existing global config contains a provider named `nararouter`; the active model remains `opencode/big-pickle`. This project config does not add any provider or paid service, and Ollama was not configured. If strictly local development models are required, the global provider configuration should be reviewed separately.

## 10. Unresolved questions

- Should unrelated global OpenCode agents and external skills be disabled or hidden for this project?
- Should each development agent be pinned to a specific local model, or continue inheriting the active model?
- Resolved in Step 0.1: the architect keeps `docs/*` write access, with secret-pattern asks and a trailing `*..*` deny.
- Should a project `.gitignore` be added when the repository is initialized, including `.env` and local data directories?
- What application-level verification commands should be added in Step 1?

## 11. Conclusion

Step 0 is complete: the project has a working OpenCode development-agent architecture, a validated skill library, project instructions, usage documentation, and this verification report. Step 0.1 hardening is recorded in section 12.

The configuration was validated for syntax, agent discovery, skill discovery, frontmatter, and resolved delegation/permission rules. The limitations above are known and should be addressed before or during Step 1.

## 12. Step 0.1 hardening

Date: 2026-11-05

Goal: resolve the five reviewer findings from the Step 0 smoke test, preserve the active `opencode/big-pickle` model and `nararouter` provider, and avoid configuring Ollama or application code.

### 12.1 Changes

- `opencode.json`
  - Global `task: deny`; the orchestrator's explicit specialist allowlist remains.
  - `read` asks for `.env*` (except `.env.example`), private keys, credentials, secrets directories, `.ssh`, `.aws`, `.kube/config`, and gcloud config.
  - `edit` asks for the same secret patterns plus `AGENTS.md`, `opencode.json`, `opencode.jsonc`, and `*.opencode/*`.
  - `read` and `edit` deny paths containing `..`.
  - Bash defaults to `ask`; safe read-only, test, lint, typecheck, build, and verification commands are allowed; installs, commits, pushes, and service lifecycle changes ask; shell composition is set to `ask` as a fail-safe, but a chain of allowed parsed commands may be allowed; destructive commands are denied.
  - `opencode debug config` is explicitly `ask`; `opencode --version`, `opencode agent list`, `opencode debug skill`, and `opencode debug agent *` are allowed.
- `AGENTS.md`
  - Added the protected-config approval rule.
  - Replaced the permission model and verification sections with the hardened behavior.
  - Set the current phase to Step 0.1.
- `docs/agent-system/README.md`
  - Aligned the permission model, validation commands, and limitations with the hardened config.
- `.opencode/agents/architect.md`
  - Changed `docs/**` to `docs/*`.
  - Added 22 `docs/...` secret-pattern `ask` rules before a trailing `*..*` deny.
  - Preserved `edit: "*": deny` and `task: "*": deny`.
- `.opencode/agents/reviewer.md`
  - Preserved `edit`, `task`, `webfetch`, and `websearch` denies; bash remains read-only Git.

### 12.2 Permission counts before and after

Resolved rule counts from `opencode debug agent`. Counts include OpenCode defaults plus project and agent rules.

| Agent | Before total | After total | Before bash | After bash |
| --- | ---: | ---: | ---: | ---: |
| orchestrator | 106 | 254 | 54 | 126 |
| architect | 113 | 284 | 67 | 139 |
| reviewer | 113 | 261 | 66 | 138 |
| backend | 98 | 246 | 54 | 126 |
| frontend | 98 | 246 | 54 | 126 |
| ai-engineer | 98 | 246 | 54 | 126 |
| data-engineer | 98 | 246 | 54 | 126 |
| devops | 98 | 246 | 54 | 126 |
| qa | 98 | 246 | 54 | 126 |

Global `bash_rules` after hardening: `126`. Global `read` rules: `41`; global `edit` rules: `41`.

Before hardening, the resolved `read` list ended with `*: allow`, which overrode the `.env` asks; `edit` was a single global allow; `task` was a global allow; the architect accepted `docs/**`.

### 12.3 Effective permission checks

The resolved rule lists were inspected. Representative last-match results:

```text
orchestrator/backend edit:
  docs/adr/README.md -> allow
  docs/.env -> ask
  docs/sub/.env -> ask
  docs/credentials.json -> ask
  docs/secrets/token -> ask
  docs/sub/.ssh/id_rsa -> ask
  AGENTS.md -> ask
  opencode.json -> ask
  .opencode/agents/foo.md -> ask
  src/foo.ts -> allow
  docs/../AGENTS.md -> deny

architect edit:
  docs/adr/README.md -> allow
  docs/.env -> ask
  docs/sub/.env -> ask
  docs/credentials.json -> ask
  docs/secrets/token -> ask
  docs/sub/.ssh/id_rsa -> ask
  AGENTS.md -> deny
  opencode.json -> deny
  .opencode/agents/foo.md -> deny
  src/foo.ts -> deny
  docs/../AGENTS.md -> deny

reviewer edit:
  all inspected paths -> deny

orchestrator task:
  architect -> allow
  reviewer -> allow
  explore -> deny
  general -> deny

specialist task:
  all inspected targets -> deny
```

`read` results were consistent: `.env`, `.env.local`, and `docs/.env` -> `ask`; `.env.example` -> `allow`; `src/foo.ts` -> `allow`; `docs/../AGENTS.md` -> `deny`.

### 12.4 Commands and observed results

```bash
python3 -m json.tool opencode.json
```

Observed: valid JSON.

```bash
opencode debug config
```

Observed: `default_agent: orchestrator`; `subagent_depth: 1`; `bash_rules: 126`; `task: deny`; `read_keys: 37`; `edit_keys: 41`; all 9 project agents present. This command was run in the current session for inspection; the resolved rule for agent use is `ask`, and `opencode debug config` was not run through a fresh agent session because its output can include provider configuration.

```bash
opencode agent list
```

Observed: 16 total agents; all 9 project agents present; none missing.

```bash
opencode debug skill
```

Observed: 17 skills; no duplicates; all 8 project skills present.

```bash
opencode debug agent orchestrator
opencode debug agent architect
opencode debug agent reviewer
opencode debug agent backend
# and the other five project agents
```

Observed, after parsing the emitted JSON:

```text
orchestrator: total=254 bash=126 task=10 edit=41 read=41 mode=primary desc=yes
architect: total=284 bash=139 task=2 edit=66 read=41 mode=subagent desc=yes
backend: total=246 bash=126 task=2 edit=41 read=41 mode=subagent desc=yes
frontend: total=246 bash=126 task=2 edit=41 read=41 mode=subagent desc=yes
ai-engineer: total=246 bash=126 task=2 edit=41 read=41 mode=subagent desc=yes
data-engineer: total=246 bash=126 task=2 edit=41 read=41 mode=subagent desc=yes
devops: total=246 bash=126 task=2 edit=41 read=41 mode=subagent desc=yes
qa: total=246 bash=126 task=2 edit=41 read=41 mode=subagent desc=yes
reviewer: total=261 bash=138 task=2 edit=42 read=41 mode=subagent desc=yes
```

Safe shell-composition test in a fresh CLI session:

```bash
opencode run --agent orchestrator "Run exactly the bash command 'pwd && ls' and report the observed output. Do not use any other tool. Do not modify files."
```

Observed: the orchestrator ran `pwd && ls` and reported the working directory and visible entries (`AGENTS.md`, `docs`, `opencode.json`). No approval prompt was observed in the non-interactive run. This is consistent with OpenCode matching the parsed commands (`pwd` and `ls`) rather than the whole string. A denied command in a chain was not tested; the explicit shell-operator `ask` rules remain as a fail-safe.

### 12.5 Findings resolved

1. **Global edit allow**: resolved by protected-config and secret-file `ask` rules in `edit`.
2. **Broad bash patterns**: resolved by `*: ask`, explicit safe allowlists, shell-composition asks, and destructive denies.
3. **No secret-file protections**: resolved by `read`/`edit` asks for `.env*`, keys, credentials, secrets, `.ssh`, `.aws`, `.kube/config`, and gcloud config.
4. **Verification commands required approval**: resolved by allowing `opencode --version`, `opencode agent list`, `opencode debug skill`, and `opencode debug agent *`; `opencode debug config` stays `ask`.
5. **Global task allow**: resolved by global `task: deny` plus the orchestrator allowlist.

Additional issues found during verification:

- The architect's `docs/**` allow overran the global `*..*` deny for paths like `docs/../AGENTS.md`; fixed with `docs/*` and a trailing `*..*` deny.
- The architect's `docs/*` allow overran global secret asks for paths like `docs/.env`; fixed with 22 `docs/...` secret-pattern `ask` rules.

### 12.6 Remaining risks and gaps

1. **Current session is stale.** The interactive session that produced this report was started before the hardening. It may still use old permissions and cannot see project agents/skills. Restart OpenCode before interactive use.
2. **Permissions are not a sandbox.** They gate OpenCode tool calls; bash remains an escape hatch. The safe `pwd && ls` chain was tested, but no denied or destructive chain was executed.
3. **Secret patterns were inspected, not live-tested.** Effective rule order was checked with resolved rules and a local wildcard matcher; no live secret-like file write was attempted.
4. **`grep`, `glob`, and LSP are not path-scoped.** They may expose secret file names or contents; do not store secrets in the workspace.
5. **Auto-generated plugin files.** `.opencode/package.json`, `.opencode/package-lock.json`, and `.opencode/node_modules/` contain `@opencode-ai/plugin@1.19.4`; they are gitignored and were not removed. No explicit install command was run.
6. **Local-only and zero-paid use are not verified.** Ollama client `0.33.0` exists but the server is not running; no local model was tested. The active model remains `opencode/big-pickle` on the `nararouter` provider.
7. **ADR recommendations are not implemented.** ADR-0001 (runtime topology/memory budget) and ADR-0002 (local-only dependency/trust boundary) are recommended but not created.
8. **Application commands do not exist.** No application test, lint, typecheck, or build command is available at Step 0.1.

### 12.7 Conclusion

Step 0.1 hardening is complete. The five reviewer findings are addressed, representative effective permissions were inspected, all project agents and skills remain discoverable, and the safe shell-composition test passed. Remaining risks are documented above. Do not begin application development until the user explicitly requests it.
