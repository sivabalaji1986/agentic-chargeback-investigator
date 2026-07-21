# Shared Contract Layer Design

Date: 2026-07-21
Status: Approved

## Purpose

Implement the complete shared, strongly-typed contract layer inside the
existing `contracts` package (import name `chargeback_contracts`), covering
every stable application-level payload that crosses a service boundary:
A2A (orchestrator ↔ specialists), Agent Registry ↔ agents, AG-UI (orchestrator
↔ UI), A2UI (orchestrator ↔ investigator decision surface), MCP-facing
adapters, and audit persistence. Contracts and validation only — no
orchestration, agents, MCP tools, RAG, AG-UI streaming server, React UI,
A2UI rendering, deterministic recommendation logic, or persistence.

Source of truth for scope and acceptance criteria is the user-provided
Prompt 2 instructions; this document records the research findings and
execution decisions needed to implement that spec correctly, not a
restatement of it.

## Research findings (inspected the real installed SDKs, not guessed)

Both pinned SDK versions were installed in a scratch venv and inspected
directly (`a2a-sdk==1.1.1`, `ag-ui-protocol==0.1.19`, both confirmed to
exist and install cleanly from the live registry on 2026-07-21):

**a2a-sdk 1.1.1** — `a2a.types` is protobuf-generated (backed by
`a2a_pb2`), not Pydantic. `Task` (`id`, `context_id`, `status`, `artifacts`,
`history`, `metadata`), `Message` (`message_id`, `context_id`, `task_id`,
`role`, `parts`, ...), and `AgentSkill` (`id`, `name`, `description`, `tags`,
`examples`, `input_modes`, `output_modes`, ...) are all protobuf messages.
`Task.id`, `Task.context_id`, and `AgentSkill.id` are plain strings.
Every contract in Prompt 2 only needs an *ID reference* ("optional A2A task
ID / context ID") — never a full embedded protobuf object — so contracts
carry `task_id: str | None` / `context_id: str | None` fields and never
construct, wrap, or subclass the protobuf types. This also means contracts
never define a class named `AgentCard`/`AgentSkill`/`Task`/`Message`/
`Artifact`/`Part`/`TaskState` themselves, satisfying "no duplicate locally
defined versions of official A2A protocol models" by construction.

**ag-ui-protocol 0.1.19** — installs as the `ag_ui` package; `ag_ui.core`
*is* Pydantic v2 (`ConfiguredBaseModel` base). The extension point for
application-specific events is `CustomEvent(type=EventType.CUSTOM,
name: str, value: Any)`. Contracts' AG-UI payloads are standalone Pydantic
models representing the `value` of a `CustomEvent` for each of the 13 event
kinds Prompt 2 lists — not subclasses of `CustomEvent` itself, since the
streaming server that would construct `CustomEvent` instances is explicitly
out of scope for this prompt.

**A2UI** — no official SDK exists; all A2UI payloads are new,
application-owned Pydantic models, versioned `"0.9"` per the spec.

## Decisions confirmed with the user (2026-07-21)

1. **A2A ID fields**: `task_id` / `context_id` are validated non-blank
   `str | None` fields (rejecting empty-string values via `Field`
   constraints). Contracts never wrap or duplicate official A2A protobuf
   models — confirmed above by construction.

2. **mypy `tests/` exclusion scope**: Prompt 1 added a blanket
   `exclude = ["(^|/)tests/"]` to resolve a duplicate-module-name collision
   across all 10 packages' identically-named `tests/test_import.py` (none
   have `tests/__init__.py`). Since Prompt 2 introduces real test logic only
   in `contracts/tests/`, and must not restructure the other 9 packages, the
   exclusion is narrowed to name the other 9 packages explicitly (not
   `contracts`), so `contracts/tests/` gets full strict mypy coverage while
   the untouched packages' trivial smoke tests remain excluded exactly as
   before. **This narrowed exclusion is documented as temporary technical
   debt**: once a later prompt adds real tests (or at least
   `tests/__init__.py`) to the remaining 9 packages, the per-package
   exclusion list should be removed package-by-package as each one no
   longer needs it.

