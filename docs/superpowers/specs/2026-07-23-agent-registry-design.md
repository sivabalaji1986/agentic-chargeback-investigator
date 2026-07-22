# Agent Registry Design

Date: 2026-07-23
Status: Approved

## Purpose

Implement `agent-registry`, a standalone FastAPI service providing
lease-based runtime capability discovery: agents register themselves with
an advertised capability set and an endpoint, periodically renew a lease to
stay listed, and are automatically dropped from discovery once their lease
expires without renewal. No database — process-lifetime in-memory state
only. Not integrated with `transaction-agent` yet; that wiring is
explicitly deferred to a later prompt.

Source of truth for scope and acceptance criteria is the user-provided
Prompt 5 instructions. This document records the design decisions needed
to implement it — the prompt leaves several concrete choices open (exact
routes, HTTP verbs, duplicate-registration semantics, concurrency
mechanism), which are decided and justified below rather than guessed at
implementation time.

## Decisions

### Framework: FastAPI, matching `transaction-agent`'s convention

Unlike `dispute-mcp-server` (MCP/stdio, no HTTP), this prompt asks for a
"Registration API", "Health endpoint", and other clearly HTTP-shaped
capabilities. `transaction-agent` already establishes the FastAPI +
`create_app(...)` + `TestClient` pattern in this repo; reusing it keeps the
whole workspace consistent rather than introducing a second HTTP
convention.

### Capability reuse: `chargeback_contracts.skills.SkillId`, never redefined

The prompt's "never duplicate capability constants" instruction points
directly at `SkillId` (`contracts/src/chargeback_contracts/skills.py`) —
the only existing capability enum in the repo, already described in its
own docstring as "shared by the Agent Registry, agents, and Orchestrator."
`agent-registry` takes a dependency on `contracts` and uses `SkillId`
everywhere a capability is represented; it defines no capability enum of
its own. The registration model itself (agent ID, endpoint, version,
lease timestamps, status) has no existing shared contract, so it is
defined locally in `agent-registry`'s own `models.py` — consistent with
how `dispute-mcp-server` defined its own local models for entities with no
prior contract, without proposing changes to `chargeback_contracts`.

### Registration semantics: idempotent upsert by `agent_id`

