# Vertical Slice (End-to-End Spike) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove the full round-trip: intake harness → Transaction Agent → dispute-mcp-server → AG-UI stream → investigator-ui → A2UI decision card → investigator action → backend. Temporary spike wiring for intake; Transaction Agent core logic, AG-UI integration, UI components, and the action endpoint must be reusable.

**Architecture:** `transaction-agent` becomes a FastAPI service with three endpoints: `/intake` (temporary, defaults to seeded `CASE-1001`), `/agent/run` (reusable — speaks the real AG-UI wire protocol via `ag_ui.core.RunAgentInput`/`RunFinishedEvent`), `/actions/decision` (reusable — logs an `InvestigatorDecision`). It calls `dispute-mcp-server` in-process via `fastmcp.Client`, calls host Ollama once for explanation text, and emits a fixed mock recommendation. `investigator-ui` gets 4 reusable components consuming `@ag-ui/client`'s `HttpAgent`.

**Tech Stack:** Python 3.13, FastAPI 0.139.2, uvicorn 0.51.0, httpx 0.28.1, `ag-ui-protocol` 0.1.19, `fastmcp` 3.4.4, existing `chargeback_contracts`/`dispute-mcp-server` packages; React 19 + `@ag-ui/client` 0.0.57 (already a dependency, unused until now).

## Global Constraints