3. **Test requirement #20** ("workspace imports from at least two dependent
   packages"): `orchestrator-agent` and `transaction-agent` each get
   `contracts` added to their `dependencies` (via `uv`'s workspace source
   mechanism) plus one small integration test importing from
   `chargeback_contracts` and constructing/round-tripping one real contract.
   Additive only — no business logic added to either package.

## Package structure

Following the prompt's suggested module split under
`contracts/src/chargeback_contracts/`:

```
__init__.py       # public contract surface (re-exports)
common.py         # shared primitives: CurrencyCode, Money, timestamps, IDs
skills.py         # SkillId, skill ID constants, dispute-type→skill mapping
dispute.py        # InvestigationRequest, source channel / dispute type enums
evidence.py       # EvidenceRef, evidence type enum, URI scheme validation
findings.py       # SpecialistFinding + Transaction/CustomerHistory/MerchantEvidence payloads
policy.py         # PolicyInterpretation
recommendation.py # InvestigationRecommendation, MissingCapabilityWarning
registry.py       # (module reserved per spec; skill/capability-adjacent registry-facing types)
agui.py           # AG-UI application event payloads (13 kinds)
a2ui.py           # A2UI envelope + decision-interface payloads
decisions.py       # InvestigatorDecision
mcp.py            # MCP boundary request/response contracts
records.py        # InvestigationRecord
```

`common.py` has zero imports from sibling contract modules (it's the leaf);
every other module may import `common` and `skills`; no module imports
`registry`/`agui`/`a2ui`/`decisions`/`mcp`/`records` from an earlier-listed
module, keeping the dependency graph a DAG with no cycles. `__init__.py`
imports from all modules and re-exports the public surface; nothing in
`chargeback_contracts` imports from any other application package.

## Modelling conventions (applied uniformly)

Pydantic v2, `model_config = ConfigDict(extra="forbid")` on every model,
string-backed enums (`class X(str, Enum)`), timezone-aware UTC datetimes
(validated via a shared `field_validator`), `Decimal` for money with a
separate ISO 4217 `CurrencyCode` (3-letter uppercase, validated), `Field`
constraints for non-empty IDs/percentages, no bare `dict`/`Any` except
where explicitly noted (none needed, per the A2A/AG-UI findings above), no
mutable defaults, snake_case internals with camelCase aliases only where an
external protocol requires it (none of our own contracts need protocol
aliases in Prompt 2 — A2A/AG-UI alias needs live inside their own SDKs, not
ours). No confidence scores anywhere.

## Validation approach

Cross-field validation uses Pydantic v2 `model_validator(mode="after")` for
things like "completion timestamp cannot precede start timestamp" and
"completed finding requires completion timestamp"; per-field `Field`/
`field_validator` for currency codes, positive amounts, non-blank IDs,
percentage bounds, and evidence URI scheme allowlisting (`evidence://`
only — any other scheme, including `file://` or a bare path, is rejected).

## Test approach

Replace `contracts/tests/test_import.py` with a focused suite split
roughly by module (`test_common.py`, `test_skills.py`, `test_dispute.py`,
`test_evidence.py`, `test_findings.py`, `test_policy.py`,
`test_recommendation.py`, `test_agui.py`, `test_a2ui.py`,
`test_decisions.py`, `test_mcp.py`, `test_records.py`), covering the 20
enumerated test requirements from the prompt. Real unit tests with concrete
data, not snapshots.

## Out of scope (explicit non-goals for this pass)

Agent Registry HTTP endpoints, orchestrator workflow, specialist agents,
MCP server tools, RAG/ChromaDB, Ollama connectivity, AG-UI streaming
server, React UI, A2UI renderer, deterministic recommendation engine,
persistence, mock business services.

## Acceptance criteria

Per the user-provided Prompt 2 instructions in full; summarized: all 20
test requirements pass, `make verify` green (ruff, strict mypy for
production *and* test code within the narrowed scope, full pytest suite,
existing React build), README + COMMIT_LOG updated, pre-existing
`.gitignore` modification and `tmp/prompts/Prompt01.md` left untouched.
