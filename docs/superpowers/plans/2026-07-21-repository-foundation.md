# Repository Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up a runnable Python 3.13 `uv` workspace foundation for `agentic-chargeback-investigator` — 10 Python packages, a React/Vite frontend shell, shared tooling config, developer commands, and minimal smoke tests. No business logic, agents, MCP tools, RAG, AG-UI, or A2UI behavior.

**Architecture:** A `uv` workspace rooted at the repo root, with 10 independent `src`-layout Python packages as workspace members sharing one dev-dependency group and one Ruff/Mypy/Pytest config. A separate `investigator-ui` Vite+React+TS app lives alongside, wired to Tailwind and `@ag-ui/client` but with no AG-UI/A2UI logic yet. A root `Makefile` wraps both toolchains.

**Tech Stack:** Python 3.13, `uv` 0.8.22, pytest, pytest-asyncio, ruff, mypy, hatchling (build backend for packages), Node/npm, React 19.2.7, Vite 8.1.5, TypeScript, Tailwind CSS 4.3.2, `@ag-ui/client` 0.0.57.

## Global Constraints

- Python 3.13 required repo-wide; `uv` workspace; `src` layout for every Python package.
- Exact pins where introduced in this prompt: `react==19.2.7`, `react-dom==19.2.7`, `vite==8.1.5`, `tailwindcss==4.3.2`, `@ag-ui/client==0.0.57` (all verified resolvable against the live npm registry).
- Backend pins (`fastapi==0.139.2`, `a2a-sdk==1.1.1`, `fastmcp==3.4.4`, `chromadb==1.5.9`, `ag-ui-protocol==0.1.19`) are **not** installed in this prompt — no Python package has business logic yet that needs them, so per the spec they are deferred to the prompt that introduces them.
- If any version pin fails to resolve when actually installed, STOP and ask the user for the correct version — do not substitute or guess (per user decision 2026-07-21).
- Directory names stay kebab-case; Python package (import) names are snake_case per the mapping table in Task 2.
- No business logic, agents, Agent Registry behavior, MCP tools, RAG ingestion, AG-UI streaming, A2UI screens, or deterministic recommendation rules in this prompt.
- Ollama is host-native, never a Docker service.
- No secrets/API keys/cloud dependencies.
- Never use the term "Commander"; use "Orchestrator".
- Docker research finding: this sandbox has the `docker` CLI but no reachable daemon, and Docker Hub's tag API was unreachable from here — there is no way to empirically verify a clean single-container ChromaDB startup. Per the spec's fallback, `docker-compose.yml` ships as a documented, comments-only scaffold (Task 13), not a live service definition.
- Commit workflow for this batch (explicit user instruction, supersedes the git-commit skill's per-commit changelog step): every created/modified file gets its own `git add <file> && git commit`, with **no** `docs/COMMIT_LOG.md` touch until the final task, which adds every entry in one consolidated commit.

---

### Task 1: Root workspace configuration files

**Files:**
- Create: `.python-version`
- Create: `pyproject.toml` (repo root)
- Create: `.env.example`

**Interfaces:**
- Produces: workspace member list that Task 2's packages must match exactly (directory names); `[dependency-groups] dev` that provides `pytest`, `pytest-asyncio`, `ruff`, `mypy` to every later task's verification steps.

- [ ] **Step 1: Create `.python-version`**

```text
3.13
```

- [ ] **Step 2: Commit**

```bash
git add .python-version
git commit -m "chore: pin Python version to 3.13"
```

- [ ] **Step 3: Create root `pyproject.toml`**

```toml
[project]
name = "agentic-chargeback-investigator"
version = "0.1.0"
description = "AI-assisted credit card chargeback investigation platform (workspace root)"
requires-python = ">=3.13"
dependencies = []

[tool.uv]
package = false

[tool.uv.workspace]
members = [
    "orchestrator-agent",
    "transaction-agent",
    "customer-history-agent",
    "merchant-evidence-agent",
    "policy-agent",
    "duplicate-transaction-agent",
    "agent-registry",
    "dispute-mcp-server",
    "contracts",
    "knowledge-ingestor",
]

[dependency-groups]
dev = [
    "pytest>=8.3",
    "pytest-asyncio>=0.24",
    "ruff>=0.8",
    "mypy>=1.13",
]

[tool.ruff]
target-version = "py313"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "W", "I", "B", "UP"]

[tool.mypy]
python_version = "3.13"
strict = true
warn_unused_ignores = true
namespace_packages = true
explicit_package_bases = true
mypy_path = [
    "orchestrator-agent/src",
    "transaction-agent/src",
    "customer-history-agent/src",
    "merchant-evidence-agent/src",
    "policy-agent/src",
    "duplicate-transaction-agent/src",
    "agent-registry/src",
    "dispute-mcp-server/src",
    "contracts/src",
    "knowledge-ingestor/src",
]

[tool.pytest.ini_options]
testpaths = [
    "orchestrator-agent/tests",
    "transaction-agent/tests",
    "customer-history-agent/tests",
    "merchant-evidence-agent/tests",
    "policy-agent/tests",
    "duplicate-transaction-agent/tests",
    "agent-registry/tests",
    "dispute-mcp-server/tests",
    "contracts/tests",
    "knowledge-ingestor/tests",
]
asyncio_mode = "auto"
```

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "chore: add root uv workspace configuration"
```

- [ ] **Step 5: Create `.env.example`**

```text
# Ollama runs on the Docker host, not as a container.
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_TEXT_MODEL=qwen3.5:9b
OLLAMA_EMBEDDING_MODEL=nomic-embed-text

# ChromaDB
CHROMA_HOST=localhost
CHROMA_PORT=8000

# Filled in once agent-registry / dispute-mcp-server exist and are addressable
AGENT_REGISTRY_URL=
DISPUTE_MCP_URL=

# Logging
LOG_LEVEL=INFO
```

- [ ] **Step 6: Commit**

```bash
git add .env.example
git commit -m "chore: add documented environment variable placeholders"
```

**Note:** Do not run `uv sync` yet — the workspace members declared above don't exist as directories until Task 2 finishes. Running it now will fail with a "member not found" error; that failure is expected and not a bug.

---

### Task 2: Create all 10 Python workspace member packages

**Files:**
- Create (×10, one set per package): `<dir>/pyproject.toml`, `<dir>/src/<import_name>/__init__.py`, `<dir>/tests/test_import.py`

**Interfaces:**
- Consumes: workspace member list from Task 1.
- Produces: 10 importable packages verified collectively in Task 3. No package imports another in this prompt.

Package mapping (directory | distribution name | import name | description):

| Directory | Import name | Description |
|---|---|---|
| `orchestrator-agent` | `orchestrator_agent` | Coordinates investigations and deterministic aggregation |
| `transaction-agent` | `transaction_agent` | Transaction-domain investigation |
| `customer-history-agent` | `customer_history_agent` | Customer history investigation |
| `merchant-evidence-agent` | `merchant_evidence_agent` | Merchant evidence investigation |
| `policy-agent` | `policy_agent` | Policy interpretation using RAG |
| `duplicate-transaction-agent` | `duplicate_transaction_agent` | Dynamically registered duplicate transaction capability |
| `agent-registry` | `agent_registry` | Lease-based agent and capability discovery |
| `dispute-mcp-server` | `dispute_mcp_server` | Mock enterprise data exposed through MCP |
| `contracts` | `chargeback_contracts` | Shared Pydantic models and capability constants |
| `knowledge-ingestor` | `knowledge_ingestor` | Seeds policy knowledge into ChromaDB |

Every package's `pyproject.toml` follows this exact template (substitute `<dir>`, `<import_name>`, `<description>`):

```toml
[project]
name = "<dir>"
version = "0.1.0"
description = "<description>"
requires-python = ">=3.13"
dependencies = []

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/<import_name>"]
```

Every package's `src/<import_name>/__init__.py` follows this exact template:

```python
"""<description>."""

__version__ = "0.1.0"
```

Every package's `tests/test_import.py` follows this exact template:

```python
import <import_name>


def test_module_imports() -> None:
    assert <import_name> is not None
```

- [ ] **Step 1: Create `orchestrator-agent/pyproject.toml`**

```toml
[project]
name = "orchestrator-agent"
version = "0.1.0"
description = "Coordinates investigations and deterministic aggregation"
requires-python = ">=3.13"
dependencies = []

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/orchestrator_agent"]
```

- [ ] **Step 2: Commit**

```bash
git add orchestrator-agent/pyproject.toml
git commit -m "chore: add orchestrator-agent package manifest"
```

- [ ] **Step 3: Create `orchestrator-agent/src/orchestrator_agent/__init__.py`**

```python
"""Coordinates investigations and deterministic aggregation."""

__version__ = "0.1.0"
```

- [ ] **Step 4: Commit**

```bash
git add orchestrator-agent/src/orchestrator_agent/__init__.py
git commit -m "chore: add orchestrator-agent package skeleton"
```

- [ ] **Step 5: Create `orchestrator-agent/tests/test_import.py`**

```python
import orchestrator_agent


def test_module_imports() -> None:
    assert orchestrator_agent is not None
```

- [ ] **Step 6: Commit**

```bash
git add orchestrator-agent/tests/test_import.py
git commit -m "test: add orchestrator-agent import smoke test"
```

- [ ] **Step 7: Repeat Steps 1–6 for the remaining 9 packages**, substituting each row of the mapping table above into the three file templates verbatim. For each package: write `pyproject.toml` (commit), write `src/<import_name>/__init__.py` (commit), write `tests/test_import.py` (commit). Concretely, for `contracts`, the distribution name is `contracts` but the import name is `chargeback_contracts` (per the mapping table) — every other package uses its directory name with hyphens replaced by underscores as the import name.

  Do not run tests yet — the workspace isn't synced until Task 3.

---

### Task 3: Sync the workspace and verify every package imports

**Files:**
- Modify: `uv.lock` (created by `uv lock`)

**Interfaces:**
- Consumes: root `pyproject.toml` (Task 1), all 10 member packages (Task 2).
- Produces: a working `uv sync` environment that Tasks 15–17's `make` targets rely on.

- [ ] **Step 1: Lock the workspace**

Run: `uv lock`
Expected: completes without error, creates/updates `uv.lock` at repo root. If it errors on a missing member, re-check Task 2 directory names against the `members` list in Task 1 exactly.

- [ ] **Step 2: Sync the workspace**

Run: `uv sync --all-packages`
Expected: installs all 10 workspace member packages plus the `dev` dependency group (pytest, pytest-asyncio, ruff, mypy) into `.venv`.

- [ ] **Step 3: Run the full test suite**

Run: `uv run pytest`
Expected: 10 tests pass (one `test_module_imports` per package), 0 failed.

- [ ] **Step 4: Run Ruff**

Run: `uv run ruff check .`
Expected: no findings. If it flags anything in the generated files above, fix the specific file and re-run.

- [ ] **Step 5: Run Mypy**

Run: `uv run mypy .`
Expected: no errors ("Success: no issues found"). If `strict = true` produces noise on the empty `__init__.py` files, note the exact error before changing config — do not weaken `strict` without first confirming the error is unavoidable.

- [ ] **Step 6: Commit the lock file**

```bash
git add uv.lock
git commit -m "chore: lock workspace dependencies"
```

---

### Task 4: docker-compose.yml scaffold

**Files:**
- Create: `docker-compose.yml`

**Interfaces:**
- Produces: none consumed elsewhere in this prompt; documents intent for Prompt 12.

Per the Global Constraints research note, this ships as a comments-only scaffold — no live services, since there's no way to verify a clean ChromaDB single-container startup from this environment.

- [ ] **Step 1: Create `docker-compose.yml`**

```yaml
# Foundation-stage scaffold only.
#
# Full service orchestration (agents, agent-registry, dispute-mcp-server,
# ChromaDB, investigator-ui) is completed in Prompt 12.
#
# Ollama is intentionally NOT defined here: it runs natively on the Docker
# host, not as a container. Services that need it reach it via
# OLLAMA_BASE_URL (see .env.example), typically
# http://host.docker.internal:11434.
#
# No services are defined yet — adding them prematurely would misrepresent
# functionality that doesn't exist in this prompt.

services: {}
```

- [ ] **Step 2: Commit**

```bash
git add docker-compose.yml
git commit -m "docs: add docker-compose scaffold for future service orchestration"
```

---

### Task 5: investigator-ui — package.json and lockfile

**Files:**
- Create: `investigator-ui/package.json`
- Create: `investigator-ui/package-lock.json` (generated by `npm install`)

**Interfaces:**
- Produces: `node_modules` and lockfile that Task 6's scaffold files and Task 7's build depend on.

- [ ] **Step 1: Create `investigator-ui/package.json`**

```json
{
  "name": "investigator-ui",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "19.2.7",
    "react-dom": "19.2.7",
    "@ag-ui/client": "0.0.57"
  },
  "devDependencies": {
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "@vitejs/plugin-react": "^4.3.4",
    "autoprefixer": "^10.4.20",
    "postcss": "^8.4.49",
    "tailwindcss": "4.3.2",
    "typescript": "^5.7.2",
    "vite": "8.1.5"
  }
}
```

- [ ] **Step 2: Install dependencies**

Run: `cd investigator-ui && npm install`
Expected: resolves and installs successfully, generating `package-lock.json`. If `react@19.2.7`, `react-dom@19.2.7`, `vite@8.1.5`, `tailwindcss@4.3.2`, or `@ag-ui/client@0.0.57` fail to resolve, STOP and ask the user — do not substitute a different version (these five were confirmed to exist on the npm registry during planning on 2026-07-21; a failure here means something changed and needs a human decision).

- [ ] **Step 3: Commit both files together**

`package.json` and its generated `package-lock.json` are one atomic unit (the lockfile is meaningless without the manifest it locks) — commit them together, then handle every subsequent file individually.

```bash
git add investigator-ui/package.json investigator-ui/package-lock.json
git commit -m "chore: add investigator-ui package manifest and lockfile"
```

---

### Task 6: investigator-ui — Vite/TS/Tailwind app shell

**Files:**
- Create: `investigator-ui/index.html`
- Create: `investigator-ui/vite.config.ts`
- Create: `investigator-ui/tsconfig.json`
- Create: `investigator-ui/tsconfig.node.json`
- Create: `investigator-ui/postcss.config.js`
- Create: `investigator-ui/tailwind.config.js`
- Create: `investigator-ui/src/index.css`
- Create: `investigator-ui/src/main.tsx`
- Create: `investigator-ui/src/App.tsx`

**Interfaces:**
- Consumes: `node_modules` from Task 5.
- Produces: a buildable app shell verified in Task 7.

- [ ] **Step 1: Create `investigator-ui/index.html`**

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Agentic Chargeback Investigator</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 2: Commit**

```bash
git add investigator-ui/index.html
git commit -m "chore: add investigator-ui HTML entrypoint"
```

- [ ] **Step 3: Create `investigator-ui/vite.config.ts`**

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
});
```

