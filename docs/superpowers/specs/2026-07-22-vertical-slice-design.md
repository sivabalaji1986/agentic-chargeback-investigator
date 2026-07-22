# Vertical Slice (End-to-End Spike) Design

Date: 2026-07-22
Status: Approved

## Purpose

Build the first end-to-end vertical slice proving the architecture:
intake harness → Transaction Agent → dispute-mcp-server → AG-UI →
investigator-ui → A2UI decision card → investigator action → backend.
This is deliberately temporary spike wiring for the intake path (to be
replaced by the Orchestrator in Prompt 6), but the Transaction Agent's
core logic, the AG-UI integration, the UI components, and the backend
action endpoint must be genuinely reusable, not throwaway.

Source of truth for scope and acceptance criteria is the user-provided
Prompt 4 instructions. This document records real validation results and
execution decisions, not a restatement of the prompt.

## LLM validation (performed for real against the live host Ollama, 2026-07-22)

- **No `<think>` leakage**: confirmed clean with `think=false` across all
  test calls.
- **Structured JSON**: 100% valid, parseable JSON across 8 test calls
  using `format: "json"`.
- **Capability identification reliability**: 5/5 identical results on a
  well-scoped classification prompt. An earlier, genuinely ambiguous test
  scenario produced 3 different (but each individually valid) answers
  across 3 runs — this reflects the scenario's real ambiguity (multiple
  defensible classifications), not model unreliability, and does not
  trigger the "stop and recommend qwen3:14b" gate.
- **Docker → host Ollama**: confirmed reachable — a container hitting
  `http://host.docker.internal:11434/api/tags` returns HTTP 200.

**Conclusion: proceed with qwen3.5. Do not switch to qwen3:14b.**

**Model tag deviation**: `.env.example` (from Prompt 1) specifies
`OLLAMA_TEXT_MODEL=qwen3.5:9b`, but no tag literally named `9b` exists on
this host — only `qwen3.5:latest` (9.7B parameters, quantization Q4_K_M),
which is almost certainly the intended model under Ollama's default
tagging. `.env.example` is updated to `qwen3.5:latest`.

## AG-UI event mapping (real API research, not guessed)

Inspected `ag_ui.encoder.EventEncoder` directly: `.encode(event)` produces
a standard SSE-formatted string (`data: {...}\n\n`) and
`.get_content_type()` returns `text/event-stream` — this is what
`fastapi.responses.StreamingResponse` needs directly.

Inspected `@ag-ui/client`'s real TypeScript declarations (installed and
read `dist/index.d.ts`, not assumed): `HttpAgent` (extends `AbstractAgent`)
takes `{ url, headers?, fetch? }`; `.runAgent(parameters?, subscriber?)`
drives a run, where `subscriber` is an `AgentSubscriber` object with named
optional hooks (`onEvent`, `onRunStartedEvent`, `onRunFinishedEvent`,
`onCustomEvent`, etc.) — a real, typed callback-per-event-kind pattern,
not a generic message bus.

All 5 required stream milestones (Investigation Started, MCP Lookup,
Transaction Loaded, Recommendation Ready, Investigation Completed) map
cleanly onto **existing** Prompt 2 `chargeback_contracts.agui` payloads —
verified field-by-field, no gaps:

| Milestone | Existing contract | Fit |
|---|---|---|
| Investigation Started | `InvestigationAcceptedEvent` | exact — has `dispute_type`, `requested_skill_ids` |
| MCP Lookup | `SpecialistStartedEvent` | exact — Transaction Agent is the specialist; "started" covers the MCP lookup beginning |
| Transaction Loaded | `SpecialistFindingReceivedEvent` | exact — the loaded transaction is reported as a `finding_id` |
| Recommendation Ready | `RecommendationProducedEvent` | exact |
| Investigation Completed | `InvestigationCompletedEvent` | exact |

**No new AG-UI contracts are needed.** The prompt's own instruction ("if
protocol payloads require refinement, update contracts...") does not
apply — refinement was checked for and found unnecessary. This is
reported rather than silently assumed, since the prompt explicitly asked
for this check.

## Decisions

### Architecture: temporary vs. reusable

`transaction-agent` (FastAPI) hosts three endpoints in this spike:
- `POST /intake` — **temporary**: seeds a canned investigation for the
  existing seeded `CASE-1001` (from Prompt 3's `dispute-mcp-server` seed
  data) and calls the run logic directly. This is exactly the piece
  Prompt 6's Orchestrator replaces — it exists only to prove the pipeline
  without a real routing layer.
- `POST /agent/run` — **reusable**: the actual AG-UI SSE streaming
  endpoint. Accepts a `RunAgentInput`-shaped payload, emits the 5 events
  above, and is the piece Prompt 6 will call the same way the Orchestrator
  will (a caller doesn't need to know whether intake or the Orchestrator
  triggered it).
- `POST /actions/decision` — **reusable**: accepts an
  `InvestigatorDecision`-shaped payload (from `chargeback_contracts`),
  logs it, returns success. Not specific to this spike's wiring.

### MCP integration: in-process client, not a new transport

`dispute-mcp-server` remains stdio-only (Prompt 3's decision — no port
exposed). `transaction-agent` calls it via `fastmcp.Client(mcp_app)`
in-process, importing `dispute_mcp_server.main.mcp` directly — the exact
pattern already proven in Prompt 3's own test suite. This avoids inventing
a new transport or duplicating lookup logic, and is honest about being
in-process (documented, not disguised as a network call).

### LLM role: explanation only, not the recommendation

The recommendation itself is a hardcoded mock value
(`RecommendationType.REQUEST_MORE_EVIDENCE`, chosen because it is a
defensible, non-committal outcome for a partially-investigated case and
requires no invented business logic to justify). The one real Ollama call
(`qwen3.5:latest`, `think=false`, `format=json`) generates the
`explanation` text that flows into the A2UI `DecisionCard.explanation`
field — this is what actually validates the LLM integration end-to-end,
without building any deterministic-recommendation logic (Prompt 9's job).

### Testing strategy

Most tests inject a fake/stub Ollama client (dependency-injected, same
pattern as `config.py`/`clock`-style injection used in earlier prompts) so
`make verify` doesn't hard-depend on a live LLM. One explicit,
separately-named real-Ollama integration test exercises the actual host
Ollama end-to-end (skipping cleanly, not failing, if unreachable) — this
environment has Ollama running, so it will actually execute here.

Given Playwright browser tools are available in this session, the React
components are verified with a real dev-server + browser check (via
Playwright), not just `vite build`, per the standing instruction to
actually exercise UI changes in a browser before claiming they work.

### Execution approach

Confirmed with the user: subagent-driven-development (same rigor as
Prompts 1-3), despite Prompt 4 not explicitly requesting it — the scope
here spans backend, LLM integration, streaming protocol, and frontend,
warranting the same fresh-implementer/fresh-reviewer/final-review process.

## Out of scope (explicit non-goals for this pass)

Agent Registry, Orchestrator, Customer History/Merchant Evidence/Policy
Agents, RAG, deterministic recommendation rules, A2A routing.

## Acceptance criteria

Per the user-provided Prompt 4 instructions in full; summarized: full
round-trip demonstrated (intake → AG-UI stream → A2UI decision → action
logged), AG-UI and A2UI interoperate, UI built from reusable components,
existing MCP reused (not duplicated), no Registry/Orchestrator/
recommendation-engine, existing tests remain green, `make verify` passes.
