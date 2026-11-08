# M1.1 — Repository and tooling verification

Date: 2026-11-07
Current status: **M1.1 PASS**, independently approved with comments, using the documented Webpack build fallback. Default Turbopack is BLOCKED by local worker-port permissions. No M1.2 work has begun.

## Baseline and authorization

Root and working directory were confirmed as `/Users/ihebsayah/Documents/my portfolio/nexus-ai`.

Before M1.1, the workspace contained backend/frontend scaffolding, a Makefile, placeholder `infra/` and cross-layer `tests/`, documentation and OpenCode development-agent configuration. It was not inside a Git worktree. No backend/frontend lockfiles or local dependency environments existed. The initial backend factory had no routes; Tailwind wiring was absent.

The first M1.1 pass preserved that work, added a process-only `/health` route, smoke tests and Tailwind, and prepared safe verification commands. Global backend diagnostics passed four tests in 0.51s; all seven pinned-environment checks were BLOCKED. QA and reviewer corrections included explicit localhost server scripts, views of current milestone status, dependency counts and no-implicit-install checks. That preapproval verdict was PARTIAL; it is superseded by the installed-environment evidence below.

The owner subsequently explicitly approved:

- Backend: `UV_PYTHON_DOWNLOADS=never uv sync --python python3.13`.
- Frontend: inspect the pin and manager, then `corepack pnpm install` if compatible.
- Confirmed project root: `git init`.

No dependency pin was upgraded, no existing lockfile was overwritten, and no unrelated direct dependency was installed. The earlier application scaffolding and all protected OpenCode files were preserved.

## Toolchain and package-manager prerequisite

| Command/inspection | Observed version/result |
| --- | --- |
| `python3 --version` | Python 3.13.3 |
| `node --version` | v22.17.0 |
| `npm --version` | 10.9.2 (baseline inspection) |
| `uv --version` | uv 0.8.2 (21fadbcc1 2025-07-22) |
| `corepack --version` | 0.33.0 |
| `git --version` | git version 2.50.1 (baseline inspection) |
| `COREPACK_ENABLE_NETWORK=0 corepack pnpm --version` from frontend | 10.15.1, exit 0; manager already cached |
| `frontend/package.json` | `packageManager: pnpm@10.15.1`, pnpm engine 10.15.1, Node engine `>=22.17.0 <23` |

The installed Node and manager satisfy the declared constraints. A newer pnpm advertisement was ignored. Big Pickle remains the intended OpenCode development model; effective external selection was not probed. Ollama is a future NEXUS AI runtime dependency.

## Installation and Git execution

| Exact command | Actual result |
| --- | --- |
| Backend: `UV_PYTHON_DOWNLOADS=never uv sync --python python3.13` | Initial sandbox attempt: exit 2 on package-cache permission. Approved-access retry: exit 0; CPython 3.13.3, 30 lock entries, 29 installed packages including editable backend 0.1.0. No Python download. |
| Frontend: `corepack pnpm install` | Initial sandbox attempt: exit 1 with registry DNS ENOTFOUND. Approved-access retry: exit 0 in 2m 40.6s, using pnpm 10.15.1; resolved 462, reused 51, downloaded 327, added 376 packages. |
| Root: `git init` | Initial sandbox attempt: exit 1 on `.git` permission. Approved-access retry: exit 0; initialized empty repository on default `master` branch. No staging, commit, push or Git config changes. |

The retries addressed sandbox restrictions, not dependency/version changes. Package-cache writes and new local environments were within the approved installation scope.

## Executed verification