- [ ] **Step 4: Commit**

```bash
git add investigator-ui/vite.config.ts
git commit -m "chore: add investigator-ui Vite config"
```

- [ ] **Step 5: Create `investigator-ui/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "useDefineForClassFields": true,
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

- [ ] **Step 6: Commit**

```bash
git add investigator-ui/tsconfig.json
git commit -m "chore: add investigator-ui TypeScript config"
```

- [ ] **Step 7: Create `investigator-ui/tsconfig.node.json`**

```json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true,
    "strict": true
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 8: Commit**

```bash
git add investigator-ui/tsconfig.node.json
git commit -m "chore: add investigator-ui Node TypeScript config"
```

- [ ] **Step 9: Create `investigator-ui/postcss.config.js`**

```javascript
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
```

- [ ] **Step 10: Commit**

```bash
git add investigator-ui/postcss.config.js
git commit -m "chore: add investigator-ui PostCSS config"
```

- [ ] **Step 11: Create `investigator-ui/tailwind.config.js`**

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {},
  },
  plugins: [],
};
```

- [ ] **Step 12: Commit**

```bash
git add investigator-ui/tailwind.config.js
git commit -m "chore: add investigator-ui Tailwind config"
```

- [ ] **Step 13: Create `investigator-ui/src/index.css`**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

- [ ] **Step 14: Commit**

```bash
git add investigator-ui/src/index.css
git commit -m "chore: add investigator-ui Tailwind entry stylesheet"
```

- [ ] **Step 15: Create `investigator-ui/src/App.tsx`**

```tsx
function App() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-100">
      <div className="text-center">
        <h1 className="text-3xl font-semibold">Agentic Chargeback Investigator</h1>
        <p className="mt-2 text-slate-400">
          The investigation UI will be implemented in a later development prompt.
        </p>
      </div>
    </div>
  );
}

