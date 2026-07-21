# Repository Foundation Design

Date: 2026-07-21
Status: Approved

## Purpose

Establish the Prompt 1 foundation for `agentic-chargeback-investigator`: a
runnable Python 3.13 `uv` workspace with initial modules, shared engineering
conventions, exact dependency pinning where required, minimal smoke tests, and
developer commands. No business logic, agents, MCP tools, RAG, AG-UI, or A2UI
behavior is implemented in this pass.

Source of truth for scope, structure, and acceptance criteria is the Prompt 1
instructions provided by the user; this document records the execution
decisions made to resolve the few ambiguous points, not a restatement of that
spec.

## Decisions

### Version pinning

Pinned versions (`fastapi==0.139.2`, `a2a-sdk==1.1.1`, `fastmcp==3.4.4`,
`chromadb==1.5.9`, `ag-ui-protocol==0.1.19`, `react==19.2.7`,
`vite==8.1.5`, `tailwindcss==4.3.2`, `@ag-ui/client==0.0.57`) will be
installed for real via `uv add` / `npm install`. If any version fails to
resolve against the live registry, stop and ask the user for the correct
version rather than substituting or guessing.

### Workspace layout

Root `pyproject.toml` declares the `uv` workspace members and holds all
shared dev dependencies (`pytest`, `pytest-asyncio`, `ruff`, `mypy`) and
shared tool configuration (`[tool.ruff]`, `[tool.mypy]`,
`[tool.pytest.ini_options]`). Child packages declare only their own name,
`src` layout, and package-specific runtime dependencies — no repeated tool
config.

Nine Python packages (`orchestrator-agent`, `transaction-agent`,
`customer-history-agent`, `merchant-evidence-agent`, `policy-agent`,
`duplicate-transaction-agent`, `agent-registry`, `dispute-mcp-server`,
`contracts`, `knowledge-ingestor`) each get an empty `src/<package>/__init__.py`
and a single `tests/test_import.py` smoke test that imports the package.

### Existing docs/README

`docs/use-case-tech-summary.md` already exists and is complete from a prior
session — left untouched. `README.md` currently contains only a title; it
will be expanded in place to cover purpose, tech stack, repository structure,
module responsibility table, prerequisites, setup steps, developer commands,
the Ollama host-runtime note, a link to the tech summary doc, and a statement
that implementation proceeds through staged prompts.

### docker-compose.yml

Attempt a real check of whether the pinned ChromaDB version supports a clean
single-container startup. If yes, ship it as the only service, commented to
note that full orchestration lands in Prompt 12. If not straightforward, ship
a comments-only scaffold instead. The outcome will be reported as a
deviation/note either way.

### investigator-ui

Vite + React + TypeScript template, Tailwind wired via PostCSS,
`@ag-ui/client` installed but unused beyond the app shell. npm is used
(matches the spec's `package-lock.json`). The frontend smoke test is a
successful `vite build`.

### Commit workflow

Per explicit user instruction, this batch of work is committed file-by-file
(or logical-unit-by-unit), with no `docs/COMMIT_LOG.md` update per commit.
A single final commit adds all `docs/COMMIT_LOG.md` entries covering the
whole batch. This supersedes the git-commit skill's normal
"update the changelog every commit" step for this batch only.

## Out of scope (explicit non-goals for this pass)

Agents, Agent Registry behavior, MCP tools, RAG ingestion, AG-UI streaming,
A2UI screens, deterministic recommendation rules, Ollama-in-Docker, cloud
dependencies/API keys, repository/module renames, use of the term
"Commander".

## Acceptance criteria

See the user-provided Prompt 1 instructions in full; summarized: valid `uv`
workspace, every package installs and imports, frontend installs and builds,
exact versions pinned where introduced, Ollama documented as host-native,
`make lint` / `make typecheck` / `make test` / `make ui-build` / `make verify`
all pass, no business functionality implemented.