The prompt lists "Duplicate registration" and "Re-register" as two
separate behaviors to support. Interpretation: re-registering the same
`agent_id` while its lease is still active ("duplicate registration") is
not an error — it's a normal upsert that refreshes the endpoint, version,
capabilities, and lease (an agent process may legitimately call register
again without tracking whether it's the first call). Registering the same
`agent_id` after it has expired or been deregistered ("re-register") is
identical code path — since expiry and deregistration both remove the
record entirely (see below), there is no stale state left to distinguish
between the two cases. One upsert method serves both; the test suite
covers both trigger conditions.

### Expiry and deregistration both fully remove the record

Rather than introducing an `EXPIRED` or `DEREGISTERED` status alongside
`ACTIVE`, both operations remove the agent from the repository outright.
This keeps "automatic expiry" and "deregistration" a single code path
(`repository.remove(agent_id)`), and keeps re-registration trivial (a
removed `agent_id` is indistinguishable from one that was never
registered). `AgentRecord.status` therefore only ever holds `ACTIVE` while
a record exists at all — modeled as a real enum (`AgentStatus.ACTIVE`) for
forward compatibility per the prompt's explicit "Status" field
requirement, not because a second value is needed yet (YAGNI).

### Concurrency: explicit `asyncio.Lock` around repository mutations

CPython's GIL means simple synchronous dict mutations without an internal
`await` can't interleave mid-operation — but relying on that implicitly
would be a fragile, undocumented invariant, and the prompt explicitly asks
for a "Concurrent registrations" test. The repository wraps every mutating
method (`register`, `renew`, `remove`, `sweep_expired`) in an
`asyncio.Lock`, so correctness is explicit and verifiable rather than
incidental. The concurrency test drives this directly with
`asyncio.gather` over many concurrent `register`/`renew` calls against the
service layer (not through `TestClient`, which executes requests
sequentially and would not exercise the lock meaningfully).

### Deterministic lease-expiry testing: injectable `Clock`

Real lease expiry (waiting tens of seconds in a test) would make the test
suite slow and flaky. `agent-registry` introduces a `Clock` protocol
(`now() -> datetime`) with two implementations: `SystemClock` (real
`datetime.now(UTC)`, used by `create_app()`'s default) and `FakeClock`
(test-controlled, manually advanced with `.advance(seconds)`), following
the same constructor-injection pattern already used for
`transaction_agent`'s `ExplanationClient`. Lease-expiry tests register an
agent, advance the `FakeClock` past its lease duration, and call the
service's `sweep_expired()` directly — no real sleeping, no background
task involved in the test.

### Background sweep: FastAPI lifespan-managed `asyncio` task

`main.py`'s `create_app()` starts a background task on FastAPI startup
(via the `lifespan` context manager) that calls `sweep_expired()` on a
configurable interval (`LEASE_SWEEP_INTERVAL_SECONDS`) and is cancelled
cleanly on shutdown. This is the real, always-on mechanism `make
registry-run` exercises; test coverage of the sweep *logic* itself goes
through direct, synchronous calls to `sweep_expired()` with a `FakeClock`
(above), not through the background task, keeping tests fast and
deterministic. `lease_manager.py` holds only the loop/task lifecycle
(start/stop), not the expiry logic itself, which lives in `service.py` and
is independently testable.

### Discovery semantics: unknown/unmatched capability returns an empty list, not an error

"Unknown capability" as a discovery-behavior test is interpreted as: a
syntactically valid `SkillId` that no currently-registered agent
advertises returns `200` with an empty list — a discovery miss is a normal
outcome for a lookup service, not an error condition. (A capability string
that isn't a valid `SkillId` value at all is a distinct, ordinary `422`
validation error, handled automatically by FastAPI/Pydantic — not a
special case to build.) "Empty registry" (no agents at all) returns the
same shape: an empty list, whether listing agents, listing capabilities,
or discovering by capability.

### Endpoints

- `POST /agents` — register or re-register (idempotent upsert by
  `agent_id`); `201` on a brand-new `agent_id`, `200` when refreshing an
  existing one.
- `POST /agents/{agent_id}/renew` — renew an existing, still-active
  agent's lease; `404` if `agent_id` is unknown or already expired (use
  `POST /agents` again in that case — that's what "re-register" is for).
- `DELETE /agents/{agent_id}` — deregister; `204` on success, `404` if
  unknown.
- `GET /agents` — list all currently active agents; empty list if none.
- `GET /agents/capabilities` — list the distinct `SkillId` values
  currently advertised by at least one active agent; empty list if none.
- `GET /agents/discover?capability=...` — list active agents advertising
  a given `SkillId`; empty list for no matches or an empty registry.
- `GET /health` — `{"status": "ok", "agent_count": <int>}`; no external
  dependencies to check (no database, per the prompt's explicit
  constraint), so this only reflects in-process state.

### Logging: explicit handler, not `logging.basicConfig`

Deliberately reusing `dispute-mcp-server`'s `logging.py` pattern
(`logger.setLevel(level)` + manually attaching a `StreamHandler` if none
exists) rather than `logging.basicConfig`. This directly applies a lesson
from Prompt 4's Task 11: `transaction-agent` originally relied on nothing
configuring the root logger at all, silently dropping every `INFO` log in
the real running process (only caught via live browser verification, not
unit tests). `dispute-mcp-server`'s explicit-handler approach never had
this gap, so `agent-registry` follows it from the start instead of
repeating the same mistake.

### Small, justified Makefile addition

The prompt doesn't mention Docker or Makefile targets, and no
docker-compose work is in scope here (unlike Prompt 3's dispute-mcp-server,
which explicitly required a runnable container). But Prompt 3 did
establish `mcp-test`/`mcp-run` targets for exactly this kind of standalone
service; adding the equivalent `registry-test`/`registry-run` targets is a
minimal, low-risk extension of an existing convention, directly serving
the "Registry starts" acceptance criterion in a discoverable way — not new
scope, just consistency.

## Package structure

```
agent-registry/src/agent_registry/
├── __init__.py
├── config.py         # env-backed settings (service name, host/port, lease durations, log level)
├── clock.py           # Clock protocol + SystemClock + FakeClock
├── models.py          # AgentStatus, AgentRegistration, AgentRecord (reuses SkillId from contracts)
├── logging.py          # structured logging setup (mirrors dispute-mcp-server's explicit-handler pattern)
├── repository.py       # AgentRepository — in-memory dict, asyncio.Lock-guarded mutations
├── service.py          # RegistryService — register/renew/deregister/discover/sweep_expired, uses Clock
├── lease_manager.py     # background sweep task lifecycle (start/stop), used only by api.py's lifespan
├── api.py              # FastAPI app, create_app(*, clock=None), all endpoints, lifespan wiring
└── main.py              # uvicorn entrypoint
```

## Out of scope (explicit non-goals for this pass)

Orchestrator, A2A, Customer History Agent, Merchant Evidence Agent, Policy
Agent, Duplicate Transaction Agent, RAG, recommendation rules,
Transaction-Agent-to-Registry integration. Existing `transaction-agent`,
`dispute-mcp-server`, AG-UI integration, and `investigator-ui` are not
modified in this pass — Task 14 (final verification) explicitly confirms
their source directories are untouched by this batch's diff.

## Acceptance criteria

Per the user-provided Prompt 5 instructions in full; summarized: registry
starts, lease expiry works (verified with a `FakeClock`, not real sleep),
discovery works (found, unknown-capability, and empty-registry cases),
health endpoint works, no orchestration logic anywhere, `make verify`
passes, all Prompt 1-4 tests remain green.
