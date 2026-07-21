# Commit Log

## 2026-07-21 — Write full foundation README

**Files:** `README.md`
**What:** Replaced the one-line title with the full foundation README (purpose, tech overview, repository structure, module responsibility table, prerequisites, setup, developer commands, Ollama note, doc link, staged-development statement).
**Why:** Give the repository a real entry point matching the Prompt 1 specification's README requirements.

## 2026-07-21 — Add root Makefile

**Files:** `Makefile`
**What:** Added the root Makefile with `install`, `lock`, `format`, `lint`, `typecheck`, `test`, `verify`, `ui-install`, `ui-build`, and `clean` targets.
**Why:** Provide the developer commands the Prompt 1 specification requires, all runnable from the repo root.

## 2026-07-21 — Fix investigator-ui build and correct changelog process

**Files:** `investigator-ui/postcss.config.js`, `investigator-ui/package.json`, `investigator-ui/package-lock.json`, `.gitignore`, `docs/COMMIT_LOG.md`
**What:** Fixed the first real `npm run build` failure (Tailwind v4 moved its PostCSS integration to `@tailwindcss/postcss`; the app shell still referenced the old v3 plugin name), added `.gitignore` entries for Node build byproducts (`node_modules/`, `*.tsbuildinfo`, generated `vite.config.js`/`.d.ts`), and reverted two premature `docs/COMMIT_LOG.md` entries the implementer had mistakenly added per-commit.
**Why:** `investigator-ui` needs to actually build (Prompt 1 acceptance criterion); the changelog for this batch is written once, consolidated, here — not per commit — so the premature entries were corrected before this final entry.

## 2026-07-21 — Add investigator-ui Vite/TS/Tailwind app shell

**Files:** `investigator-ui/index.html`, `investigator-ui/vite.config.ts`, `investigator-ui/tsconfig.json`, `investigator-ui/tsconfig.node.json`, `investigator-ui/postcss.config.js`, `investigator-ui/tailwind.config.js`, `investigator-ui/src/index.css`, `investigator-ui/src/App.tsx`, `investigator-ui/src/main.tsx`
**What:** Added the Vite + React + TypeScript + Tailwind app shell: an HTML entrypoint, Vite/TS/PostCSS/Tailwind config, and a placeholder `App` component titled "Agentic Chargeback Investigator" noting the investigation UI comes later.
**Why:** Prompt 1 requires a minimal, buildable frontend shell — no AG-UI/A2UI behavior yet.

## 2026-07-21 — Add investigator-ui package manifest and lockfile

**Files:** `investigator-ui/package.json`, `investigator-ui/package-lock.json`
**What:** Added the frontend package manifest with exact pins (`react@19.2.7`, `react-dom@19.2.7`, `vite@8.1.5`, `tailwindcss@4.3.2`, `@ag-ui/client@0.0.57`) and installed dependencies.
**Why:** Establish the frontend toolchain with the exact versions the Prompt 1 specification requires.

## 2026-07-21 — Add docker-compose scaffold

**Files:** `docker-compose.yml`
**What:** Added a comments-only docker-compose scaffold explaining that full service orchestration lands in a later prompt, and that Ollama is intentionally not defined (it runs natively on the Docker host).
**Why:** Document orchestration intent without fabricating an unverifiable live service definition — this sandbox has no reachable Docker daemon to confirm a clean single-container ChromaDB startup.

## 2026-07-21 — Lock workspace and fix pytest/mypy test-module collision

**Files:** `pyproject.toml`, `uv.lock`
**What:** Ran `uv lock`/`uv sync` for the first time and fixed a real pytest/mypy "duplicate module" collision caused by all 10 packages sharing the `tests/test_import.py` basename with no `__init__.py`, via `--import-mode=importlib` (pytest) and a `tests/` exclude (mypy) — no package files touched, `strict = true` left intact.
**Why:** Verify the workspace actually installs and every package imports, per the Prompt 1 acceptance criteria.

## 2026-07-21 — Add knowledge-ingestor package

**Files:** `knowledge-ingestor/pyproject.toml`, `knowledge-ingestor/src/knowledge_ingestor/__init__.py`, `knowledge-ingestor/tests/test_import.py`
**What:** Added the `knowledge-ingestor` workspace member (manifest, empty package, import smoke test).
**Why:** Scaffold the package that will later seed policy knowledge into ChromaDB.

## 2026-07-21 — Add contracts package

**Files:** `contracts/pyproject.toml`, `contracts/src/chargeback_contracts/__init__.py`, `contracts/tests/test_import.py`
**What:** Added the `contracts` workspace member (distribution name `contracts`, import name `chargeback_contracts`).
**Why:** Scaffold the package that will later hold shared Pydantic models and capability constants.

## 2026-07-21 — Add dispute-mcp-server package