export default App;
```

- [ ] **Step 16: Commit**

```bash
git add investigator-ui/src/App.tsx
git commit -m "chore: add investigator-ui App shell placeholder"
```

- [ ] **Step 17: Create `investigator-ui/src/main.tsx`**

```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
```

- [ ] **Step 18: Commit**

```bash
git add investigator-ui/src/main.tsx
git commit -m "chore: add investigator-ui entrypoint"
```

---

### Task 7: investigator-ui — verify the build

**Files:** none created; verification only.

**Interfaces:**
- Consumes: everything from Tasks 5–6.
- Produces: a passing `npm run build`, the frontend's smoke test per the spec.

- [ ] **Step 1: Build the frontend**

Run: `cd investigator-ui && npm run build`
Expected: TypeScript project build (`tsc -b`) and Vite build both succeed, producing `investigator-ui/dist/`. Fix any TS error in the specific file it points to before proceeding — do not loosen `strict` in `tsconfig.json` to silence it.

- [ ] **Step 2: Confirm `dist/` was produced**

Run: `ls investigator-ui/dist`
Expected: contains `index.html` and an `assets/` directory.

No commit in this task — it verifies files already committed in Tasks 5–6. `dist/` and `node_modules/` must already be covered by `.gitignore`; if they aren't, add them as part of Task 8.

---

### Task 8: Makefile

**Files:**
- Create: `Makefile`

**Interfaces:**
- Consumes: `uv` workspace (Tasks 1–3), `investigator-ui` (Tasks 5–7).
- Produces: the `make verify` entrypoint that Task 9 runs end-to-end.

- [ ] **Step 1: Create `Makefile`**

```makefile
.PHONY: install lock format lint typecheck test verify ui-install ui-build clean

