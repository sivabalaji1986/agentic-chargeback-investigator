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

## Dispute MCP Server

`dispute-mcp-server` is a single FastMCP server exposing mocked enterprise
data through four tool groups — case, transaction, customer, merchant (13
tools total). All responses come from deterministic, cross-referenced
seed data (`seed_data.py`); there are no live integrations and no business
decisions made here.

Tool groups:

- **Case**: `get_case`, `update_case`, `write_audit`
- **Transaction**: `get_transaction`, `get_authorization`, `get_settlement`, `get_refund_or_reversal`
- **Customer**: `get_customer_profile`, `get_prior_disputes`, `get_refund_history`
- **Merchant**: `get_merchant_evidence`, `get_delivery_details`, `get_cancellation_details`

`update_case` and `write_audit` reuse the shared `chargeback_contracts.mcp`
write-side envelope contracts (idempotency key required, structured
success/failure response); every other tool returns a package-owned
response model, since the underlying business schema didn't exist before
this prompt.

Run it locally with `make mcp-run`; test it with `make mcp-test`.

## Vertical Slice (End-to-End Spike)

The first end-to-end path proving the architecture:

```text
Intake harness (temporary)
        v
Transaction Agent (FastAPI, reusable)
        v
dispute-mcp-server (in-process fastmcp.Client)
        v
AG-UI event stream (ag-ui-protocol 0.1.19)
        v
investigator-ui (@ag-ui/client 0.0.57)
        v
A2UI v0.9 decision card
        v
Investigator action -> backend
```

`transaction-agent` exposes three endpoints:

- `POST /intake` — **temporary**: seeds a run for the existing seeded `CASE-1001`, standing in for the Orchestrator that replaces it in a later prompt.
- `POST /agent/run` — **reusable**: the real AG-UI wire-protocol endpoint (`RunAgentInput` in, SSE-encoded events out).
- `POST /actions/decision` — **reusable**: logs an investigator's Approve / Reject / Request More Evidence decision.

The recommendation returned is a **fixed mock value** (`request_more_evidence`) — deterministic recommendation logic is Prompt 9's job. The one real LLM call (host Ollama, `qwen3.5:latest`, `think=false`) generates only the explanation text shown on the decision card; this was validated directly against the live Ollama instance (no `<think>` leakage, reliably structured JSON, reachable from a container via `host.docker.internal`).

All 5 streamed milestones (Investigation Started, MCP Lookup, Transaction Loaded, Recommendation Ready, Investigation Completed) reuse **existing** `chargeback_contracts.agui` event payloads from Prompt 2 — no new shared contracts were needed.

`investigator-ui` gained four reusable components: `InvestigationTimeline`, `EventStream`, `RecommendationCard`, `DecisionCard` — a later prompt extends these rather than replacing them.

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