- No Agent Registry, Orchestrator, Customer History/Merchant Evidence/Policy Agents, RAG, deterministic recommendation logic, or A2A routing — the recommendation is a hardcoded mock (`RecommendationType.REQUEST_MORE_EVIDENCE`); only the `explanation` text is LLM-generated.
- All 5 required AG-UI stream milestones map onto **existing** `chargeback_contracts.agui` payloads (confirmed by field-level inspection during design) — do not add new AG-UI contracts unless a task discovers a genuine gap; if one is found, update `chargeback_contracts/agui.py` narrowly, rerun the full `contracts/tests/` suite, and do not touch `dispute.py`/`findings.py`/`recommendation.py`/`records.py` ("business contracts" stay unchanged).
- `dispute-mcp-server` stays stdio-only (no new port) — `transaction-agent` calls it via `fastmcp.Client(dispute_mcp_server.main.mcp)` in-process, importing the same module object Prompt 3's own tests use.
- `ag_ui.core` models use camelCase JSON aliases on the wire (`threadId`, `runId`, `forwardedProps`, ...) — confirmed by direct inspection. `/agent/run` accepts a real `ag_ui.core.RunAgentInput` request body (FastAPI + Pydantic v2 handle the alias parsing natively), extracting `case_id` from `input.forwarded_props["case_id"]` — this is what makes the endpoint genuinely AG-UI-protocol-compliant rather than a look-alike.
- Ollama model: `.env.example`'s `OLLAMA_TEXT_MODEL` is corrected from `qwen3.5:9b` (a tag that does not exist on this host) to `qwen3.5:latest` (the actual 9.7B model) — confirmed via `curl http://localhost:11434/api/tags`.
- Most tests inject `FakeExplanationClient` (no live LLM dependency) so `make verify` doesn't require Ollama; exactly one test (`test_llm_client_live_ollama.py`) exercises the real host Ollama, skipping cleanly (not failing) if unreachable.
- Pre-existing, already-committed repo state must not be touched: the `.gitignore` modification and `tmp/prompts/*.md` files.
- Commit workflow for this batch (explicit user instruction): every created/modified file gets its own `git add <file> && git commit`, with **no** `docs/COMMIT_LOG.md` touch until the final task, which the controller writes directly (lesson carried from Prompt 1's premature-changelog incident).
- `make verify` must stay green throughout.

---

### Task 1: `transaction-agent` dependencies + Ollama model tag fix

**Files:**
- Modify: `transaction-agent/pyproject.toml`
- Modify: `.env.example`

**Interfaces:**
- Produces: `fastapi`, `uvicorn`, `httpx`, `ag-ui-protocol`, `fastmcp`, and workspace-local `dispute-mcp-server` available to every later task.

- [ ] **Step 1: Update `transaction-agent/pyproject.toml`**

Current content (from Prompt 2, Task 16):
```toml
[project]
name = "transaction-agent"
version = "0.1.0"
description = "Transaction-domain investigation"
requires-python = ">=3.13"
dependencies = ["contracts"]

[tool.uv.sources]
contracts = { workspace = true }

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/transaction_agent"]
```

Replace with:
```toml
[project]
name = "transaction-agent"
version = "0.1.0"
description = "Transaction-domain investigation"
requires-python = ">=3.13"
dependencies = [
    "fastapi==0.139.2",
    "uvicorn[standard]==0.51.0",
    "httpx==0.28.1",
    "ag-ui-protocol==0.1.19",
    "fastmcp==3.4.4",
    "contracts",
    "dispute-mcp-server",
]

[tool.uv.sources]
contracts = { workspace = true }
dispute-mcp-server = { workspace = true }

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/transaction_agent"]
```

- [ ] **Step 2: Lock and sync**

Run: `uv lock && uv sync --all-packages`
Expected: resolves cleanly. All 5 new versions were confirmed to exist on the live registry during design research (2026-07-22). If resolution fails, STOP and report BLOCKED with the exact error rather than substituting a version.

- [ ] **Step 3: Update `.env.example`**

Change the line:
```text
OLLAMA_TEXT_MODEL=qwen3.5:9b
```
to:
```text
OLLAMA_TEXT_MODEL=qwen3.5:latest
```
(Leave every other line in `.env.example` unchanged — verify with `git diff` that only this one line changed.)

- [ ] **Step 4: Commit**

```bash
git add transaction-agent/pyproject.toml uv.lock
git commit -m "chore: add transaction-agent dependencies (fastapi, uvicorn, httpx, ag-ui-protocol, fastmcp)"
git add .env.example
git commit -m "fix: correct OLLAMA_TEXT_MODEL to the actual installed tag (qwen3.5:latest)"
```

---

### Task 2: `config.py` + `llm_client.py` (explanation client, injectable)

**Files:**
- Create: `transaction-agent/src/transaction_agent/config.py`
- Create: `transaction-agent/src/transaction_agent/llm_client.py`
- Create: `transaction-agent/tests/test_llm_client.py`

**Interfaces:**
- Produces: `Settings`, `load_settings()`, `ExplanationClient` (protocol), `OllamaExplanationClient`, `FakeExplanationClient` — consumed by `service.py` and `api.py`.

- [ ] **Step 1: Write `transaction-agent/src/transaction_agent/config.py`**

```python
"""Environment-backed settings for transaction-agent."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    service_name: str
    ollama_base_url: str
    ollama_text_model: str
    log_level: str


def load_settings() -> Settings:
    return Settings(
        service_name=os.environ.get("SERVICE_NAME", "transaction-agent"),
        ollama_base_url=os.environ.get(
            "OLLAMA_BASE_URL", "http://host.docker.internal:11434"
        ),
        ollama_text_model=os.environ.get("OLLAMA_TEXT_MODEL", "qwen3.5:latest"),
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
    )
```

- [ ] **Step 2: Write `transaction-agent/src/transaction_agent/llm_client.py`**

```python
"""LLM client for generating investigation explanations.

The recommendation itself is never LLM-generated in this prompt -- only
the explanation text. See
docs/superpowers/specs/2026-07-22-vertical-slice-design.md.
"""

from __future__ import annotations

import json
from typing import Protocol

import httpx


class ExplanationClient(Protocol):
    async def generate_explanation(self, *, dispute_summary: str) -> str: ...


class OllamaExplanationClient:
    """Real client: calls the host Ollama /api/chat endpoint.

    Uses think=false (validated during design research to produce no
    <think> leakage) and format=json (validated to produce reliably
    parseable structured output for a well-scoped prompt).
    """

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        timeout_seconds: float = 30.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = base_url
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    async def generate_explanation(self, *, dispute_summary: str) -> str:
        async with httpx.AsyncClient(
            timeout=self._timeout_seconds, transport=self._transport
        ) as client:
            response = await client.post(
                f"{self._base_url}/api/chat",
                json={
                    "model": self._model,
                    "think": False,
                    "stream": False,
                    "format": "json",
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are a chargeback investigation assistant. "
                                'Respond only with JSON matching: {"explanation": string}. '
                                "The explanation must be 1-2 sentences, factual, and reference "
                                "only the details given. Do not include any other text."
                            ),
                        },
                        {"role": "user", "content": dispute_summary},
                    ],
                },
            )
            response.raise_for_status()
            payload = response.json()
        content = payload["message"]["content"]
        parsed = json.loads(content)
        explanation = parsed["explanation"]
        if not isinstance(explanation, str) or not explanation.strip():
            raise ValueError("Ollama returned an empty or non-string explanation")
        return explanation


class FakeExplanationClient:
    """Deterministic stand-in for tests that don't need a live LLM."""

    def __init__(
        self, *, fixed_explanation: str = "Delivery proof has not yet been provided."
    ) -> None:
        self._fixed_explanation = fixed_explanation

    async def generate_explanation(self, *, dispute_summary: str) -> str:
        return self._fixed_explanation
```

- [ ] **Step 3: Write `transaction-agent/tests/test_llm_client.py`**

```python
"""Unit tests for llm_client.py using httpx.MockTransport (no real network)."""

from __future__ import annotations

import json

import httpx
import pytest

from transaction_agent.llm_client import FakeExplanationClient, OllamaExplanationClient


async def test_fake_client_returns_fixed_explanation() -> None:
    client = FakeExplanationClient(fixed_explanation="Example explanation.")
    result = await client.generate_explanation(dispute_summary="x")
    assert result == "Example explanation."


async def test_ollama_client_sends_think_false_and_json_format() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={"message": {"content": '{"explanation": "Real explanation text."}'}},
        )

    client = OllamaExplanationClient(
        base_url="http://fake-ollama:11434",
        model="qwen3.5:latest",
        transport=httpx.MockTransport(handler),
    )
    result = await client.generate_explanation(dispute_summary="Customer disputes a charge.")

    assert result == "Real explanation text."
    body = captured["body"]
    assert isinstance(body, dict)
    assert body["model"] == "qwen3.5:latest"
    assert body["think"] is False
    assert body["format"] == "json"


async def test_ollama_client_rejects_malformed_json_content() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"message": {"content": "not json"}})

    client = OllamaExplanationClient(
        base_url="http://fake-ollama:11434",
        model="qwen3.5:latest",
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(json.JSONDecodeError):
        await client.generate_explanation(dispute_summary="x")


async def test_ollama_client_rejects_empty_explanation() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"message": {"content": '{"explanation": "   "}'}})

    client = OllamaExplanationClient(
        base_url="http://fake-ollama:11434",
        model="qwen3.5:latest",
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(ValueError, match="empty or non-string"):
        await client.generate_explanation(dispute_summary="x")
```

- [ ] **Step 4: Run the focused tests**

Run: `uv run pytest transaction-agent/tests/test_llm_client.py -v`
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add transaction-agent/src/transaction_agent/config.py transaction-agent/src/transaction_agent/llm_client.py transaction-agent/tests/test_llm_client.py
git commit -m "feat: add transaction-agent config and injectable explanation client"
```

---

### Task 3: `mcp_client.py` — in-process dispute-mcp-server client

**Files:**
- Create: `transaction-agent/src/transaction_agent/mcp_client.py`
- Create: `transaction-agent/tests/test_mcp_client.py`

**Interfaces:**
- Consumes: `dispute_mcp_server.main.mcp` (the real app object).
- Produces: `TransactionLookupError`, `get_case_and_transaction()` — consumed by `api.py`.

- [ ] **Step 1: Write `transaction-agent/src/transaction_agent/mcp_client.py`**

```python
"""In-process client for the existing dispute-mcp-server.

Reuses the same server object dispute-mcp-server's own tests use
(fastmcp.Client(mcp_app)) rather than inventing a new transport or
duplicating lookup logic -- dispute-mcp-server remains stdio-only.
"""

from __future__ import annotations

from fastmcp import Client
from fastmcp.exceptions import ToolError

from dispute_mcp_server.main import mcp as dispute_mcp_app


class TransactionLookupError(Exception):
    """Raised when the case/transaction cannot be found via dispute-mcp-server."""


async def get_case_and_transaction(
    case_id: str,
) -> tuple[dict[str, object], dict[str, object]]:
    """Fetch a case and its transaction from dispute-mcp-server.

    Returns (case_data, transaction_data) as plain dicts (the MCP tool
    result's structured content), or raises TransactionLookupError.
    """
    async with Client(dispute_mcp_app) as client:
        try:
            case_result = await client.call_tool("get_case", {"case_id": case_id})
        except ToolError as exc:
            raise TransactionLookupError(f"case not found: {case_id}") from exc
        case_data = case_result.structured_content
        if case_data is None:
            raise TransactionLookupError(f"case not found: {case_id}")

        transaction_id = case_data["transaction_id"]
        transaction_result = await client.call_tool(
            "get_transaction", {"transaction_id": transaction_id}
        )
        transaction_data = transaction_result.structured_content
        if transaction_data is None:
            raise TransactionLookupError(f"transaction not found: {transaction_id}")

    return case_data, transaction_data
```

- [ ] **Step 2: Write `transaction-agent/tests/test_mcp_client.py`**

```python
"""Tests for mcp_client.py, using the real dispute-mcp-server in-process.

Real seed data (from Prompt 3), no mocking needed -- this is a genuine
integration test.
"""

from __future__ import annotations

import pytest

from transaction_agent.mcp_client import TransactionLookupError, get_case_and_transaction


async def test_get_case_and_transaction_returns_real_seeded_data() -> None:
    case_data, transaction_data = await get_case_and_transaction("CASE-1001")
    assert case_data["case_id"] == "CASE-1001"
    assert case_data["customer_id"] == "CUST-3001"
    assert transaction_data["transaction_id"] == "TXN-2001"
    assert transaction_data["case_id"] == "CASE-1001"


async def test_get_case_and_transaction_unknown_case_raises() -> None:
    with pytest.raises(TransactionLookupError):
        await get_case_and_transaction("CASE-NOPE")
```

- [ ] **Step 3: Run the focused tests**

Run: `uv run pytest transaction-agent/tests/test_mcp_client.py -v`
Expected: both tests pass, using dispute-mcp-server's real seeded data.

- [ ] **Step 4: Commit**

```bash
git add transaction-agent/src/transaction_agent/mcp_client.py transaction-agent/tests/test_mcp_client.py
git commit -m "feat: add in-process dispute-mcp-server client"
```

---

### Task 4: `service.py` — AG-UI event sequence + A2UI envelope construction

**Files:**
- Create: `transaction-agent/src/transaction_agent/service.py`
- Create: `transaction-agent/tests/test_service.py`

**Interfaces:**
- Consumes: `ExplanationClient` from `llm_client.py`; `InvestigationAcceptedEvent`, `SpecialistStartedEvent`, `SpecialistFindingReceivedEvent`, `RecommendationProducedEvent`, `InvestigationCompletedEvent` from `chargeback_contracts.agui`; `A2UI_VERSION`, `A2uiEnvelope`, `DecisionCard`, `InvestigatorAction` from `chargeback_contracts.a2ui`; `RecommendationType` from `chargeback_contracts.recommendation`; `DisputeType`, `SkillId` from `chargeback_contracts.skills`; `ag_ui.core` (`CustomEvent`, `EventType`, `RunFinishedEvent`, `RunFinishedSuccessOutcome`, `RunStartedEvent`) and `ag_ui.encoder.EventEncoder`.
- Produces: `MOCK_RECOMMENDATION`, `run_investigation()` — consumed by `api.py`.

This task takes already-fetched `case_data`/`transaction_data` dicts rather than doing its own MCP lookup — the route handler in `api.py` fetches first (so an unknown case can return a clean 404 *before* the SSE stream starts, not mid-stream, which would corrupt the response).

- [ ] **Step 1: Write `transaction-agent/src/transaction_agent/service.py`**

```python
"""Core investigation run logic: builds the AG-UI event sequence and the
final A2UI decision-card envelope.

This is the reusable piece a future Orchestrator calls the same way this
prompt's endpoints do -- it has no dependency on how the run was
triggered, and does not look up data itself (the caller fetches
case/transaction data first, so a not-found case can be rejected before
any streaming response begins).
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime

from ag_ui.core import CustomEvent, EventType, RunFinishedEvent, RunFinishedSuccessOutcome, RunStartedEvent
from ag_ui.encoder import EventEncoder
from chargeback_contracts.a2ui import A2UI_VERSION, A2uiEnvelope, DecisionCard, InvestigatorAction
from chargeback_contracts.agui import (
    InvestigationAcceptedEvent,
    InvestigationCompletedEvent,
    RecommendationProducedEvent,
    SpecialistFindingReceivedEvent,
    SpecialistStartedEvent,
)
from chargeback_contracts.recommendation import RecommendationType
from chargeback_contracts.skills import DisputeType, SkillId

from transaction_agent.llm_client import ExplanationClient

MOCK_RECOMMENDATION = RecommendationType.REQUEST_MORE_EVIDENCE

_ENCODER = EventEncoder()


async def run_investigation(
    *,
    case_data: dict[str, object],
    transaction_data: dict[str, object],
    thread_id: str,
    run_id: str,
    explanation_client: ExplanationClient,
) -> AsyncIterator[str]:
    """Yield SSE-encoded AG-UI event strings for a single investigation run."""
    case_id = str(case_data["case_id"])
    dispute_type = DisputeType(case_data["dispute_type"])

    yield _ENCODER.encode(RunStartedEvent(thread_id=thread_id, run_id=run_id))

    accepted = InvestigationAcceptedEvent(
        investigation_id=case_id,
        case_id=case_id,
        run_id=run_id,
        occurred_at=datetime.now(UTC),
        dispute_type=dispute_type,
        requested_skill_ids=(SkillId.TRANSACTION_INVESTIGATION,),
    )
    yield _ENCODER.encode(
        CustomEvent(type=EventType.CUSTOM, name=accepted.event_name, value=accepted.model_dump(mode="json"))
    )

    started = SpecialistStartedEvent(
        investigation_id=case_id,
        case_id=case_id,
        run_id=run_id,
        occurred_at=datetime.now(UTC),
        agent_id="transaction-agent",
        skill_id=SkillId.TRANSACTION_INVESTIGATION,
    )
    yield _ENCODER.encode(
        CustomEvent(type=EventType.CUSTOM, name=started.event_name, value=started.model_dump(mode="json"))
    )

    finding_id = f"FIND-{uuid.uuid4().hex[:8]}"
    finding_received = SpecialistFindingReceivedEvent(
        investigation_id=case_id,
        case_id=case_id,
        run_id=run_id,
        occurred_at=datetime.now(UTC),
        agent_id="transaction-agent",
        skill_id=SkillId.TRANSACTION_INVESTIGATION,
        finding_id=finding_id,
    )
    yield _ENCODER.encode(
        CustomEvent(
            type=EventType.CUSTOM,
            name=finding_received.event_name,
            value=finding_received.model_dump(mode="json"),
        )
    )

    dispute_summary = (
        f"Customer disputes a {transaction_data['currency']} {transaction_data['amount']} "
        f"transaction ({dispute_type.value}). Transaction description: "
        f"{transaction_data['description']}."
    )
    explanation = await explanation_client.generate_explanation(dispute_summary=dispute_summary)

    recommendation_event = RecommendationProducedEvent(
        investigation_id=case_id,
        case_id=case_id,
        run_id=run_id,
        occurred_at=datetime.now(UTC),
        recommendation=MOCK_RECOMMENDATION,
    )
    yield _ENCODER.encode(
        CustomEvent(
            type=EventType.CUSTOM,
            name=recommendation_event.event_name,
            value=recommendation_event.model_dump(mode="json"),
        )
    )

    completed = InvestigationCompletedEvent(
        investigation_id=case_id,
        case_id=case_id,
        run_id=run_id,
        occurred_at=datetime.now(UTC),
        final_status="completed",
    )
    yield _ENCODER.encode(
        CustomEvent(type=EventType.CUSTOM, name=completed.event_name, value=completed.model_dump(mode="json"))
    )

    decision_card = DecisionCard(
        investigation_id=case_id,
        recommendation=MOCK_RECOMMENDATION,
        explanation=explanation,
    )
    envelope = A2uiEnvelope(
        version=A2UI_VERSION,
        surface_id=f"decision-{case_id}",
        investigation_id=case_id,
        components=(decision_card,),
        allowed_actions=(
            InvestigatorAction.APPROVE_RECOMMENDATION,
            InvestigatorAction.REJECT_RECOMMENDATION,
            InvestigatorAction.REQUEST_MORE_EVIDENCE,
        ),
        generated_at=datetime.now(UTC),
    )

    yield _ENCODER.encode(
        RunFinishedEvent(
            thread_id=thread_id,
            run_id=run_id,
            outcome=RunFinishedSuccessOutcome(type="success"),
            result=envelope.model_dump(mode="json"),
        )
    )
```

- [ ] **Step 2: Write `transaction-agent/tests/test_service.py`**

```python
"""Integration tests for service.py's run_investigation.

Uses real seeded CASE-1001/TXN-2001 data (fetched via mcp_client, itself
tested in Task 3) and FakeExplanationClient (no live LLM needed here --
the live LLM path is validated separately in test_llm_client_live_ollama.py).
"""

from __future__ import annotations

import json

import pytest
from ag_ui.core import EventType

from transaction_agent.llm_client import FakeExplanationClient
from transaction_agent.mcp_client import get_case_and_transaction
from transaction_agent.service import run_investigation


def _parse_sse_events(lines: list[str]) -> list[dict[str, object]]:
    events = []
    for line in lines:
        assert line.startswith("data: ")
        events.append(json.loads(line[len("data: ") :].strip()))
    return events


async def _run_for_case_1001(explanation_client: FakeExplanationClient) -> list[dict[str, object]]:
    case_data, transaction_data = await get_case_and_transaction("CASE-1001")
    lines = [
        line
        async for line in run_investigation(
            case_data=case_data,
            transaction_data=transaction_data,
            thread_id="thread-1",
            run_id="run-1",
            explanation_client=explanation_client,
        )
    ]
    return _parse_sse_events(lines)


async def test_run_investigation_yields_five_milestones_plus_run_bookends() -> None:
    events = await _run_for_case_1001(FakeExplanationClient())
    types = [e["type"] for e in events]
    assert types[0] == EventType.RUN_STARTED.value
    assert types[-1] == EventType.RUN_FINISHED.value

    custom_names = [e["name"] for e in events if e["type"] == EventType.CUSTOM.value]
    assert custom_names == [
        "investigation.accepted",
        "specialist.started",
        "specialist.finding_received",
        "recommendation.produced",
        "investigation.completed",
    ]


async def test_run_investigation_final_result_is_a_valid_decision_card_envelope() -> None:
    events = await _run_for_case_1001(
        FakeExplanationClient(fixed_explanation="Fixed test explanation.")
    )
    run_finished = events[-1]
    envelope = run_finished["result"]
    assert isinstance(envelope, dict)
    assert envelope["version"] == "0.9"
    assert envelope["investigation_id"] == "CASE-1001"
    card = envelope["components"][0]
    assert card["component_type"] == "decision_card"
    assert card["explanation"] == "Fixed test explanation."
    assert card["recommendation"] == "request_more_evidence"
    assert set(envelope["allowed_actions"]) == {
        "approve_recommendation",
        "reject_recommendation",
        "request_more_evidence",
    }


async def test_run_investigation_dispute_type_matches_seeded_case() -> None:
    events = await _run_for_case_1001(FakeExplanationClient())
    accepted = next(e for e in events if e.get("name") == "investigation.accepted")
    assert accepted["value"]["dispute_type"] == "goods_not_received"
```

- [ ] **Step 3: Run the focused tests**

Run: `uv run pytest transaction-agent/tests/test_service.py -v`
Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add transaction-agent/src/transaction_agent/service.py transaction-agent/tests/test_service.py
git commit -m "feat: add AG-UI event sequence and A2UI envelope construction"
```

---

### Task 5: `api.py` + `main.py` — FastAPI endpoints

**Files:**
- Create: `transaction-agent/src/transaction_agent/api.py`
- Create: `transaction-agent/src/transaction_agent/main.py`
- Create: `transaction-agent/tests/test_api.py`

**Interfaces:**
- Consumes: everything from Tasks 2-4; `chargeback_contracts.decisions.InvestigatorDecision`; `ag_ui.core.RunAgentInput`.
- Produces: `create_app()`, module-level `app` — used by `main.py` and, later, Docker/dev-server runs.

- [ ] **Step 1: Write `transaction-agent/src/transaction_agent/api.py`**

```python
"""FastAPI app: temporary intake, real AG-UI run, and investigator-action
endpoints.

/agent/run speaks the actual AG-UI wire protocol (RunAgentInput in,
SSE-encoded events out) -- confirmed during design research that ag_ui.core
models use camelCase JSON aliases (threadId, runId, forwardedProps), which
FastAPI/Pydantic handle natively. case_id travels in
input.forwarded_props["case_id"] since RunAgentInput has no case-specific
field of its own.
"""

from __future__ import annotations

import logging

from ag_ui.core import RunAgentInput
from chargeback_contracts.decisions import InvestigatorDecision
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from transaction_agent.config import load_settings
from transaction_agent.llm_client import ExplanationClient, OllamaExplanationClient
from transaction_agent.mcp_client import TransactionLookupError, get_case_and_transaction
from transaction_agent.service import run_investigation

logger = logging.getLogger("transaction_agent")

DEFAULT_INTAKE_CASE_ID = "CASE-1001"


class IntakeRequest(BaseModel):
    """Temporary intake payload -- the piece Prompt 6's Orchestrator replaces."""

    model_config = ConfigDict(extra="forbid")
    case_id: str = Field(min_length=1, default=DEFAULT_INTAKE_CASE_ID)


async def _lookup_or_404(case_id: str) -> tuple[dict[str, object], dict[str, object]]:
    try:
        return await get_case_and_transaction(case_id)
    except TransactionLookupError as exc:
        logger.warning("investigation lookup failed case_id=%s error=%s", case_id, type(exc).__name__)
        raise HTTPException(status_code=404, detail="case not found") from exc


def create_app(*, explanation_client: ExplanationClient | None = None) -> FastAPI:
    settings = load_settings()
    if explanation_client is None:
        explanation_client = OllamaExplanationClient(
            base_url=settings.ollama_base_url, model=settings.ollama_text_model
        )

    app = FastAPI(title=settings.service_name)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.post("/agent/run")
    async def agent_run(run_input: RunAgentInput) -> StreamingResponse:
        forwarded = run_input.forwarded_props if isinstance(run_input.forwarded_props, dict) else {}
        case_id = forwarded.get("case_id")
        if not isinstance(case_id, str) or not case_id.strip():
            raise HTTPException(status_code=422, detail="forwardedProps.case_id is required")

        case_data, transaction_data = await _lookup_or_404(case_id)
        generator = run_investigation(
            case_data=case_data,
            transaction_data=transaction_data,
            thread_id=run_input.thread_id,
            run_id=run_input.run_id,
            explanation_client=explanation_client,
        )
        return StreamingResponse(generator, media_type="text/event-stream")

    @app.post("/intake")
    async def intake(request: IntakeRequest) -> StreamingResponse:
        import uuid

        case_data, transaction_data = await _lookup_or_404(request.case_id)
        thread_id = f"thread-{uuid.uuid4().hex[:8]}"
        run_id = f"run-{uuid.uuid4().hex[:8]}"
        generator = run_investigation(
            case_data=case_data,
            transaction_data=transaction_data,
            thread_id=thread_id,
            run_id=run_id,
            explanation_client=explanation_client,
        )
        return StreamingResponse(generator, media_type="text/event-stream")

    @app.post("/actions/decision", status_code=204)
    async def actions_decision(decision: InvestigatorDecision) -> Response:
        logger.info(
            "investigator_decision case_id=%s action=%s investigator_id=%s",
            decision.case_id,
            decision.selected_action.value,
            decision.investigator_id,
        )
        return Response(status_code=204)

    return app


app = create_app()
```

- [ ] **Step 2: Write `transaction-agent/src/transaction_agent/main.py`**

```python
"""uvicorn entrypoint for transaction-agent."""

from __future__ import annotations

import uvicorn

from transaction_agent.api import app

__all__ = ["app", "main"]


def main() -> None:
    uvicorn.run(app, host="0.0.0.0", port=8010)


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Write `transaction-agent/tests/test_api.py`**

```python
"""Tests for the FastAPI app's three endpoints."""

from __future__ import annotations

import json
import logging

from fastapi.testclient import TestClient

from transaction_agent.api import create_app
from transaction_agent.llm_client import FakeExplanationClient


def _parse_sse(text: str) -> list[dict[str, object]]:
    events = []
    for raw_line in text.strip().split("\n\n"):
        if not raw_line.strip():
            continue
        assert raw_line.startswith("data: ")
        events.append(json.loads(raw_line[len("data: ") :]))
    return events


def test_agent_run_streams_five_milestones_for_seeded_case() -> None:
    app = create_app(explanation_client=FakeExplanationClient())
    client = TestClient(app)
    response = client.post(
        "/agent/run",
        json={
            "threadId": "thread-1",
            "runId": "run-1",
            "state": {},
            "messages": [],
            "tools": [],
            "context": [],
            "forwardedProps": {"case_id": "CASE-1001"},
        },
    )
    assert response.status_code == 200
    events = _parse_sse(response.text)
    custom_names = [e["name"] for e in events if e["type"] == "CUSTOM"]
    assert custom_names == [
        "investigation.accepted",
        "specialist.started",
        "specialist.finding_received",
        "recommendation.produced",
        "investigation.completed",
    ]


def test_agent_run_missing_case_id_returns_422() -> None:
    app = create_app(explanation_client=FakeExplanationClient())
    client = TestClient(app)
    response = client.post(
        "/agent/run",
        json={
            "threadId": "thread-1",
            "runId": "run-1",
            "state": {},
            "messages": [],
            "tools": [],
            "context": [],
            "forwardedProps": {},
        },
    )
    assert response.status_code == 422


def test_agent_run_unknown_case_returns_404() -> None:
    app = create_app(explanation_client=FakeExplanationClient())
    client = TestClient(app)
    response = client.post(
        "/agent/run",
        json={
            "threadId": "thread-1",
            "runId": "run-1",
            "state": {},
            "messages": [],
            "tools": [],
            "context": [],
            "forwardedProps": {"case_id": "CASE-NOPE"},
        },
    )
    assert response.status_code == 404


def test_intake_defaults_to_seeded_case_1001() -> None:
    app = create_app(explanation_client=FakeExplanationClient())
    client = TestClient(app)
    response = client.post("/intake", json={})
    assert response.status_code == 200
    events = _parse_sse(response.text)
    assert events[0]["type"] == "RUN_STARTED"


def test_actions_decision_returns_204_and_logs(caplog: object) -> None:
    app = create_app(explanation_client=FakeExplanationClient())
    client = TestClient(app)
    with caplog.at_level(logging.INFO, logger="transaction_agent"):  # type: ignore[attr-defined]
        response = client.post(
            "/actions/decision",
            json={
                "decision_id": "DEC-1",
                "investigation_id": "CASE-1001",
                "case_id": "CASE-1001",
                "investigator_id": "inv-jane",
                "selected_action": "approve_recommendation",
                "recommendation_shown": "request_more_evidence",
                "decided_at": "2026-01-01T00:00:00Z",
            },
        )
    assert response.status_code == 204
    assert any("investigator_decision" in r.message for r in caplog.records)  # type: ignore[attr-defined]


def test_actions_decision_rejects_unknown_field() -> None:
    app = create_app(explanation_client=FakeExplanationClient())
    client = TestClient(app)
    response = client.post(
        "/actions/decision",
        json={
            "decision_id": "DEC-1",
            "investigation_id": "CASE-1001",
            "case_id": "CASE-1001",
            "investigator_id": "inv-jane",
            "selected_action": "approve_recommendation",
            "recommendation_shown": "request_more_evidence",
            "decided_at": "2026-01-01T00:00:00Z",
            "unexpected_field": "nope",
        },
    )
    assert response.status_code == 422
```

Note: the `caplog: object` / `# type: ignore[attr-defined]` annotations are a placeholder-hedge for the real `pytest.LogCaptureFixture` type, exactly like the `info: object` hedge pattern from earlier prompts (Prompt 2's `ValidationInfo` cleanup) — if `uv run mypy` complains, fix these two occurrences by importing `pytest` and using `caplog: pytest.LogCaptureFixture` directly (it should just work; the hedge exists only in case an unusual import ordering issue surfaces, matching this repo's established practice of resolving such things for real rather than guessing in the plan).

- [ ] **Step 4: Run the focused tests**

Run: `uv run pytest transaction-agent/tests/test_api.py -v`
Expected: all tests pass. If mypy later flags the `caplog` hedge, fix it as noted above.

- [ ] **Step 5: Run the full transaction-agent suite**

Run: `uv run pytest transaction-agent/ -v`
Expected: every test file from Tasks 2-5 passes.

- [ ] **Step 6: Commit**

```bash
git add transaction-agent/src/transaction_agent/api.py transaction-agent/src/transaction_agent/main.py transaction-agent/tests/test_api.py
git commit -m "feat: add FastAPI endpoints (intake, agent/run, actions/decision)"
```

---

### Task 6: Real Ollama live-validation test

**Files:**
- Create: `transaction-agent/tests/test_llm_client_live_ollama.py`

**Interfaces:** none new.

- [ ] **Step 1: Write `transaction-agent/tests/test_llm_client_live_ollama.py`**

```python
"""Real, live validation against the host Ollama instance.

Skips (does not fail) if Ollama isn't reachable -- other machines running
this suite may not have it running. This environment does, so it will
actually execute here. This is the empirical "no <think> leakage /
structured JSON / reliable classification" gate Prompt 4 requires.
"""

from __future__ import annotations

import httpx
import pytest

from transaction_agent.config import load_settings
from transaction_agent.llm_client import OllamaExplanationClient


def _ollama_reachable(base_url: str) -> bool:
    try:
        response = httpx.get(f"{base_url}/api/tags", timeout=2.0)
        return response.status_code == 200
    except httpx.HTTPError:
        return False


async def test_real_ollama_produces_clean_explanation_with_no_think_leakage() -> None:
    settings = load_settings()
    if not _ollama_reachable(settings.ollama_base_url):
        pytest.skip(f"Ollama not reachable at {settings.ollama_base_url}")

    client = OllamaExplanationClient(
        base_url=settings.ollama_base_url, model=settings.ollama_text_model
    )
    explanation = await client.generate_explanation(
        dispute_summary=(
            "Customer disputes a USD 89.99 transaction claiming goods were "
            "never received. Delivery status shows not yet delivered."
        )
    )

    assert explanation.strip()
    assert "<think>" not in explanation
    assert "</think>" not in explanation
```

- [ ] **Step 2: Run it directly**

Run: `uv run pytest transaction-agent/tests/test_llm_client_live_ollama.py -v -s`
Expected: this environment has Ollama running, so the test should actually execute (not skip) and pass, printing a real explanation. If it skips, note in your report that `OLLAMA_BASE_URL` in this environment doesn't match `http://localhost:11434` (the default assumes `host.docker.internal`, which resolves inside containers but not on the bare host) — if so, re-run with `OLLAMA_BASE_URL=http://localhost:11434 uv run pytest transaction-agent/tests/test_llm_client_live_ollama.py -v -s` to get a real (not skipped) result, and report which URL actually worked.

- [ ] **Step 3: Commit**

```bash
git add transaction-agent/tests/test_llm_client_live_ollama.py
git commit -m "test: add real Ollama live-validation test (no think leakage)"
```

---

### Task 7: Remove smoke test; mypy/ruff cleanup for transaction-agent

**Files:**
- Delete: `transaction-agent/tests/test_import.py`
- Modify: root `pyproject.toml` (`[tool.mypy] exclude` — remove the `transaction-agent` line)

**Interfaces:** none new.

- [ ] **Step 1: Delete the old smoke test**

```bash
git rm transaction-agent/tests/test_import.py
```

- [ ] **Step 2: Remove `transaction-agent` from the mypy exclude list**

In root `pyproject.toml`, remove the `"^transaction-agent/tests/",` line from `[tool.mypy] exclude` (currently 8 entries; after this change, 7).

- [ ] **Step 3: Run mypy**

Run: `uv run mypy .`
Expected: clean, including `transaction-agent/src` and `transaction-agent/tests`. Fix any real error in the specific file it points to — do not weaken `strict = true`. This is where the `caplog` type hedge from Task 5 gets resolved for real if it surfaces.

- [ ] **Step 4: Run ruff and the full workspace test suite**

Run: `uv run ruff check .`, `uv run ruff format --check .`, `uv run pytest`
Expected: all clean; full workspace suite passes (including the Prompt 2 `contracts/` suite and Prompt 3 `dispute-mcp-server/` suite, both untouched by this batch so far).

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml transaction-agent/tests/test_import.py
git commit -m "chore: remove transaction-agent Prompt-1 smoke test, strict-check it in mypy"
```

(Adjust `git add` if any mypy fix touched other files, per the same pattern used in Prompts 2 and 3.)

---

### Task 8: Frontend — types, agent client, EventStream, InvestigationTimeline

**Files:**
- Create: `investigator-ui/src/types.ts`
- Create: `investigator-ui/src/lib/agent.ts`
- Create: `investigator-ui/src/components/EventStream.tsx`
- Create: `investigator-ui/src/components/InvestigationTimeline.tsx`

**Interfaces:**
- Produces: `TimelineMilestone`, `StreamEvent`, `DecisionCardData` types; `createTransactionAgentClient()`, `ACTIONS_URL`; `EventStream`, `InvestigationTimeline` components — consumed by `App.tsx` (Task 10) and `DecisionCard.tsx` (Task 9).

- [ ] **Step 1: Write `investigator-ui/src/types.ts`**

```typescript
export interface TimelineMilestone {
  key: string;
  label: string;
  status: "pending" | "done";
}

export interface StreamEvent {
  name: string;
  occurredAt: string;
  raw: Record<string, unknown>;
}

export interface DecisionCardData {
  investigationId: string;
  recommendation: string;
  explanation: string;
  allowedActions: string[];
}
```

- [ ] **Step 2: Write `investigator-ui/src/lib/agent.ts`**

```typescript
import { HttpAgent } from "@ag-ui/client";

const BACKEND_URL =
  (import.meta.env.VITE_TRANSACTION_AGENT_URL as string | undefined) ??
  "http://localhost:8010";

export function createTransactionAgentClient(): HttpAgent {
  return new HttpAgent({ url: `${BACKEND_URL}/agent/run` });
}

export const ACTIONS_URL = `${BACKEND_URL}/actions/decision`;
```

- [ ] **Step 3: Write `investigator-ui/src/components/EventStream.tsx`**

```tsx
import type { StreamEvent } from "../types";

interface EventStreamProps {
  events: StreamEvent[];
}

export function EventStream({ events }: EventStreamProps) {
  return (
    <div className="flex flex-col gap-1 rounded border border-slate-800 p-3 text-sm">
      {events.length === 0 && <p className="text-slate-500">No events yet.</p>}
      {events.map((event, index) => (
        <div key={`${event.name}-${index}`} className="flex justify-between gap-4 text-slate-400">
          <span className="font-mono">{event.name}</span>
          <span>{event.occurredAt}</span>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 4: Write `investigator-ui/src/components/InvestigationTimeline.tsx`**

```tsx
import type { TimelineMilestone } from "../types";

const MILESTONE_ORDER: { key: string; label: string }[] = [
  { key: "investigation.accepted", label: "Investigation Started" },
  { key: "specialist.started", label: "MCP Lookup" },
  { key: "specialist.finding_received", label: "Transaction Loaded" },
  { key: "recommendation.produced", label: "Recommendation Ready" },
  { key: "investigation.completed", label: "Investigation Completed" },
];

interface InvestigationTimelineProps {
  seenEventNames: Set<string>;
}

export function InvestigationTimeline({ seenEventNames }: InvestigationTimelineProps) {
  const milestones: TimelineMilestone[] = MILESTONE_ORDER.map(({ key, label }) => ({
    key,
    label,
    status: seenEventNames.has(key) ? "done" : "pending",
  }));

  return (
    <ol className="flex flex-col gap-2">
      {milestones.map((milestone) => (
        <li key={milestone.key} className="flex items-center gap-2">
          <span
            className={
              milestone.status === "done"
                ? "h-2 w-2 rounded-full bg-emerald-400"
                : "h-2 w-2 rounded-full bg-slate-600"
            }
          />
          <span className={milestone.status === "done" ? "text-slate-100" : "text-slate-500"}>
            {milestone.label}
          </span>
        </li>
      ))}
    </ol>
  );
}
```

- [ ] **Step 5: Verify it compiles**

Run: `cd investigator-ui && npx tsc -b --noEmit` (or `npm run build` if this fails standalone due to project references — use whichever actually works, note which)
Expected: no TypeScript errors. Fix any real type error in the specific file.

- [ ] **Step 6: Commit**

```bash
git add investigator-ui/src/types.ts investigator-ui/src/lib/agent.ts investigator-ui/src/components/EventStream.tsx investigator-ui/src/components/InvestigationTimeline.tsx
git commit -m "feat: add AG-UI client, EventStream, and InvestigationTimeline components"
```

---

### Task 9: Frontend — RecommendationCard, DecisionCard

**Files:**
- Create: `investigator-ui/src/components/RecommendationCard.tsx`
- Create: `investigator-ui/src/components/DecisionCard.tsx`

**Interfaces:**
- Consumes: `DecisionCardData` from `types.ts`, `ACTIONS_URL` from `lib/agent.ts`.
- Produces: `RecommendationCard`, `DecisionCard` components — consumed by `App.tsx` (Task 10).

- [ ] **Step 1: Write `investigator-ui/src/components/RecommendationCard.tsx`**

```tsx
interface RecommendationCardProps {
  recommendation: string | null;
}

export function RecommendationCard({ recommendation }: RecommendationCardProps) {
  if (!recommendation) {
    return <p className="text-slate-500">Awaiting recommendation...</p>;
  }
  return (
    <div className="rounded border border-slate-800 p-3">
      <p className="text-xs uppercase tracking-wide text-slate-500">Recommendation</p>
      <p className="text-lg font-semibold text-slate-100">{recommendation.replaceAll("_", " ")}</p>
    </div>
  );
}
```

- [ ] **Step 2: Write `investigator-ui/src/components/DecisionCard.tsx`**

```tsx
import { useState } from "react";
import type { DecisionCardData } from "../types";
import { ACTIONS_URL } from "../lib/agent";

interface DecisionCardProps {
  data: DecisionCardData | null;
  investigatorId: string;
}

export function DecisionCard({ data, investigatorId }: DecisionCardProps) {
  const [submittedAction, setSubmittedAction] = useState<string | null>(null);

  if (!data) {
    return <p className="text-slate-500">Awaiting decision card...</p>;
  }

  async function submit(action: string): Promise<void> {
    await fetch(ACTIONS_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        decision_id: `DEC-${Date.now()}`,
        investigation_id: data!.investigationId,
        case_id: data!.investigationId,
        investigator_id: investigatorId,
        selected_action: action,
        recommendation_shown: data!.recommendation,
        decided_at: new Date().toISOString(),
      }),
    });
    setSubmittedAction(action);
  }

  return (
    <div className="rounded border border-slate-800 p-4">
      <p className="text-xs uppercase tracking-wide text-slate-500">Decision</p>
      <p className="mt-1 text-slate-100">{data.explanation}</p>
      <div className="mt-3 flex gap-2">
        {data.allowedActions.map((action) => (
          <button
            key={action}
            type="button"
            disabled={submittedAction !== null}
            onClick={() => {
              void submit(action);
            }}
            className="rounded bg-slate-800 px-3 py-1 text-sm text-slate-100 disabled:opacity-40"
          >
            {action.replaceAll("_", " ")}
          </button>
        ))}
      </div>
      {submittedAction && (
        <p className="mt-2 text-sm text-emerald-400">Recorded: {submittedAction.replaceAll("_", " ")}</p>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Verify it compiles**

Run: `cd investigator-ui && npx tsc -b --noEmit`
Expected: no TypeScript errors.

- [ ] **Step 4: Commit**

```bash
git add investigator-ui/src/components/RecommendationCard.tsx investigator-ui/src/components/DecisionCard.tsx
git commit -m "feat: add RecommendationCard and DecisionCard components"
```

---

### Task 10: Frontend — wire `App.tsx`; verify the build

**Files:**
- Modify: `investigator-ui/src/App.tsx`

**Interfaces:**
- Consumes: everything from Tasks 8-9.

- [ ] **Step 1: Replace `investigator-ui/src/App.tsx`**

Current content is the Prompt 1 placeholder shell. Replace entirely with:

```tsx
import { useCallback, useState } from "react";
import { DecisionCard } from "./components/DecisionCard";
import { EventStream } from "./components/EventStream";
import { InvestigationTimeline } from "./components/InvestigationTimeline";
import { RecommendationCard } from "./components/RecommendationCard";
import { createTransactionAgentClient } from "./lib/agent";
import type { DecisionCardData, StreamEvent } from "./types";

interface CustomEventLike {
  type: string;
  name?: string;
  value?: Record<string, unknown>;
}

interface RunFinishedLike {
  result?: {
    investigation_id?: string;
    allowed_actions?: string[];
    components?: Array<Record<string, unknown>>;
  };
}

function App() {
  const [events, setEvents] = useState<StreamEvent[]>([]);
  const [recommendation, setRecommendation] = useState<string | null>(null);
  const [decisionCard, setDecisionCard] = useState<DecisionCardData | null>(null);
  const [running, setRunning] = useState(false);

  const startInvestigation = useCallback(async () => {
    setEvents([]);
    setRecommendation(null);
    setDecisionCard(null);
    setRunning(true);

    const agent = createTransactionAgentClient();
    await agent.runAgent(
      { forwardedProps: { case_id: "CASE-1001" } },
      {
        onEvent: ({ event }) => {
          const customEvent = event as unknown as CustomEventLike;
          if (customEvent.type === "CUSTOM" && customEvent.name && customEvent.value) {
            setEvents((prev) => [
              ...prev,
              {
                name: customEvent.name!,
                occurredAt: String(customEvent.value!.occurred_at ?? ""),
                raw: customEvent.value!,
              },
            ]);
            if (customEvent.name === "recommendation.produced") {
              setRecommendation(String(customEvent.value.recommendation));
            }
          }
        },
        onRunFinishedEvent: ({ event }) => {
          const result = (event as unknown as RunFinishedLike).result;
          const card = result?.components?.find((c) => c.component_type === "decision_card");
          if (result && card) {
            setDecisionCard({
              investigationId: String(result.investigation_id),
              recommendation: String(card.recommendation),
              explanation: String(card.explanation),
              allowedActions: result.allowed_actions ?? [],
            });
          }
          setRunning(false);
        },
      },
    );
  }, []);

  const seenEventNames = new Set(events.map((event) => event.name));

  return (
    <div className="min-h-screen bg-slate-950 p-8 text-slate-100">
      <div className="mx-auto max-w-2xl">
        <h1 className="text-3xl font-semibold">Agentic Chargeback Investigator</h1>
        <p className="mt-2 text-slate-400">
          Vertical-slice spike: intake harness &rarr; Transaction Agent &rarr; AG-UI &rarr; A2UI.
        </p>
        <button
          type="button"
          onClick={() => {
            void startInvestigation();
          }}
          disabled={running}
          className="mt-4 rounded bg-slate-800 px-4 py-2 text-sm disabled:opacity-40"
        >
          {running ? "Investigating..." : "Start Investigation (CASE-1001)"}
        </button>

        <div className="mt-6 grid gap-6">
          <section>
            <h2 className="mb-2 text-sm uppercase tracking-wide text-slate-500">Timeline</h2>
            <InvestigationTimeline seenEventNames={seenEventNames} />
          </section>
          <section>
            <h2 className="mb-2 text-sm uppercase tracking-wide text-slate-500">Event Stream</h2>
            <EventStream events={events} />
          </section>
          <section>
            <h2 className="mb-2 text-sm uppercase tracking-wide text-slate-500">Recommendation</h2>
            <RecommendationCard recommendation={recommendation} />
          </section>
          <section>
            <h2 className="mb-2 text-sm uppercase tracking-wide text-slate-500">Decision</h2>
            <DecisionCard data={decisionCard} investigatorId="inv-demo" />
          </section>
        </div>
      </div>
    </div>
  );
}

export default App;
```

- [ ] **Step 2: Build**

Run: `cd investigator-ui && npm run build`
Expected: succeeds. Fix any real TypeScript error in the specific file it points to (e.g. the `@ag-ui/client` `AgentSubscriber` callback signatures were confirmed during design research to be `({ event }) => ...`/`MaybePromise<...>` — if the actual installed version's exact callback shape differs subtly from what's written here, adjust to match the real type error, don't guess).

- [ ] **Step 3: Commit**

```bash
git add investigator-ui/src/App.tsx
git commit -m "feat: wire investigator-ui to the transaction-agent AG-UI endpoint"
```

---

### Task 11: Real browser verification (Playwright)

**Files:** none created; verification only.

**Interfaces:**
- Consumes: the running `transaction-agent` backend (Task 5-7) and `investigator-ui` dev server (Tasks 8-10).

- [ ] **Step 1: Start the backend**

Run (background): `uv run --package transaction-agent uvicorn transaction_agent.api:app --host 0.0.0.0 --port 8010`

- [ ] **Step 2: Start the frontend dev server**

Run (background): `cd investigator-ui && npm run dev`
Note the port Vite reports (typically 5173).

- [ ] **Step 3: Drive it with Playwright**

Navigate to the dev server URL, click "Start Investigation (CASE-1001)", wait for the timeline/event stream/recommendation/decision card to populate, click one of the three decision buttons ("Approve"/"Reject"/"Request More Evidence"), and confirm the "Recorded: ..." confirmation text appears. Take a screenshot at the point where the decision card is fully rendered (before clicking) and one after clicking a button.

This is the acceptance-criteria-defining check ("Full round-trip demonstrated," "AG-UI and A2UI interoperate," "UI built from reusable components") — do this for real using the Playwright browser tools available in this session, not just `npm run build`.

- [ ] **Step 4: Check the backend logs**

Confirm the backend process's stdout shows the `investigator_decision` log line from Task 5's `/actions/decision` handler, proving the action round-trip actually reached the backend (not just the frontend's optimistic UI state).

- [ ] **Step 5: Stop both servers**

Stop the backend and frontend dev-server processes started in Steps 1-2 (they were for verification only, not meant to keep running).

- [ ] **Step 6: No commit for this task** — it's a verification step; report the screenshots/observations in your final report.

---

### Task 12: Rerun Prompt 2 contract tests; confirm business contracts unchanged

**Files:** none created; verification only.

**Interfaces:** none.

- [ ] **Step 1: Run the full contracts suite**

Run: `uv run pytest contracts/ -v`
Expected: all tests still pass (this batch should not have touched anything under `contracts/src/chargeback_contracts/`).

- [ ] **Step 2: Confirm no business contract was touched**

Run: `git diff --stat <task-1-base-sha>..HEAD -- contracts/src/chargeback_contracts/`
Expected: empty output — nothing in `contracts/` changed in this batch, confirming the design decision that all 5 AG-UI stream milestones fit existing contracts with no refinement needed.

- [ ] **Step 3: If Step 1 or 2 reveals contracts DID need to change**

(Not expected, but if some earlier task in this plan found a genuine AG-UI payload gap and modified `agui.py`): confirm only `agui.py` changed, not `dispute.py`/`findings.py`/`recommendation.py`/`records.py`, and that this was reported as a deviation in that task's own report.

---

### Task 13: README update

**Files:**
- Modify: `README.md`

**Interfaces:** none.

- [ ] **Step 1: Insert a new section after "Dispute MCP Server"**

```markdown
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
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add vertical slice section to README"
```

---

### Task 14: Full verification run

**Files:** none created; verification only.

**Interfaces:**
- Consumes: everything from Tasks 1-13.

- [ ] **Step 1: Run `make verify` from the repo root**

Run: `make verify`
Expected: Ruff format-check, Ruff lint, strict Mypy, the full pytest suite (including the real-Ollama test, which should actually execute — not skip — in this environment), and the `investigator-ui` production build all pass.

- [ ] **Step 2: If anything fails**

Fix the specific file the error points to. Do not weaken strictness anywhere. Re-run `make verify` until clean. Commit each fix separately.

- [ ] **Step 3: Confirm working tree is clean and pre-existing files untouched**

Run: `git status --short`
Expected: no output. Also confirm no commit in this batch touched `.gitignore` or `tmp/`.

---

### Task 15: Consolidated changelog commit

**Files:**
- Modify: `docs/COMMIT_LOG.md`

**Interfaces:**
- Consumes: the full commit history produced by Tasks 1-14.

Per the user's explicit instruction: the changelog is written and
committed **once**, covering every individual commit — not per-commit.
Per the lesson from Prompt 1, **this task should be performed directly by
the controller**, not delegated to a fresh subagent.

- [ ] **Step 1: List this batch's commits for reference**

Run: `git log --oneline <task-1-base-sha>..HEAD`

- [ ] **Step 2: Prepend entries to `docs/COMMIT_LOG.md`**

Add one entry per logical unit of work (dependencies + model-tag fix;
config/llm_client; mcp_client; service; api/main; live-Ollama test; mypy
cleanup; each frontend task; README; any fixes from Task 14), most recent
first, above the existing top entry. Use today's actual date and the real
filenames touched. Include the Task 11 Playwright verification's outcome
as its own entry (documentation of what was proven, even though it has no
commit of its own).

- [ ] **Step 3: Commit**

```bash
git add docs/COMMIT_LOG.md
git commit -m "docs: log Prompt 4 vertical slice batch"
```

---

## Self-Review Notes

- **Spec coverage:** Transaction Agent (Tasks 1-7), AG-UI streaming (Task 4-5, real protocol types), investigator-ui integration (Tasks 8-10), A2UI decision screen (`DecisionCard`, Task 9), backend callback endpoint (`/actions/decision`, Task 5), host Ollama integration (Tasks 2, 6), intake harness (`/intake`, Task 5) — every scope item maps to a task.
- **No placeholders:** every step has complete, real code, verified against actual installed package APIs (ag_ui.core field names/aliases, @ag-ui/client's real .d.ts, fastmcp's Client/ToolError/structured_content behavior already proven in Prompt 3).
- **No business logic:** the recommendation is a hardcoded constant (`MOCK_RECOMMENDATION`); no dispute-type-to-outcome logic anywhere.
- **No duplicate contracts:** confirmed by design that all 5 AG-UI milestones fit existing Prompt 2 payloads; Task 12 explicitly verifies nothing in `contracts/` changed.
- **Reusable vs. temporary boundary:** `/intake` is the only piece explicitly marked temporary; `/agent/run`, `/actions/decision`, and all 4 UI components are designed to be extended, not replaced, by later prompts.