install:
	uv sync --all-packages

lock:
	uv lock

format:
	uv run ruff format .

lint:
	uv run ruff check .

typecheck:
	uv run mypy .

test:
	uv run pytest

ui-install:
	cd investigator-ui && npm install

ui-build:
	cd investigator-ui && npm run build

verify:
	uv run ruff format --check .
	uv run ruff check .
	uv run mypy .
	uv run pytest
	$(MAKE) ui-install
	$(MAKE) ui-build

clean:
	find . -type d -name '__pycache__' -exec rm -rf {} +
	find . -type d -name '.pytest_cache' -exec rm -rf {} +
	find . -type d -name '.mypy_cache' -exec rm -rf {} +
	find . -type d -name '.ruff_cache' -exec rm -rf {} +
	rm -rf investigator-ui/dist investigator-ui/node_modules
```

- [ ] **Step 2: Commit**

```bash
git add Makefile
git commit -m "chore: add root Makefile with developer commands"
```

---

### Task 9: Verify `.gitignore` covers generated output

**Files:**
- Modify: `.gitignore` (only if a gap is found)

**Interfaces:** none.

The existing `.gitignore` already covers Python artifacts (`__pycache__/`, `.venv/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, etc.) and `.env`. It does not yet cover Node/frontend output.

- [ ] **Step 1: Check current coverage**