| Command/check | Actual result |
| --- | --- |
| Root: `make -k backend-lint backend-typecheck backend-test` | Exit 0. Ruff lint passes; 11 files already formatted; mypy reports no issues in 11 source files; pytest 9.2.0: 4 passed, 1 warning in 1.29s. |
| Root: `make -k frontend-lint frontend-typecheck frontend-test frontend-build` | ESLint, TypeScript and Vitest pass (1 file/1 test). Combined exit 2 because default Turbopack build fails on worker-port permission. |
| Root, broader-access retry: `make frontend-build` | Exit 2; same Turbopack `creating new process / binding to a port / Operation not permitted` failure. |
| `frontend/node_modules/.bin/next build --help` | Exit 0; bundled CLI confirms supported `--webpack` option. |
| Frontend: `NEXT_TELEMETRY_DISABLED=1 node_modules/.bin/next build --webpack` | Exit 0; production build compiles and prerenders `/` and `/_not-found`. |
| Root: `make verify NEXT_BUILD_FLAGS=--webpack` before reviewer CI safeguard | **Exit 0**. Ruff lint/format, ESLint, mypy, Next route-type generation, TypeScript, backend tests (4 passed, 1 warning in 0.34s), frontend test (1 passed) and Webpack production build all pass sequentially. |
| Root: `make frontend-typecheck frontend-build NEXT_BUILD_FLAGS=--webpack` after reviewer safeguard | **Exit 0**. Both Next invocations use local `CI=1`; type generation, TypeScript and Webpack production build pass. No dependency or lockfile changes. |
| Installed backend import/version assertions using `.venv/bin/python`, without PYTHONPATH | Exit 0. All six runtime/dev pins match; editable `nexus-ai-backend==0.1.0` imports from `backend/src/nexus`. |
| `UV_CACHE_DIR=/tmp/nexus-m11-uv-cache uv pip check --python backend/.venv/bin/python` | Exit 0; 29 installed packages checked, all compatible. A prior default-cache attempt was sandbox-denied. |
| Backend: `UV_CACHE_DIR=/tmp/nexus-m11-uv-cache UV_PYTHON_DOWNLOADS=never uv lock --check --offline` | Exit 0; resolved 30 packages in 14ms; lock agrees with project metadata. |
| Frontend installed-version assertions; `corepack pnpm list --depth 0 --json` from frontend | Exit 0; all 13 direct packages match manifest pins. An earlier listing from root returned only the root directory and was not used as dependency evidence. |
| Python TOML/JSON/AST checks and Node configuration syntax checks | Passed during QA: backend TOML, three JSON files, 11 Python sources, ESLint and PostCSS `.mjs` syntax. |

These are executed local checks, not latency, memory or security benchmarks. Both tests and typechecking use the installed pinned environment in the final run. No production application service was started.

## Build fallback and generated configuration

Default Turbopack requires a PostCSS worker port unavailable in this execution environment, even after the broader-access retry. It remains **BLOCKED here**. Webpack is an existing supported Next.js build mode, requiring no new dependency or version change; its production build passed. No relative performance claim is made. `NEXT_BUILD_FLAGS=--webpack` is an explicit Makefile override; the default Next build mode and package scripts remain intact.

Next added `.next/dev/types/**/*.ts` to TypeScript's include list. All original includes and compiler options were preserved; broad auto-formatting was reduced to the single additive include. Next also regenerated `next-env.d.ts`, preserving its original reference declarations and adding generated route/root-parameter imports. That generated file remains on disk but is now ignored by Git. `make frontend-typecheck` runs `next typegen` before TypeScript so generated declarations can be recreated after checkout. Build/type generation disables Next telemetry and sets `CI=1` locally to prevent Next from auto-installing missing TypeScript packages. This validation-mode flag does not introduce a hosted CI service.

## Lockfile review and resolved versions

Both application locks are new, not replacements. Backend lock format is version 1/revision 2, Python `==3.13.*`: 30 records include the editable package and platform-conditional dependencies (29 packages installed here). Every registry dependency uses public PyPI; dependency references resolve; artifact SHA-256 hashes are present. The pinned build backend remains Hatchling 1.33.0 in `pyproject.toml` and is acquired in build isolation, not installed as an application runtime package.

Frontend lock format is 9.0. An already-installed js-yaml dependency parsed the lock without adding packages: all 13 importer pins agree with the manifest, and all 462 package records have SHA-512 integrity values; there are 462 snapshots. No VCS/custom-tarball source was found. The 376 installed packages differ from lock record count because the lock includes optional/platform variants and peer resolutions. This is not a claim of testing other platforms.

