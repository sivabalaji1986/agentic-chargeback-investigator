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

## Shared contract layer

Every stable payload that crosses a service boundary — A2A (Orchestrator ↔
specialists), Agent Registry ↔ agents, AG-UI (Orchestrator ↔ UI), A2UI
(Orchestrator ↔ investigator decision surface), MCP-facing adapters, and
audit persistence — is defined once in `contracts` (import name
`chargeback_contracts`). All application services depend inward on it; it
depends on nothing in this repository.

```text
orchestrator-agent  transaction-agent  customer-history-agent  ...
        \                  |                    /
         \                 |                   /
          \                |                  /
           v                v                v
                    chargeback_contracts
```

Key points:

- Official A2A protocol objects (`Task`, `Message`, `AgentSkill`, ...) come
  from `a2a.types` (`a2a-sdk`) — this repository never redefines them; it
  only carries their string `task_id` / `context_id` identifiers.
- Official AG-UI event types come from `ag_ui.core` (`ag-ui-protocol`);
  `chargeback_contracts` defines only the typed application payloads
  carried inside a `CustomEvent`.
- A2UI has no official SDK; every A2UI payload here is application-owned,
  targeting specification version `0.9`.
- Specialists (`SpecialistFinding`) and the Policy Agent
  (`PolicyInterpretation`) never carry a recommendation — only
  `InvestigationRecommendation` does, and it is always deterministic;
  `explanation` is independent, descriptive text.
- Human approval is mandatory: a `WorkflowStatus.COMPLETED`
  `InvestigationRecord` cannot validate without an `InvestigatorDecision`.

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