Run: `grep -E "node_modules|dist" .gitignore`
Expected: no output (not yet covered).

- [ ] **Step 2: Append Node/frontend entries**

Add to the end of `.gitignore`:

```text

# Node / frontend
node_modules/
investigator-ui/dist/
```

- [ ] **Step 3: Commit**

```bash
git add .gitignore
git commit -m "chore: ignore frontend build output and node_modules"
```

---

### Task 10: Root README

**Files:**
- Modify: `README.md` (currently just a one-line title)

**Interfaces:**
- Consumes: module purposes from the spec's responsibility table, links to `docs/use-case-tech-summary.md`.

- [ ] **Step 1: Replace `README.md` contents**

```markdown
# Agentic Chargeback Investigator

An AI-assisted credit card chargeback investigation platform. A customer
submits a single chargeback dispute; an Orchestrator coordinates specialist
agents to investigate it, a Policy Agent interprets applicable policy via
RAG, and a human Investigator makes the final Accept / Reject / Request More
Evidence decision — the system recommends, it never decides. The project
exists to demonstrate A2A, MCP, RAG, AG-UI, A2UI, dynamic agent
registration, and mandatory human approval working together end to end.

## Technology overview

- Python 3.13, managed as a `uv` workspace
- FastAPI, `a2a-sdk`, FastMCP, ChromaDB (introduced as each backend service is implemented)
- React 19 + TypeScript + Vite + Tailwind CSS for the investigator UI
- AG-UI protocol for streaming, A2UI for the human-approval surface
- Ollama, running natively on the Docker host (not containerized)

See [`docs/use-case-tech-summary.md`](docs/use-case-tech-summary.md) for the
full canonical design reference.

## Repository structure

```text
agentic-chargeback-investigator
├── orchestrator-agent
├── transaction-agent
├── customer-history-agent
├── merchant-evidence-agent
├── policy-agent
├── duplicate-transaction-agent
├── agent-registry
├── dispute-mcp-server
├── contracts
├── knowledge-ingestor
├── investigator-ui
├── docs
├── docker-compose.yml
└── Makefile
```

## Module responsibilities

| Module | Purpose |
|---|---|
| `contracts` | Shared Pydantic models and capability constants |
| `orchestrator-agent` | Coordinates investigations and deterministic aggregation |
| `transaction-agent` | Transaction-domain investigation |
| `customer-history-agent` | Customer history investigation |
| `merchant-evidence-agent` | Merchant evidence investigation |
| `policy-agent` | Policy interpretation using RAG |
| `duplicate-transaction-agent` | Dynamically registered duplicate transaction capability |
| `agent-registry` | Lease-based agent and capability discovery |
| `dispute-mcp-server` | Mock enterprise data exposed through MCP |
| `knowledge-ingestor` | Seeds policy knowledge into ChromaDB |
| `investigator-ui` | React UI using AG-UI and A2UI |
| `docs` | Canonical design documentation |

## Prerequisites

- Python 3.13
- [`uv`](https://docs.astral.sh/uv/)
- Node.js 22 and npm
- [Ollama](https://ollama.com), running natively on the host (not in Docker) with the `qwen3.5:9b` and `nomic-embed-text` models pulled

## Initial setup

```bash
cp .env.example .env
make install
make ui-install
```

## Developer commands

| Command | Effect |
|---|---|
| `make install` | Install all Python workspace dependencies |
| `make lock` | Refresh `uv.lock` |
| `make format` | Format Python code with Ruff |
| `make lint` | Run Ruff checks |
| `make typecheck` | Run Mypy |
| `make test` | Run the Python test suite |
| `make verify` | Format check, lint, typecheck, tests, and frontend build |
| `make ui-install` | Install frontend dependencies |
| `make ui-build` | Build the frontend |
| `make clean` | Remove caches and build output |

## Ollama

Ollama runs natively on the Docker host — it is never run as a container.
Services that call it read `OLLAMA_BASE_URL` from the environment (see
`.env.example`), typically `http://host.docker.internal:11434` when other
services are containerized.