**Files:** `dispute-mcp-server/pyproject.toml`, `dispute-mcp-server/src/dispute_mcp_server/__init__.py`, `dispute-mcp-server/tests/test_import.py`
**What:** Added the `dispute-mcp-server` workspace member (manifest, empty package, import smoke test).
**Why:** Scaffold the package that will later expose mock enterprise data through MCP.

## 2026-07-21 — Add agent-registry package

**Files:** `agent-registry/pyproject.toml`, `agent-registry/src/agent_registry/__init__.py`, `agent-registry/tests/test_import.py`
**What:** Added the `agent-registry` workspace member (manifest, empty package, import smoke test).
**Why:** Scaffold the package that will later provide lease-based agent and capability discovery.

## 2026-07-21 — Add duplicate-transaction-agent package

**Files:** `duplicate-transaction-agent/pyproject.toml`, `duplicate-transaction-agent/src/duplicate_transaction_agent/__init__.py`, `duplicate-transaction-agent/tests/test_import.py`
**What:** Added the `duplicate-transaction-agent` workspace member (manifest, empty package, import smoke test).
**Why:** Scaffold the package that will later demonstrate dynamic capability registration.

## 2026-07-21 — Add policy-agent package

**Files:** `policy-agent/pyproject.toml`, `policy-agent/src/policy_agent/__init__.py`, `policy-agent/tests/test_import.py`
**What:** Added the `policy-agent` workspace member (manifest, empty package, import smoke test).
**Why:** Scaffold the package that will later interpret policy using RAG.

## 2026-07-21 — Add merchant-evidence-agent package

**Files:** `merchant-evidence-agent/pyproject.toml`, `merchant-evidence-agent/src/merchant_evidence_agent/__init__.py`, `merchant-evidence-agent/tests/test_import.py`
**What:** Added the `merchant-evidence-agent` workspace member (manifest, empty package, import smoke test).
**Why:** Scaffold the package that will later investigate merchant evidence.

## 2026-07-21 — Add customer-history-agent package

**Files:** `customer-history-agent/pyproject.toml`, `customer-history-agent/src/customer_history_agent/__init__.py`, `customer-history-agent/tests/test_import.py`
**What:** Added the `customer-history-agent` workspace member (manifest, empty package, import smoke test).
**Why:** Scaffold the package that will later investigate customer history.

## 2026-07-21 — Add transaction-agent package

**Files:** `transaction-agent/pyproject.toml`, `transaction-agent/src/transaction_agent/__init__.py`, `transaction-agent/tests/test_import.py`
**What:** Added the `transaction-agent` workspace member (manifest, empty package, import smoke test).
**Why:** Scaffold the package that will later handle transaction-domain investigation.

## 2026-07-21 — Add orchestrator-agent package

**Files:** `orchestrator-agent/pyproject.toml`, `orchestrator-agent/src/orchestrator_agent/__init__.py`, `orchestrator-agent/tests/test_import.py`
**What:** Added the `orchestrator-agent` workspace member (manifest, empty package, import smoke test).
**Why:** Scaffold the package that will later coordinate investigations and deterministic aggregation.

## 2026-07-21 — Add root uv workspace configuration

**Files:** `pyproject.toml`, `.python-version`, `.env.example`
**What:** Added the root `uv` workspace manifest (10-member workspace, shared dev dependencies, Ruff/Mypy/Pytest config), pinned Python to 3.13, and documented environment variable placeholders (Ollama, ChromaDB, registry/MCP URLs, log level).
**Why:** Establish the Prompt 1 foundation's workspace root before any member package exists, per the accompanying design spec.

## 2026-07-21 — Add git-commit skill

**Files:** `.claude/skills/git-commit/SKILL.md`
**What:** Added the git-commit skill, tailored for this Python repo (Python-specific never-stage list, repo name, commit workflow).
**Why:** Give Claude Code a repo-specific, repeatable procedure for committing changes and logging them in docs/COMMIT_LOG.md.

## 2026-07-21 — Add use-case tech summary

**Files:** `docs/use-case-tech-summary.md`
**What:** Added the canonical design reference covering project overview, tech stack, architecture components, specialist agents, responsibility matrix, investigation flow, decision rules, demo scenarios, repository structure, and key architectural principles.
**Why:** Provide a single source of truth for the agentic chargeback investigator design (A2A, MCP, RAG, AG-UI, A2UI) before implementation begins.

## 2026-07-21 — Add project README

**Files:** `README.md`
**What:** Added a README with the project title.
**Why:** Establish a starting point for project documentation.

## 2026-07-21 — Ignore macOS .DS_Store files

**Files:** `.gitignore`
**What:** Added `.DS_Store` to the ignore list.
**Why:** Prevent macOS Finder metadata files from being tracked.