| Backend lock package | Resolved version |
| --- | --- |
| annotated-doc | 0.0.5 |
| annotated-types | 0.8.0 |
| anyio | 4.16.0 |
| ast-serialize | 0.13.1 |
| certifi | 2026.10.23 |
| click | 8.5.1 |
| colorama | 0.4.6 |
| fastapi | 0.162.2 |
| h11 | 0.16.0 |
| httpcore | 1.0.9 |
| httpx | 0.28.1 |
| idna | 3.20 |
| iniconfig | 2.3.1 |
| librt | 0.16.0 |
| mypy | 2.4.1 |
| mypy-extensions | 1.2.0 |
| nexus-ai-backend | 0.1.0 |
| opentelemetry-api | 1.45.2 |
| packaging | 26.3 |
| pathspec | 1.1.1 |
| pluggy | 1.7.0 |
| pydantic | 2.14.3 |
| pydantic-core | 2.50.4 |
| pygments | 2.21.0 |
| pytest | 9.2.0 |
| ruff | 0.17.4 |
| starlette | 1.10.0 |
| typing-extensions | 4.16.0 |
| typing-inspection | 0.4.5 |
| uvicorn | 0.54.0 |

| Frontend direct dependency | Installed/locked version |
| --- | --- |
| next | 16.4.5 |
| react | 19.3.1 |
| react-dom | 19.3.1 |
| @types/node | 22.20.1 |
| @types/react | 19.3.0 |
| @types/react-dom | 19.3.0 |
| eslint | 9.39.5 |
| eslint-config-next | 16.4.5 |
| typescript | 5.9.3 |
| vitest | 5.1.0 |
| tailwindcss | 4.3.5 |
| @tailwindcss/postcss | 4.3.5 |
| postcss | 8.5.23 |

The full frontend transitive resolution is in [pnpm-lock.yaml](../frontend/pnpm-lock.yaml); the backend resolution is in [uv.lock](../backend/uv.lock). Direct pins stayed unchanged from the approved manifests.

Lockfile SHA-256 values at final parent verification:

```text
backend/uv.lock: a9e27fddc84fe500e889dbd894cf730231c2ca8a0dd08869911e68747f00407f
frontend/pnpm-lock.yaml: d4dcae06538a753e37d89449e42679b773aca8cc8dbe4f1f2d3280bbbde94d2c
```

## Git, exclusions and preservation

`git rev-parse --show-toplevel` confirms the intended root; `git rev-parse --is-inside-work-tree` returns true. `git status --short --untracked-files=all` shows project source/config/docs and the new application locks as untracked. `git ls-files` is empty: nothing is tracked or staged and no commit exists.

Actual `git check-ignore --quiet --no-index` assertions verify 11 representative secret/local/generated paths excluded: `.env`, `.env.local`, `backend/.env`, `backend/.venv/bin/python`, `frontend/node_modules/.bin/next`, `frontend/.next/server/app/index.html`, `frontend/tsconfig.tsbuildinfo`, `backend/.pytest_cache/README.md`, `credentials/example.json`, `secrets/example.txt`, and `frontend/next-env.d.ts`. Five required example/source/lock paths remain visible: `.env.example`, both application lockfiles, backend application source and frontend page source. The tested secret paths are representative path names; no real private environment or credential content was read. No comprehensive secret scanner audit is claimed.

A pre-install snapshot covers 64 non-secret, non-generated project files. All remain present. Both manifests, backend application/tests, frontend page/layout and all 22 protected configuration/support/agent/skill files retain their original pre-install hashes. Changes are explained below. Earlier pre-scaffold preservation checks also found no original files missing.

## Changes in this approved completion pass