## Status

This repository is built through a series of staged development prompts.
This foundation stage establishes the workspace, module skeletons, and
tooling only — no agent, registry, MCP, RAG, AG-UI, or A2UI behavior is
implemented yet.
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: write full foundation README"
```

---

### Task 11: Full verification run

**Files:** none created; verification only.

**Interfaces:**
- Consumes: everything from Tasks 1–10.
- Produces: the evidence needed for the final report's acceptance-criteria checklist.

- [ ] **Step 1: Run `make verify` from the repo root**

Run: `make verify`
Expected: Ruff format-check passes, Ruff lint passes, Mypy passes, all 10 pytest smoke tests pass, `npm install` and `npm run build` both succeed in `investigator-ui`.

- [ ] **Step 2: If anything fails**

Fix the specific file the error points to (do not weaken Ruff/Mypy/TS strictness to silence it), re-run `make verify`, and repeat until clean. Record any fix as its own commit (e.g. `git commit -m "fix: correct mypy error in <file>"`).

- [ ] **Step 3: Confirm working tree is clean**

Run: `git status --short`
Expected: no output (everything from Tasks 1–10 already committed; any fix from Step 2 committed separately).

---

### Task 12: Consolidated changelog commit

**Files:**
- Modify: `docs/COMMIT_LOG.md`

**Interfaces:**
- Consumes: the full commit history produced by Tasks 1–11 (`git log --oneline` since the design-spec commit).

Per the user's explicit instruction for this batch: the changelog is written and committed **once**, covering every individual commit made in Tasks 1–11 — not per-commit as the git-commit skill normally does.

- [ ] **Step 1: List this batch's commits for reference**

Run: `git log --oneline 8a4ec89..HEAD`
(`8a4ec89` is the design-spec commit that precedes this batch.) Use the output to make sure every commit below is represented.

- [ ] **Step 2: Prepend entries to `docs/COMMIT_LOG.md`**

Add one entry per logical unit of work (root config, each of the 10 packages, workspace lock, docker-compose, frontend manifest, frontend app shell, Makefile, gitignore update, README), most recent first, above the existing `## 2026-07-21 — Add git-commit skill` entry. Use today's actual date and the real filenames touched, e.g.:

```markdown
## 2026-07-21 — Add Prompt 1 repository foundation

**Files:** `pyproject.toml`, `.python-version`, `.env.example`, `uv.lock`, `Makefile`, `docker-compose.yml`, `README.md`, `.gitignore`, all 10 package directories under workspace root, `investigator-ui/**`
**What:** Scaffolded the full Prompt 1 foundation: a 10-package `uv` Python workspace with shared Ruff/Mypy/Pytest config and one import smoke test per package, a Vite+React+TypeScript+Tailwind `investigator-ui` shell wired to `@ag-ui/client`, a documented docker-compose scaffold, a root Makefile, and a full README.
**Why:** Establish a stable, verified foundation (`make verify` green) for the staged development prompts that follow, per the Prompt 1 specification and its accompanying design spec.
```

- [ ] **Step 3: Commit**

```bash
git add docs/COMMIT_LOG.md
git commit -m "docs: log Prompt 1 repository foundation batch"
```

---

## Self-Review Notes

- **Spec coverage:** every required file in the spec's tree maps to a task above (root config → Task 1; 10 packages → Task 2; workspace verification → Task 3; docker-compose → Task 4; frontend → Tasks 5–7; Makefile → Task 8; gitignore → Task 9; README → Task 10; full verify → Task 11; changelog → Task 12).
- **Deferred deps confirmed:** backend version pins (fastapi, a2a-sdk, fastmcp, chromadb, ag-ui-protocol) intentionally do not appear in any Task 2 `pyproject.toml` — no package has code that uses them yet, and the spec permits deferring "most runtime dependencies until the package that needs them is implemented."
- **No placeholders:** every file template above has full, real content — no TODOs, no "similar to Task N" shortcuts.
- **Type/name consistency:** the package mapping table (Task 2) is the single source of truth for directory/import names; Tasks 1, 3, 8, and 10 all reference it rather than redefining it.
