# Dispute MCP Server Design

Date: 2026-07-22
Status: Approved

## Purpose

Implement `dispute-mcp-server`, a single FastMCP 3.4.4 server exposing four
logical tool groups (case, transaction, customer, merchant) backed by
deterministic, internally-consistent seeded mock data. Enterprise data
access only — no business decisions, no orchestration, no persistence
across restarts.

Source of truth for scope and acceptance criteria is the user-provided
Prompt 3 instructions (`tmp/prompts/Prompt03-Agent-Registry.md`, despite
its filename — the file's actual content is the dispute-mcp-server
prompt, confirmed correct by the user after an earlier mismatched prompt
was withdrawn). This document records the research findings and execution
decisions needed to implement it, not a restatement of the prompt.

## Research findings (inspected the real installed SDK)

`fastmcp==3.4.4` was installed in a scratch venv and exercised directly:

- `FastMCP(name)` creates a server instance; `@mcp.tool` decorates a plain
  typed function (with a docstring) to register it as an MCP tool —
  confirmed by round-tripping a tool through `fastmcp.Client`.
- `fastmcp.Client(mcp)` accepts the `FastMCP` instance directly as an
  in-memory transport — no real stdio/HTTP process needed for testing.
  `client.list_tools()` and `client.call_tool(name, args)` both work
  in-memory; a `ValueError` raised inside a tool surfaces to the client as
  `fastmcp.exceptions.ToolError`.
- This confirms the whole test suite (tool behavior, invalid identifiers,
  discovery, startup) can be written without any real network I/O,
  matching the constraint that dispute-mcp-server tests must not depend on
  live integrations.

## Decisions

### Contract reuse vs. new local models

`chargeback_contracts.mcp`'s read-side contracts (`GetCaseResponse`,
`GetTransactionResponse`, ...) are *deliberately* minimal per Prompt 2's
own design note — no business schema, because at the time no prompt had
yet defined one. This prompt is exactly where that schema needs to exist,
so reusing those minimal response shapes would mean wrapping richer mock
data in a container that immediately has to be worked around. Decision:
reuse the write-side contracts fully (`UpdateCaseStatusRequest`,
`CreateAuditEntryRequest`, `McpWriteResponse` — these are generic
envelopes that don't need business-specific richness and are a genuine
fit as-is) for `update_case` and `write_audit`; define new local,
package-owned Pydantic models in
`dispute-mcp-server/src/dispute_mcp_server/models.py` for every read
tool's return type (`get_case`, `get_transaction`, `get_authorization`,
`get_settlement`, `get_refund_or_reversal`, `get_customer_profile`,
`get_prior_disputes`, `get_refund_history`, `get_merchant_evidence`,
`get_delivery_details`, `get_cancellation_details`) — not added to
`chargeback_contracts`, per the instruction not to duplicate or refactor
completed work.

Tool *parameters* use flat scalar arguments (`case_id: str`,
`transaction_id: str`, ...) rather than wrapping inputs in request
objects — this is FastMCP's idiomatic style (confirmed during research:
`@mcp.tool` generates its schema straight from the function signature) and
keeps tool calls natural (flat kwargs, not one nested object), matching
how the existing `GetCaseRequest`/`GetTransactionRequest` single-field
shapes would look anyway if unwrapped.

### Repository shape

`seed_data.py` holds static, cross-referenced mock records (cases,
transactions, authorizations, settlements, refunds, customer profiles,
prior disputes, merchant evidence, delivery details, cancellation details,
audit records) keyed by consistent IDs so future prompts can reuse them
(e.g. `CASE-1001` ↔ `TXN-2001` ↔ `CUST-3001` ↔ `MERCH-4001`).
`repository.py`'s `DisputeRepository` wraps this data with typed lookup
methods, raising a local `NotFoundError` for unknown IDs. `update_case`
and `write_audit` mutate in-memory state for the life of the process — no
persistence across restarts is required or implemented (unlike a
database-backed service; nothing in this prompt asks for that).

### Tool registration (avoiding circular imports)

Each `tools/*_tools.py` module exports one `register_*_tools(mcp: FastMCP,
repository: DisputeRepository, logger: Logger) -> None` function
containing `@mcp.tool`-decorated closures. `main.py` creates the `FastMCP`
instance and the repository, then calls all four register functions — this
avoids tool modules importing `mcp` from `main.py` (which would be
circular) and keeps the repository/logger injectable for tests.

### Docker Compose service shape

The prompt doesn't specify a port for `dispute-mcp-server`, and FastMCP
servers are conventionally run over stdio for local MCP-client use rather
than networked. The compose service runs the server via its stdio
entrypoint with no host port mapping, documented with a comment explaining
this choice — not guessed at as an HTTP-exposed service the prompt never
asked for.

## Package structure

Following the prompt's suggested layout, with one addition
(`models.py`, for the local response models described above):

```
dispute-mcp-server/src/dispute_mcp_server/
├── __init__.py
├── config.py       # env-backed settings (service name, log level)
├── logging.py       # structured logging setup + tool-call log helper
├── seed_data.py     # static, cross-referenced mock records
├── models.py        # local Pydantic models for entities with no shared contract
├── repository.py    # DisputeRepository — owns seeded data, typed lookups
├── tools/
│   ├── __init__.py
│   ├── case_tools.py         # get_case, update_case, write_audit
│   ├── transaction_tools.py  # get_transaction, get_authorization, get_settlement, get_refund_or_reversal
│   ├── customer_tools.py     # get_customer_profile, get_prior_disputes, get_refund_history
│   └── merchant_tools.py     # get_merchant_evidence, get_delivery_details, get_cancellation_details
└── main.py          # creates FastMCP + repository, registers all tools, run entrypoint
```

## Out of scope (explicit non-goals for this pass)

Agent Registry, Orchestrator, A2A task execution, AG-UI, A2UI, RAG,
Ollama, recommendation rules, specialist agent logic, Duplicate
Transaction Agent behavior, real persistence across restarts.

## Acceptance criteria

Per the user-provided Prompt 3 instructions in full; summarized: FastMCP
server starts, all 13 tools discoverable, seeded responses deterministic,
no business rules, docker-compose validates, `make verify` passes,
existing Prompt 1/2 tests remain green, pre-existing `.gitignore`
modification and `tmp/prompts/*.md` files untouched.