```text
nexus-ai/
├── .git/                         A local metadata; no commit
├── .gitignore                    M ignore generated Next declarations
├── Makefile                      M explicit build flags; generate types before tsc
├── README.md                     M installed setup, results and fallback
├── backend/
│   ├── .venv/                    A ignored local environment
│   └── uv.lock                   A new reviewed application lock
├── frontend/
│   ├── node_modules/             A ignored local dependency tree
│   ├── .next/                    A ignored build/type output
│   ├── next-env.d.ts             G generated on disk, ignored; original references retained
│   ├── tsconfig.json             M additive generated-type include only
│   └── pnpm-lock.yaml            A new reviewed application lock
└── docs/
    ├── M1_1_VERIFICATION.md       M actual execution and resolved versions
    └── ROADMAP.md                M current M1.1 evidence/status
```

The prior M1.1 scaffold changes remain: backend health/testing metadata, frontend Tailwind/PostCSS/global stylesheet and Node pin, placeholder-only environment example, ignore rules and developer setup. No existing source file was discarded. No OpenCode model/provider, permission, agent or skill file was changed. Both ADRs remain **Proposed**.

## Warnings and verification limits

- Starlette emits a deprecation warning for HTTPX TestClient and suggests HTTPX2. All tests pass; adding a new direct package was outside the approved constraints and was not done.
- pnpm reports pinned ESLint 9.39.5 unsupported. The declared version was retained; changing the pin requires a separately justified change. No dependency vulnerability audit or CVE claim is made.
- Default Turbopack is blocked by worker-port permissions; the explicit Webpack production build passes.
- A fresh second-machine installation and cross-platform behavior were not tested. Locked repeat-install commands in README are guidance, not an invented clean-install result.
- Git contains no staged/tracked files or commits. This review validates exclusions and an empty index, not a published or committed repository.

## M1.1 exit criteria

| Roadmap criterion / required gate | PASS / FAIL / BLOCKED | Evidence |
| --- | --- | --- |
| Layout and developer commands documented | PASS | Monorepo preserved; README and Makefile document setup, verification and explicit build fallback. |
| No real credentials or personal data tracked | PASS | Empty Git index; example placeholders and representative secret exclusions checked. No real secret file read. |
| Test and lint entry points run with recorded successful output | PASS | Final `make verify NEXT_BUILD_FLAGS=--webpack` exit 0, including both linters and test runners. |
| Python project import/package and strict typecheck | PASS | Editable import without PYTHONPATH, direct version assertions, compatible installed packages and strict mypy. |
| Frontend typecheck and production build | PASS via documented fallback | Type generation/TypeScript and Webpack production build pass; default Turbopack remains BLOCKED by environment. |
| Dependency locks and installed version agreement | PASS | New reviewed locks, backend offline lock check, direct pins verified. |
| Git initialization/exclusion checks | PASS | Correct worktree root, empty index, source/lock visibility and generated/secret exclusions. |
| Preserve source, OpenCode configuration and milestone boundary | PASS | Snapshot checks; manifests/scaffold unchanged; Proposed ADRs; no M1.2 integration or service startup. |
| Independent final reviewer | PASS | Approve with comments; one material safeguard finding corrected and rechecked. |

No FAIL is recorded; the default Turbopack path is an explicit environment BLOCKED item with a passing supported fallback. Overall **M1.1 PASS with documented fallback and warnings**, following independent approval with comments. Stop after M1.1; do not begin M1.2.

## Independent final review

The independent read-only reviewer found that Next can auto-install missing TypeScript packages despite executable guards. Both Next typegen/build invocations now set `CI=1`, which the installed Next dependency-check code uses to fail instead of install. Relevant frontend typecheck/build checks were rerun and passed; the reviewer rechecked the fix. No missing package was installed implicitly.

The reviewer independently confirmed preservation of 64 files and 22 protected hashes, six backend and 13 frontend direct pins against installed versions and locks, lock integrity records, Git exclusions, empty index and Proposed ADRs. It reviewed the executed test/build evidence without repeating the broad suite. Verdict: **approve with comments; M1.1 PASS with explicit Webpack fallback and documented warnings**. No unresolved material finding.

Final parent checks confirm both reviewed lock hashes remain unchanged after all verification and no HEAD commit exists. No Docker, PostgreSQL, Ollama, domain entities, database migrations or runtime integration was started or introduced. Stop after M1.1.
