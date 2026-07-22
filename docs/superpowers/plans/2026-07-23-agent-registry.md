# Agent Registry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `agent-registry`, a standalone FastAPI service providing lease-based runtime capability discovery — registration, renewal, deregistration, discovery, listing, health — backed entirely by an in-memory, process-lifetime repository.

**Architecture:** `config.py` (env-backed settings) → `clock.py` (injectable time source) → `models.py` (registration/record shapes, reusing `chargeback_contracts.skills.SkillId`) → `logging.py` (explicit-handler structured logging) → `repository.py` (in-memory, `asyncio.Lock`-guarded store) → `service.py` (register/renew/deregister/discover/sweep_expired policy layer) → `lease_manager.py` (background sweep task lifecycle) → `api.py` (FastAPI endpoints + lifespan wiring) → `main.py` (uvicorn entrypoint).

**Tech Stack:** Python 3.13, FastAPI 0.139.2, uvicorn 0.51.0, httpx 0.28.1 (test client only), Pydantic v2, `chargeback_contracts` (workspace dependency), pytest + pytest-asyncio (already configured at the workspace root).

## Global Constraints

- Reuse `chargeback_contracts.skills.SkillId` for every capability reference — never define a new capability enum.
- No database; state lives only in an in-memory `AgentRepository` for the life of the process.
- Do NOT implement: Orchestrator, A2A, Customer History Agent, Merchant Evidence Agent, Policy Agent, Duplicate Transaction Agent, RAG, recommendation rules, or any Transaction-Agent-to-Registry integration.
- Do NOT modify `transaction-agent/`, `dispute-mcp-server/`, or `investigator-ui/` in this batch — Task 11 explicitly verifies this.
- Do NOT touch `docs/COMMIT_LOG.md` until the final task (controller-authored, not delegated).
- Do NOT touch `.gitignore` or `tmp/`.
- Lease expiry must be tested deterministically via an injectable `Clock` (`FakeClock`) — no test may rely on real `sleep()` to observe expiry.
- All repository mutations go through an `asyncio.Lock` — concurrency must be demonstrated with a real `asyncio.gather` test, not asserted by inspection.
- Logging follows `dispute-mcp-server/src/dispute_mcp_server/logging.py`'s pattern exactly: an explicit `logger.setLevel(...)` + manually-attached `StreamHandler`, never `logging.basicConfig` (Prompt 4 found that `logging.basicConfig` is easy to forget to call at all; the explicit-handler pattern has no such gap).
- Commit file-by-file per the project's git-commit skill; update `docs/COMMIT_LOG.md` exactly once, at the end, summarizing the whole batch.

---

### Task 1: Dependencies and configuration

**Files:**
- Modify: `agent-registry/pyproject.toml`
- Modify: `pyproject.toml` (root — mypy exclude list)
- Create: `agent-registry/src/agent_registry/config.py`
- Test: `agent-registry/tests/test_config.py`

**Interfaces:**
- Produces: `Settings` (frozen dataclass: `service_name: str`, `lease_duration_seconds: float`, `lease_sweep_interval_seconds: float`, `log_level: str`), `load_settings() -> Settings`.

- [ ] **Step 1: Update `agent-registry/pyproject.toml`**

Replace its entire contents with:

```toml
[project]
name = "agent-registry"
version = "0.1.0"
description = "Lease-based agent and capability discovery"
requires-python = ">=3.13"
dependencies = [
    "fastapi==0.139.2",
    "uvicorn[standard]==0.51.0",
    "httpx==0.28.1",
    "contracts",
]

[tool.uv.sources]
contracts = { workspace = true }

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/agent_registry"]
```

(`httpx` is required by FastAPI's `TestClient`, not for any outbound call this service makes — matching `transaction-agent`'s own `pyproject.toml`, which lists it as a plain dependency the same way.)

- [ ] **Step 2: Run `uv sync --all-packages` and confirm it succeeds**

Run: `uv sync --all-packages`
Expected: resolves cleanly, `agent-registry` now depends on `contracts` as an editable workspace member.

- [ ] **Step 3: Update the root `pyproject.toml` mypy exclude list**

The current block (root `pyproject.toml`, `[tool.mypy]` section) reads:

```toml
# Temporary technical debt (introduced in Prompt 1, narrowed in Prompt 2):
# these 9 packages still have only a single import-smoke `tests/test_import.py`
# with no `__init__.py`, so mypy's duplicate-module-name detector would
# otherwise refuse to run (all 9 files share the bare module name
# `test_import`). `contracts/tests/` is intentionally NOT excluded — it now
# has real test logic and must be strict-mypy-checked like production code.
# Remove each package's line below once that package gains real tests (or
# at minimum a `tests/__init__.py`), one line at a time, rather than in one
# batch — do not remove this comment until the list is empty.
exclude = [
    "^orchestrator-agent/tests/",
    "^customer-history-agent/tests/",
    "^merchant-evidence-agent/tests/",
    "^policy-agent/tests/",
    "^duplicate-transaction-agent/tests/",
    "^agent-registry/tests/",
    "^knowledge-ingestor/tests/",
]
```

Replace it with (removing the `agent-registry` line — this package is gaining real tests in this batch — and correcting the stale count in the comment, which drifted from 9 to 7 over Prompts 2 and 4 without the prose being updated):

```toml
# Temporary technical debt (introduced in Prompt 1, narrowed in Prompts 2, 4, 5):
# these 6 packages still have only a single import-smoke `tests/test_import.py`
# with no `__init__.py`, so mypy's duplicate-module-name detector would
# otherwise refuse to run (all 6 files share the bare module name
# `test_import`). `contracts/tests/` is intentionally NOT excluded — it now
# has real test logic and must be strict-mypy-checked like production code.
# Remove each package's line below once that package gains real tests (or
# at minimum a `tests/__init__.py`), one line at a time, rather than in one
# batch — do not remove this comment until the list is empty.
exclude = [
    "^orchestrator-agent/tests/",
    "^customer-history-agent/tests/",
    "^merchant-evidence-agent/tests/",
    "^policy-agent/tests/",
    "^duplicate-transaction-agent/tests/",
    "^knowledge-ingestor/tests/",
]
```

- [ ] **Step 4: Delete the now-superseded smoke test**

Run: `rm agent-registry/tests/test_import.py`

- [ ] **Step 5: Write the failing test**

Create `agent-registry/tests/test_config.py`:

```python
"""Tests for agent_registry.config."""

from __future__ import annotations

from agent_registry.config import load_settings


def test_load_settings_uses_documented_defaults(monkeypatch) -> None:
    monkeypatch.delenv("REGISTRY_SERVICE_NAME", raising=False)
    monkeypatch.delenv("LEASE_DURATION_SECONDS", raising=False)
    monkeypatch.delenv("LEASE_SWEEP_INTERVAL_SECONDS", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)

    settings = load_settings()

    assert settings.service_name == "agent-registry"
    assert settings.lease_duration_seconds == 30.0
    assert settings.lease_sweep_interval_seconds == 10.0
    assert settings.log_level == "INFO"


def test_load_settings_reads_environment_overrides(monkeypatch) -> None:
    monkeypatch.setenv("REGISTRY_SERVICE_NAME", "registry-test")
    monkeypatch.setenv("LEASE_DURATION_SECONDS", "5")
    monkeypatch.setenv("LEASE_SWEEP_INTERVAL_SECONDS", "1")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    settings = load_settings()

    assert settings.service_name == "registry-test"
    assert settings.lease_duration_seconds == 5.0
    assert settings.lease_sweep_interval_seconds == 1.0
    assert settings.log_level == "DEBUG"
```

- [ ] **Step 6: Run test to verify it fails**

Run: `uv run pytest agent-registry/tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agent_registry.config'`

- [ ] **Step 7: Write the implementation**

Create `agent-registry/src/agent_registry/config.py`:

```python
"""Environment-backed settings for agent-registry."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    service_name: str
    lease_duration_seconds: float
    lease_sweep_interval_seconds: float
    log_level: str


def load_settings() -> Settings:
    return Settings(
        service_name=os.environ.get("REGISTRY_SERVICE_NAME", "agent-registry"),
        lease_duration_seconds=float(os.environ.get("LEASE_DURATION_SECONDS", "30")),
        lease_sweep_interval_seconds=float(
            os.environ.get("LEASE_SWEEP_INTERVAL_SECONDS", "10")
        ),
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
    )
```

- [ ] **Step 8: Run test to verify it passes**

Run: `uv run pytest agent-registry/tests/test_config.py -v`
Expected: `2 passed`

- [ ] **Step 9: Commit**

```bash
git add agent-registry/pyproject.toml agent-registry/tests/test_config.py \
  agent-registry/src/agent_registry/config.py pyproject.toml uv.lock
git rm agent-registry/tests/test_import.py
git commit -m "feat: add agent-registry dependencies and config"
```

---

### Task 2: Injectable clock

**Files:**
- Create: `agent-registry/src/agent_registry/clock.py`
- Test: `agent-registry/tests/test_clock.py`

**Interfaces:**
- Produces: `Clock` (Protocol: `now(self) -> datetime`), `SystemClock` (real implementation), `FakeClock(start: datetime | None = None)` with `.now()` and `.advance(seconds: float) -> None`.

- [ ] **Step 1: Write the failing test**

Create `agent-registry/tests/test_clock.py`:

```python
"""Tests for agent_registry.clock."""

from __future__ import annotations

from datetime import UTC, datetime

from agent_registry.clock import FakeClock, SystemClock


def test_system_clock_returns_timezone_aware_utc_now() -> None:
    clock = SystemClock()
    result = clock.now()
    assert result.tzinfo is not None
    assert result.utcoffset().total_seconds() == 0


def test_fake_clock_starts_at_a_fixed_point_by_default() -> None:
    clock = FakeClock()
    assert clock.now() == datetime(2026, 1, 1, tzinfo=UTC)


def test_fake_clock_can_start_at_an_explicit_point() -> None:
    start = datetime(2020, 6, 15, 12, 0, 0, tzinfo=UTC)
    clock = FakeClock(start=start)
    assert clock.now() == start


def test_fake_clock_advance_moves_time_forward_by_exact_seconds() -> None:
    clock = FakeClock(start=datetime(2026, 1, 1, tzinfo=UTC))
    clock.advance(90)
    assert clock.now() == datetime(2026, 1, 1, 0, 1, 30, tzinfo=UTC)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest agent-registry/tests/test_clock.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agent_registry.clock'`

- [ ] **Step 3: Write the implementation**

Create `agent-registry/src/agent_registry/clock.py`:

```python
"""Injectable clock so lease-expiry logic is deterministically testable.

Real lease expiry would otherwise require tests to sleep for as long as
the lease duration. `FakeClock` lets tests advance time instantly instead.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime: ...


class SystemClock:
    """Real wall-clock time, used by the running service."""

    def now(self) -> datetime:
        return datetime.now(UTC)


class FakeClock:
    """Test-controlled clock that only moves when explicitly advanced."""

    def __init__(self, *, start: datetime | None = None) -> None:
        self._current = start if start is not None else datetime(2026, 1, 1, tzinfo=UTC)

    def now(self) -> datetime:
        return self._current

    def advance(self, seconds: float) -> None:
        self._current = self._current + timedelta(seconds=seconds)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest agent-registry/tests/test_clock.py -v`
Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add agent-registry/src/agent_registry/clock.py agent-registry/tests/test_clock.py
git commit -m "feat: add injectable Clock for deterministic lease-expiry testing"
```

---

### Task 3: Registration and record models

**Files:**
- Create: `agent-registry/src/agent_registry/models.py`
- Test: `agent-registry/tests/test_models.py`

**Interfaces:**
- Consumes: `chargeback_contracts.skills.SkillId`.
- Produces: `AgentStatus` (StrEnum: `ACTIVE = "active"`), `AgentRegistration` (Pydantic model: `agent_id: str`, `agent_name: str`, `endpoint: str`, `version: str`, `capabilities: tuple[SkillId, ...]`), `AgentRecord` (Pydantic model: all `AgentRegistration` fields plus `status: AgentStatus`, `lease_expires_at: datetime`).

- [ ] **Step 1: Write the failing test**

Create `agent-registry/tests/test_models.py`:

```python
"""Tests for agent_registry.models."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from agent_registry.models import AgentRecord, AgentRegistration, AgentStatus
from chargeback_contracts.skills import SkillId


def test_agent_registration_accepts_valid_payload() -> None:
    registration = AgentRegistration(
        agent_id="transaction-agent-1",
        agent_name="Transaction Agent",
        endpoint="http://localhost:8010",
        version="0.1.0",
        capabilities=[SkillId.TRANSACTION_INVESTIGATION],
    )
    assert registration.agent_id == "transaction-agent-1"


def test_agent_registration_capabilities_reuse_the_shared_skill_id_enum() -> None:
    registration = AgentRegistration(
        agent_id="transaction-agent-1",
        agent_name="Transaction Agent",
        endpoint="http://localhost:8010",
        version="0.1.0",
        capabilities=[SkillId.TRANSACTION_INVESTIGATION],
    )
    assert registration.capabilities[0] is SkillId.TRANSACTION_INVESTIGATION
    assert registration.capabilities[0] == "transaction-investigation"


def test_agent_registration_requires_at_least_one_capability() -> None:
    with pytest.raises(ValidationError):
        AgentRegistration(
            agent_id="agent-1",
            agent_name="Agent",
            endpoint="http://localhost:9000",
            version="0.1.0",
            capabilities=[],
        )


def test_agent_registration_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError):
        AgentRegistration(
            agent_id="agent-1",
            agent_name="Agent",
            endpoint="http://localhost:9000",
            version="0.1.0",
            capabilities=[SkillId.TRANSACTION_INVESTIGATION],
            unexpected="nope",
        )


def test_agent_record_round_trips_through_json() -> None:
    record = AgentRecord(
        agent_id="agent-1",
        agent_name="Agent",
        endpoint="http://localhost:9000",
        version="0.1.0",
        capabilities=(SkillId.TRANSACTION_INVESTIGATION,),
        status=AgentStatus.ACTIVE,
        lease_expires_at=datetime(2026, 1, 1, 0, 0, 30, tzinfo=UTC),
    )
    payload = json.loads(record.model_dump_json())
    restored = AgentRecord.model_validate(payload)
    assert restored == record
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest agent-registry/tests/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agent_registry.models'`

- [ ] **Step 3: Write the implementation**

Create `agent-registry/src/agent_registry/models.py`:

```python
"""Agent Registry's own registration/record models.

Capabilities reuse `chargeback_contracts.skills.SkillId` -- this module
defines no capability enum of its own, per the "never duplicate capability
constants" instruction. The registration/record shapes themselves have no
existing shared contract, so they are defined locally here (matching how
dispute-mcp-server defines local models for entities with no prior
contract).
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from chargeback_contracts.skills import SkillId


class AgentStatus(StrEnum):
    """Only ACTIVE is used today: expiry and deregistration remove the
    record entirely rather than transitioning it to a different status
    (see docs/superpowers/specs/2026-07-23-agent-registry-design.md).
    """

    ACTIVE = "active"


class AgentRegistration(BaseModel):
    """Inbound registration (and re-registration/refresh) payload."""

    model_config = ConfigDict(extra="forbid")

    agent_id: str = Field(min_length=1)
    agent_name: str = Field(min_length=1)
    endpoint: str = Field(min_length=1)
    version: str = Field(min_length=1)
    capabilities: tuple[SkillId, ...] = Field(min_length=1)


class AgentRecord(BaseModel):
    """Stored representation of a currently-registered agent."""

    model_config = ConfigDict(extra="forbid")

    agent_id: str
    agent_name: str
    endpoint: str
    version: str
    capabilities: tuple[SkillId, ...]
    status: AgentStatus
    lease_expires_at: datetime
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest agent-registry/tests/test_models.py -v`
Expected: `5 passed`

- [ ] **Step 5: Commit**

```bash
git add agent-registry/src/agent_registry/models.py agent-registry/tests/test_models.py
git commit -m "feat: add AgentRegistration and AgentRecord models"
```

---

### Task 4: Structured logging

**Files:**
- Create: `agent-registry/src/agent_registry/logging.py`
- Test: `agent-registry/tests/test_logging.py`

**Interfaces:**
- Produces: `configure_logging(level: str) -> logging.Logger`.

- [ ] **Step 1: Write the failing test**

Create `agent-registry/tests/test_logging.py`:

```python
"""Tests for agent_registry.logging."""

from __future__ import annotations

import logging

from agent_registry.logging import configure_logging


def test_configure_logging_sets_the_requested_level() -> None:
    logger = configure_logging("DEBUG")
    assert logger.level == logging.DEBUG
    assert logger.name == "agent_registry"


def test_configure_logging_attaches_exactly_one_handler_even_if_called_twice() -> None:
    first = configure_logging("INFO")
    second = configure_logging("WARNING")
    assert first is second
    assert len(second.handlers) == 1
    assert second.level == logging.WARNING
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest agent-registry/tests/test_logging.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agent_registry.logging'`

- [ ] **Step 3: Write the implementation**

Create `agent-registry/src/agent_registry/logging.py`:

```python
"""Structured logging for agent-registry.

Mirrors dispute-mcp-server's logging.py deliberately: an explicit
logger.setLevel(...) plus a manually-attached StreamHandler, never
logging.basicConfig. Prompt 4 found that relying on something else to
call logging.basicConfig is easy to silently omit entirely (transaction-
agent's INFO logs were dropped in the real running process until that gap
was found via live browser verification and fixed) -- this explicit
pattern has no such gap.
"""

from __future__ import annotations

import logging

_LOGGER_NAME = "agent_registry"


def configure_logging(level: str) -> logging.Logger:
    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(level)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
    return logger
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest agent-registry/tests/test_logging.py -v`
Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add agent-registry/src/agent_registry/logging.py agent-registry/tests/test_logging.py
git commit -m "feat: add structured logging for agent-registry"
```

---

### Task 5: In-memory repository

**Files:**
- Create: `agent-registry/src/agent_registry/repository.py`
- Test: `agent-registry/tests/test_repository.py`

**Interfaces:**
- Consumes: `agent_registry.models.AgentRecord`, `chargeback_contracts.skills.SkillId`.
- Produces: `AgentRepository` with `async def upsert(record: AgentRecord) -> None`, `async def get(agent_id: str) -> AgentRecord | None`, `async def remove(agent_id: str) -> AgentRecord | None`, `async def list_all() -> tuple[AgentRecord, ...]`, `async def find_by_capability(capability: SkillId) -> tuple[AgentRecord, ...]`, `async def list_capabilities() -> tuple[SkillId, ...]`, `async def remove_expired(*, now: datetime) -> tuple[str, ...]`.

- [ ] **Step 1: Write the failing test**

Create `agent-registry/tests/test_repository.py`:

```python
"""Tests for agent_registry.repository."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from agent_registry.models import AgentRecord, AgentStatus
from agent_registry.repository import AgentRepository
from chargeback_contracts.skills import SkillId


def _record(
    agent_id: str,
    *,
    capabilities: tuple[SkillId, ...] = (SkillId.TRANSACTION_INVESTIGATION,),
    lease_expires_at: datetime = datetime(2026, 1, 1, 0, 0, 30, tzinfo=UTC),
) -> AgentRecord:
    return AgentRecord(
        agent_id=agent_id,
        agent_name=f"Agent {agent_id}",
        endpoint=f"http://localhost:9000/{agent_id}",
        version="0.1.0",
        capabilities=capabilities,
        status=AgentStatus.ACTIVE,
        lease_expires_at=lease_expires_at,
    )


@pytest.mark.asyncio
async def test_upsert_then_get_returns_the_record() -> None:
    repository = AgentRepository()
    record = _record("agent-1")
    await repository.upsert(record)
    assert await repository.get("agent-1") == record


@pytest.mark.asyncio
async def test_get_unknown_agent_returns_none() -> None:
    repository = AgentRepository()
    assert await repository.get("nope") is None


@pytest.mark.asyncio
async def test_remove_returns_and_deletes_the_record() -> None:
    repository = AgentRepository()
    record = _record("agent-1")
    await repository.upsert(record)
    removed = await repository.remove("agent-1")
    assert removed == record
    assert await repository.get("agent-1") is None


@pytest.mark.asyncio
async def test_remove_unknown_agent_returns_none() -> None:
    repository = AgentRepository()
    assert await repository.remove("nope") is None


@pytest.mark.asyncio
async def test_list_all_on_empty_registry_returns_empty_tuple() -> None:
    repository = AgentRepository()
    assert await repository.list_all() == ()


@pytest.mark.asyncio
async def test_list_all_returns_every_upserted_record() -> None:
    repository = AgentRepository()
    await repository.upsert(_record("agent-1"))
    await repository.upsert(_record("agent-2"))
    result = await repository.list_all()
    assert {record.agent_id for record in result} == {"agent-1", "agent-2"}


@pytest.mark.asyncio
async def test_find_by_capability_returns_matching_agents_only() -> None:
    repository = AgentRepository()
    await repository.upsert(_record("agent-1", capabilities=(SkillId.TRANSACTION_INVESTIGATION,)))
    await repository.upsert(_record("agent-2", capabilities=(SkillId.CHARGEBACK_POLICY_INTERPRETATION,)))
    result = await repository.find_by_capability(SkillId.TRANSACTION_INVESTIGATION)
    assert [record.agent_id for record in result] == ["agent-1"]


@pytest.mark.asyncio
async def test_find_by_capability_with_no_matching_agents_returns_empty_tuple() -> None:
    repository = AgentRepository()
    await repository.upsert(_record("agent-1", capabilities=(SkillId.TRANSACTION_INVESTIGATION,)))
    result = await repository.find_by_capability(SkillId.CHARGEBACK_POLICY_INTERPRETATION)
    assert result == ()


@pytest.mark.asyncio
async def test_list_capabilities_returns_distinct_sorted_capabilities() -> None:
    repository = AgentRepository()
    await repository.upsert(_record("agent-1", capabilities=(SkillId.TRANSACTION_INVESTIGATION,)))
    await repository.upsert(
        _record(
            "agent-2",
            capabilities=(SkillId.TRANSACTION_INVESTIGATION, SkillId.CHARGEBACK_POLICY_INTERPRETATION),
        )
    )
    result = await repository.list_capabilities()
    assert result == tuple(
        sorted({SkillId.TRANSACTION_INVESTIGATION, SkillId.CHARGEBACK_POLICY_INTERPRETATION})
    )


@pytest.mark.asyncio
async def test_list_capabilities_on_empty_registry_returns_empty_tuple() -> None:
    repository = AgentRepository()
    assert await repository.list_capabilities() == ()


@pytest.mark.asyncio
async def test_remove_expired_deletes_only_records_past_the_given_time() -> None:
    repository = AgentRepository()
    now = datetime(2026, 1, 1, tzinfo=UTC)
    await repository.upsert(_record("expired", lease_expires_at=now - timedelta(seconds=1)))
    await repository.upsert(_record("still-active", lease_expires_at=now + timedelta(seconds=1)))
    removed_ids = await repository.remove_expired(now=now)
    assert removed_ids == ("expired",)
    assert await repository.get("expired") is None
    assert await repository.get("still-active") is not None


@pytest.mark.asyncio
async def test_concurrent_upserts_do_not_lose_any_record() -> None:
    repository = AgentRepository()
    await asyncio.gather(*(repository.upsert(_record(f"agent-{i}")) for i in range(50)))
    result = await repository.list_all()
    assert {record.agent_id for record in result} == {f"agent-{i}" for i in range(50)}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest agent-registry/tests/test_repository.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agent_registry.repository'`

- [ ] **Step 3: Write the implementation**

Create `agent-registry/src/agent_registry/repository.py`:

```python
"""In-memory repository owning registered agent state.

All mutations are guarded by an asyncio.Lock so concurrent registrations
can't interleave into a corrupted state -- explicit and verifiable rather
than relying on the GIL as an implicit invariant.
"""

from __future__ import annotations

import asyncio
from datetime import datetime

from agent_registry.models import AgentRecord
from chargeback_contracts.skills import SkillId


class AgentRepository:
    def __init__(self) -> None:
        self._agents: dict[str, AgentRecord] = {}
        self._lock = asyncio.Lock()

    async def upsert(self, record: AgentRecord) -> None:
        async with self._lock:
            self._agents[record.agent_id] = record

    async def get(self, agent_id: str) -> AgentRecord | None:
        async with self._lock:
            return self._agents.get(agent_id)

    async def remove(self, agent_id: str) -> AgentRecord | None:
        async with self._lock:
            return self._agents.pop(agent_id, None)

    async def list_all(self) -> tuple[AgentRecord, ...]:
        async with self._lock:
            return tuple(self._agents.values())

    async def find_by_capability(self, capability: SkillId) -> tuple[AgentRecord, ...]:
        async with self._lock:
            return tuple(
                record for record in self._agents.values() if capability in record.capabilities
            )

    async def list_capabilities(self) -> tuple[SkillId, ...]:
        async with self._lock:
            seen: set[SkillId] = set()
            for record in self._agents.values():
                seen.update(record.capabilities)
            return tuple(sorted(seen))

    async def remove_expired(self, *, now: datetime) -> tuple[str, ...]:
        async with self._lock:
            expired_ids = [
                agent_id
                for agent_id, record in self._agents.items()
                if record.lease_expires_at <= now
            ]
            for agent_id in expired_ids:
                del self._agents[agent_id]
            return tuple(expired_ids)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest agent-registry/tests/test_repository.py -v`
Expected: `12 passed`

- [ ] **Step 5: Commit**

```bash
git add agent-registry/src/agent_registry/repository.py agent-registry/tests/test_repository.py
git commit -m "feat: add in-memory, lock-guarded AgentRepository"
```

---

### Task 6: Registry service (register/renew/deregister/discover/sweep)

**Files:**
- Create: `agent-registry/src/agent_registry/service.py`
- Test: `agent-registry/tests/test_service.py`

**Interfaces:**
- Consumes: `agent_registry.clock.Clock`, `agent_registry.clock.FakeClock`, `agent_registry.models.{AgentRecord, AgentRegistration, AgentStatus}`, `agent_registry.repository.AgentRepository`, `chargeback_contracts.skills.SkillId`.
- Produces: `UnknownAgentError` (Exception), `RegistryService(*, repository: AgentRepository, clock: Clock, lease_duration_seconds: float)` with `async def register(registration: AgentRegistration) -> tuple[AgentRecord, bool]`, `async def renew(agent_id: str) -> AgentRecord`, `async def deregister(agent_id: str) -> AgentRecord`, `async def list_agents() -> tuple[AgentRecord, ...]`, `async def list_capabilities() -> tuple[SkillId, ...]`, `async def discover(capability: SkillId) -> tuple[AgentRecord, ...]`, `async def sweep_expired() -> tuple[str, ...]`.

- [ ] **Step 1: Write the failing test**

Create `agent-registry/tests/test_service.py`:

```python
"""Tests for agent_registry.service."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from agent_registry.clock import FakeClock
from agent_registry.models import AgentRegistration
from agent_registry.repository import AgentRepository
from agent_registry.service import RegistryService, UnknownAgentError
from chargeback_contracts.skills import SkillId


def _registration(agent_id: str = "agent-1") -> AgentRegistration:
    return AgentRegistration(
        agent_id=agent_id,
        agent_name=f"Agent {agent_id}",
        endpoint=f"http://localhost:9000/{agent_id}",
        version="0.1.0",
        capabilities=[SkillId.TRANSACTION_INVESTIGATION],
    )


def _service(clock: FakeClock | None = None, lease_duration_seconds: float = 30.0) -> RegistryService:
    return RegistryService(
        repository=AgentRepository(),
        clock=clock if clock is not None else FakeClock(),
        lease_duration_seconds=lease_duration_seconds,
    )


@pytest.mark.asyncio
async def test_register_new_agent_returns_record_and_is_new_true() -> None:
    service = _service(FakeClock(start=datetime(2026, 1, 1, tzinfo=UTC)), lease_duration_seconds=30.0)
    record, is_new = await service.register(_registration())
    assert is_new is True
    assert record.agent_id == "agent-1"
    assert record.lease_expires_at == datetime(2026, 1, 1, 0, 0, 30, tzinfo=UTC)


@pytest.mark.asyncio
async def test_register_existing_agent_id_refreshes_and_returns_is_new_false() -> None:
    service = _service()
    await service.register(_registration())
    _, is_new = await service.register(_registration())
    assert is_new is False


@pytest.mark.asyncio
async def test_renew_extends_the_lease_expiry() -> None:
    clock = FakeClock(start=datetime(2026, 1, 1, tzinfo=UTC))
    service = _service(clock, lease_duration_seconds=30.0)
    await service.register(_registration())
    clock.advance(20)
    renewed = await service.renew("agent-1")
    assert renewed.lease_expires_at == datetime(2026, 1, 1, 0, 0, 50, tzinfo=UTC)


@pytest.mark.asyncio
async def test_renew_unknown_agent_raises_unknown_agent_error() -> None:
    service = _service()
    with pytest.raises(UnknownAgentError):
        await service.renew("nope")


@pytest.mark.asyncio
async def test_deregister_removes_the_agent() -> None:
    service = _service()
    await service.register(_registration())
    await service.deregister("agent-1")
    assert await service.list_agents() == ()


@pytest.mark.asyncio
async def test_deregister_unknown_agent_raises_unknown_agent_error() -> None:
    service = _service()
    with pytest.raises(UnknownAgentError):
        await service.deregister("nope")


@pytest.mark.asyncio
async def test_list_agents_on_empty_registry_returns_empty_tuple() -> None:
    service = _service()
    assert await service.list_agents() == ()


@pytest.mark.asyncio
async def test_discover_returns_agents_advertising_the_capability() -> None:
    service = _service()
    await service.register(_registration("agent-1"))
    result = await service.discover(SkillId.TRANSACTION_INVESTIGATION)
    assert [record.agent_id for record in result] == ["agent-1"]


@pytest.mark.asyncio
async def test_discover_unknown_capability_returns_empty_tuple() -> None:
    service = _service()
    await service.register(_registration("agent-1"))
    result = await service.discover(SkillId.CHARGEBACK_POLICY_INTERPRETATION)
    assert result == ()


@pytest.mark.asyncio
async def test_sweep_expired_removes_only_agents_past_their_lease_using_fake_clock() -> None:
    clock = FakeClock(start=datetime(2026, 1, 1, tzinfo=UTC))
    service = _service(clock, lease_duration_seconds=30.0)
    await service.register(_registration("agent-1"))
    clock.advance(31)
    expired_ids = await service.sweep_expired()
    assert expired_ids == ("agent-1",)
    assert await service.list_agents() == ()


@pytest.mark.asyncio
async def test_sweep_expired_leaves_agents_still_within_their_lease() -> None:
    clock = FakeClock(start=datetime(2026, 1, 1, tzinfo=UTC))
    service = _service(clock, lease_duration_seconds=30.0)
    await service.register(_registration("agent-1"))
    clock.advance(10)
    expired_ids = await service.sweep_expired()
    assert expired_ids == ()
    assert len(await service.list_agents()) == 1


@pytest.mark.asyncio
async def test_re_register_after_expiry_succeeds_as_a_fresh_registration() -> None:
    clock = FakeClock(start=datetime(2026, 1, 1, tzinfo=UTC))
    service = _service(clock, lease_duration_seconds=30.0)
    await service.register(_registration("agent-1"))
    clock.advance(31)
    await service.sweep_expired()
    _, is_new = await service.register(_registration("agent-1"))
    assert is_new is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest agent-registry/tests/test_service.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agent_registry.service'`

- [ ] **Step 3: Write the implementation**

Create `agent-registry/src/agent_registry/service.py`:

```python
"""RegistryService: register/renew/deregister/discover/sweep_expired.

Sits between the API and the repository; owns the lease-duration policy
and all interactions with the injected Clock. Contains no orchestration
logic -- it only tracks who is registered and what they advertise.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from agent_registry.clock import Clock
from agent_registry.models import AgentRecord, AgentRegistration, AgentStatus
from agent_registry.repository import AgentRepository
from chargeback_contracts.skills import SkillId

logger = logging.getLogger("agent_registry")


class UnknownAgentError(Exception):
    """Raised when an operation targets an agent_id with no active lease."""


class RegistryService:
    def __init__(
        self, *, repository: AgentRepository, clock: Clock, lease_duration_seconds: float
    ) -> None:
        self._repository = repository
        self._clock = clock
        self._lease_duration_seconds = lease_duration_seconds

    async def register(self, registration: AgentRegistration) -> tuple[AgentRecord, bool]:
        """Upsert an agent by agent_id. Returns (record, is_new)."""
        existing = await self._repository.get(registration.agent_id)
        record = AgentRecord(
            agent_id=registration.agent_id,
            agent_name=registration.agent_name,
            endpoint=registration.endpoint,
            version=registration.version,
            capabilities=registration.capabilities,
            status=AgentStatus.ACTIVE,
            lease_expires_at=self._clock.now() + timedelta(seconds=self._lease_duration_seconds),
        )
        await self._repository.upsert(record)
        logger.info(
            "agent_id=%s outcome=%s",
            registration.agent_id,
            "registered" if existing is None else "refreshed",
        )
        return record, existing is None

    async def renew(self, agent_id: str) -> AgentRecord:
        existing = await self._repository.get(agent_id)
        if existing is None:
            raise UnknownAgentError(f"agent not found: {agent_id}")
        renewed = existing.model_copy(
            update={
                "lease_expires_at": self._clock.now()
                + timedelta(seconds=self._lease_duration_seconds)
            }
        )
        await self._repository.upsert(renewed)
        logger.info("agent_id=%s outcome=renewed", agent_id)
        return renewed

    async def deregister(self, agent_id: str) -> AgentRecord:
        removed = await self._repository.remove(agent_id)
        if removed is None:
            raise UnknownAgentError(f"agent not found: {agent_id}")
        logger.info("agent_id=%s outcome=deregistered", agent_id)
        return removed

    async def list_agents(self) -> tuple[AgentRecord, ...]:
        return await self._repository.list_all()

    async def list_capabilities(self) -> tuple[SkillId, ...]:
        return await self._repository.list_capabilities()

    async def discover(self, capability: SkillId) -> tuple[AgentRecord, ...]:
        return await self._repository.find_by_capability(capability)

    async def sweep_expired(self) -> tuple[str, ...]:
        expired_ids = await self._repository.remove_expired(now=self._clock.now())
        for agent_id in expired_ids:
            logger.info("agent_id=%s outcome=expired", agent_id)
        return expired_ids
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest agent-registry/tests/test_service.py -v`
Expected: `13 passed`

- [ ] **Step 5: Commit**

```bash
git add agent-registry/src/agent_registry/service.py agent-registry/tests/test_service.py
git commit -m "feat: add RegistryService with register/renew/deregister/discover/sweep"
```

---

### Task 7: Background lease-sweep task lifecycle

**Files:**
- Create: `agent-registry/src/agent_registry/lease_manager.py`
- Test: `agent-registry/tests/test_lease_manager.py`

**Interfaces:**
- Consumes: `agent_registry.service.RegistryService`.
- Produces: `LeaseManager(*, service: RegistryService, sweep_interval_seconds: float)` with `def start() -> None`, `async def stop() -> None`.

- [ ] **Step 1: Write the failing test**

Create `agent-registry/tests/test_lease_manager.py`:

```python
"""Tests for agent_registry.lease_manager.

These use a tiny real sweep_interval_seconds (not a FakeClock) because
this module's job is the scheduling loop itself, not expiry correctness
(fully covered, deterministically, in test_service.py). Kept fast with
sub-50ms real sleeps.
"""

from __future__ import annotations

import asyncio

import pytest

from agent_registry.clock import FakeClock
from agent_registry.lease_manager import LeaseManager
from agent_registry.repository import AgentRepository
from agent_registry.service import RegistryService


class _CountingService(RegistryService):
    def __init__(self) -> None:
        super().__init__(repository=AgentRepository(), clock=FakeClock(), lease_duration_seconds=30.0)
        self.sweep_calls = 0

    async def sweep_expired(self) -> tuple[str, ...]:
        self.sweep_calls += 1
        return await super().sweep_expired()


@pytest.mark.asyncio
async def test_start_runs_sweep_expired_at_least_once_within_a_few_intervals() -> None:
    service = _CountingService()
    manager = LeaseManager(service=service, sweep_interval_seconds=0.01)
    manager.start()
    await asyncio.sleep(0.05)
    await manager.stop()
    assert service.sweep_calls >= 1


@pytest.mark.asyncio
async def test_stop_cancels_the_background_task_cleanly() -> None:
    service = _CountingService()
    manager = LeaseManager(service=service, sweep_interval_seconds=0.01)
    manager.start()
    await asyncio.sleep(0.02)
    await manager.stop()
    calls_after_stop = service.sweep_calls
    await asyncio.sleep(0.05)
    assert service.sweep_calls == calls_after_stop


@pytest.mark.asyncio
async def test_start_is_idempotent_if_called_twice(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _CountingService()
    manager = LeaseManager(service=service, sweep_interval_seconds=0.01)
    create_task_calls = 0
    original_create_task = asyncio.create_task

    def counting_create_task(coro: object) -> asyncio.Task[None]:
        nonlocal create_task_calls
        create_task_calls += 1
        return original_create_task(coro)  # type: ignore[arg-type]

    monkeypatch.setattr(asyncio, "create_task", counting_create_task)
    manager.start()
    manager.start()
    assert create_task_calls == 1
    await manager.stop()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest agent-registry/tests/test_lease_manager.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agent_registry.lease_manager'`

- [ ] **Step 3: Write the implementation**

Create `agent-registry/src/agent_registry/lease_manager.py`:

```python
"""Background lease-sweep task lifecycle, used by api.py's FastAPI lifespan.

The sweep *logic* lives in RegistryService.sweep_expired(), independently
and deterministically tested with a FakeClock; this module only owns
starting/stopping the periodic background asyncio task around it.
"""

from __future__ import annotations

import asyncio
import logging

from agent_registry.service import RegistryService

logger = logging.getLogger("agent_registry")


class LeaseManager:
    def __init__(self, *, service: RegistryService, sweep_interval_seconds: float) -> None:
        self._service = service
        self._sweep_interval_seconds = sweep_interval_seconds
        self._task: asyncio.Task[None] | None = None

    async def _run(self) -> None:
        while True:
            await asyncio.sleep(self._sweep_interval_seconds)
            try:
                await self._service.sweep_expired()
            except Exception:
                logger.exception("lease sweep failed")

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest agent-registry/tests/test_lease_manager.py -v`
Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add agent-registry/src/agent_registry/lease_manager.py agent-registry/tests/test_lease_manager.py
git commit -m "feat: add background LeaseManager sweep task lifecycle"
```

---

### Task 8: FastAPI app and entrypoint

**Files:**
- Create: `agent-registry/src/agent_registry/api.py`
- Create: `agent-registry/src/agent_registry/main.py`
- Test: `agent-registry/tests/test_api.py`

**Interfaces:**
- Consumes: `agent_registry.config.load_settings`, `agent_registry.clock.{Clock, SystemClock}`, `agent_registry.logging.configure_logging`, `agent_registry.models.{AgentRecord, AgentRegistration}`, `agent_registry.repository.AgentRepository`, `agent_registry.service.{RegistryService, UnknownAgentError}`, `agent_registry.lease_manager.LeaseManager`, `chargeback_contracts.skills.SkillId`.
- Produces: `create_app(*, clock: Clock | None = None) -> FastAPI`, module-level `app`.

- [ ] **Step 1: Write the failing test**

Create `agent-registry/tests/test_api.py`:

```python
"""Tests for the FastAPI app's registration/renewal/deregistration/discovery/health endpoints."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from agent_registry.api import create_app
from agent_registry.clock import FakeClock


def _registration_payload(agent_id: str = "agent-1") -> dict[str, object]:
    return {
        "agent_id": agent_id,
        "agent_name": f"Agent {agent_id}",
        "endpoint": f"http://localhost:9000/{agent_id}",
        "version": "0.1.0",
        "capabilities": ["transaction-investigation"],
    }


def test_register_new_agent_returns_201() -> None:
    with TestClient(create_app(clock=FakeClock())) as client:
        response = client.post("/agents", json=_registration_payload())
    assert response.status_code == 201
    assert response.json()["agent_id"] == "agent-1"


def test_register_existing_agent_id_returns_200_and_refreshes() -> None:
    with TestClient(create_app(clock=FakeClock())) as client:
        client.post("/agents", json=_registration_payload())
        response = client.post("/agents", json=_registration_payload())
    assert response.status_code == 200


def test_register_rejects_unknown_field() -> None:
    with TestClient(create_app(clock=FakeClock())) as client:
        payload = _registration_payload()
        payload["unexpected"] = "nope"
        response = client.post("/agents", json=payload)
    assert response.status_code == 422


def test_renew_returns_200_with_a_later_lease_expiry() -> None:
    clock = FakeClock(start=datetime(2026, 1, 1, tzinfo=UTC))
    with TestClient(create_app(clock=clock)) as client:
        initial = client.post("/agents", json=_registration_payload()).json()
        clock.advance(5)
        response = client.post("/agents/agent-1/renew")
        renewed = response.json()
    assert response.status_code == 200
    assert renewed["lease_expires_at"] > initial["lease_expires_at"]


def test_renew_unknown_agent_returns_404() -> None:
    with TestClient(create_app(clock=FakeClock())) as client:
        response = client.post("/agents/nope/renew")
    assert response.status_code == 404


def test_deregister_returns_204() -> None:
    with TestClient(create_app(clock=FakeClock())) as client:
        client.post("/agents", json=_registration_payload())
        response = client.delete("/agents/agent-1")
    assert response.status_code == 204


def test_deregister_unknown_agent_returns_404() -> None:
    with TestClient(create_app(clock=FakeClock())) as client:
        response = client.delete("/agents/nope")
    assert response.status_code == 404


def test_list_agents_on_empty_registry_returns_empty_list() -> None:
    with TestClient(create_app(clock=FakeClock())) as client:
        response = client.get("/agents")
    assert response.status_code == 200
    assert response.json() == []


def test_list_agents_returns_registered_agents() -> None:
    with TestClient(create_app(clock=FakeClock())) as client:
        client.post("/agents", json=_registration_payload())
        response = client.get("/agents")
    assert [agent["agent_id"] for agent in response.json()] == ["agent-1"]


def test_list_capabilities_returns_distinct_capabilities() -> None:
    with TestClient(create_app(clock=FakeClock())) as client:
        client.post("/agents", json=_registration_payload())
        response = client.get("/agents/capabilities")
    assert response.json() == ["transaction-investigation"]


def test_discover_returns_matching_agents() -> None:
    with TestClient(create_app(clock=FakeClock())) as client:
        client.post("/agents", json=_registration_payload())
        response = client.get("/agents/discover", params={"capability": "transaction-investigation"})
    assert [agent["agent_id"] for agent in response.json()] == ["agent-1"]


def test_discover_unknown_capability_returns_empty_list() -> None:
    with TestClient(create_app(clock=FakeClock())) as client:
        client.post("/agents", json=_registration_payload())
        response = client.get(
            "/agents/discover", params={"capability": "chargeback-policy-interpretation"}
        )
    assert response.status_code == 200
    assert response.json() == []


def test_discover_rejects_an_invalid_capability_value() -> None:
    with TestClient(create_app(clock=FakeClock())) as client:
        response = client.get("/agents/discover", params={"capability": "not-a-real-capability"})
    assert response.status_code == 422


def test_health_returns_status_ok_and_agent_count() -> None:
    with TestClient(create_app(clock=FakeClock())) as client:
        client.post("/agents", json=_registration_payload())
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "agent_count": 1}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest agent-registry/tests/test_api.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agent_registry.api'`

- [ ] **Step 3: Write the implementation**

Create `agent-registry/src/agent_registry/api.py`:

```python
"""FastAPI app: registration, renewal, deregistration, discovery, health.

No orchestration logic here or anywhere in this package -- this service
only tracks who is registered and what they advertise.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict

from agent_registry.clock import Clock, SystemClock
from agent_registry.config import load_settings
from agent_registry.lease_manager import LeaseManager
from agent_registry.logging import configure_logging
from agent_registry.models import AgentRecord, AgentRegistration
from agent_registry.repository import AgentRepository
from agent_registry.service import RegistryService, UnknownAgentError
from chargeback_contracts.skills import SkillId


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str
    agent_count: int


def create_app(*, clock: Clock | None = None) -> FastAPI:
    settings = load_settings()
    configure_logging(settings.log_level)
    repository = AgentRepository()
    service = RegistryService(
        repository=repository,
        clock=clock if clock is not None else SystemClock(),
        lease_duration_seconds=settings.lease_duration_seconds,
    )
    lease_manager = LeaseManager(
        service=service, sweep_interval_seconds=settings.lease_sweep_interval_seconds
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        lease_manager.start()
        yield
        await lease_manager.stop()

    app = FastAPI(title=settings.service_name, lifespan=lifespan)

    @app.post("/agents", response_model=AgentRecord)
    async def register_agent(registration: AgentRegistration, response: Response) -> AgentRecord:
        record, is_new = await service.register(registration)
        response.status_code = status.HTTP_201_CREATED if is_new else status.HTTP_200_OK
        return record

    @app.post("/agents/{agent_id}/renew", response_model=AgentRecord)
    async def renew_agent(agent_id: str) -> AgentRecord:
        try:
            return await service.renew(agent_id)
        except UnknownAgentError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    @app.delete("/agents/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def deregister_agent(agent_id: str) -> None:
        try:
            await service.deregister(agent_id)
        except UnknownAgentError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    @app.get("/agents", response_model=list[AgentRecord])
    async def list_agents() -> list[AgentRecord]:
        return list(await service.list_agents())

    @app.get("/agents/capabilities", response_model=list[SkillId])
    async def list_capabilities() -> list[SkillId]:
        return list(await service.list_capabilities())

    @app.get("/agents/discover", response_model=list[AgentRecord])
    async def discover(capability: SkillId) -> list[AgentRecord]:
        return list(await service.discover(capability))

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        agents = await service.list_agents()
        return HealthResponse(status="ok", agent_count=len(agents))

    return app


app = create_app()
```

Create `agent-registry/src/agent_registry/main.py`:

```python
"""uvicorn entrypoint for agent-registry."""

from __future__ import annotations

import uvicorn

from agent_registry.api import app

__all__ = ["app", "main"]


def main() -> None:
    uvicorn.run(app, host="0.0.0.0", port=8020)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest agent-registry/tests/test_api.py -v`
Expected: `14 passed`

Also run the full package's suite to confirm nothing regressed:

Run: `uv run pytest agent-registry/tests/ -v`
Expected: all tests across every task in this plan pass.

- [ ] **Step 5: Commit**

```bash
git add agent-registry/src/agent_registry/api.py agent-registry/src/agent_registry/main.py \
  agent-registry/tests/test_api.py
git commit -m "feat: add agent-registry FastAPI endpoints and entrypoint"
```

---

### Task 9: Makefile developer commands

**Files:**
- Modify: `Makefile`

**Interfaces:** none.

- [ ] **Step 1: Add `registry-test` and `registry-run` targets**

In `Makefile`, update the `.PHONY` line and add two targets, mirroring the existing `mcp-test`/`mcp-run` pair:

Change:
```makefile
.PHONY: install lock format lint typecheck test mcp-test mcp-run verify ui-install ui-build clean
```
to:
```makefile
.PHONY: install lock format lint typecheck test mcp-test mcp-run registry-test registry-run verify ui-install ui-build clean
```

Add, directly after the existing `mcp-run:` target:
```makefile
registry-test:
	uv run pytest agent-registry/tests -v

registry-run:
	uv run --package agent-registry python -m agent_registry.main
```

- [ ] **Step 2: Verify the new targets work**

Run: `make registry-test`
Expected: the full `agent-registry` test suite passes (same count as Task 8's Step 4 full-package run).

- [ ] **Step 3: Commit**

```bash
git add Makefile
git commit -m "chore: add registry-test and registry-run Makefile targets"
```

---

### Task 10: README update

**Files:**
- Modify: `README.md`

**Interfaces:** none.

- [ ] **Step 1: Insert a new section after "Vertical Slice (End-to-End Spike)"**

Insert, immediately after that section's final paragraph and before "## Prerequisites":

```markdown
## Agent Registry

`agent-registry` is a standalone FastAPI service providing lease-based
runtime capability discovery. No database — state lives only in an
in-memory repository for the life of the process.

- `POST /agents` — register or re-register (idempotent upsert by
  `agent_id`; `201` when new, `200` when refreshing an existing lease).
- `POST /agents/{agent_id}/renew` — renew an active lease; `404` if the
  agent is unknown or already expired.
- `DELETE /agents/{agent_id}` — deregister; `404` if unknown.
- `GET /agents` — list all currently active agents.
- `GET /agents/capabilities` — list the distinct capabilities currently
  advertised by at least one active agent.
- `GET /agents/discover?capability=...` — find active agents advertising
  a given capability (reuses `chargeback_contracts.skills.SkillId` — this
  package defines no capability constants of its own); an unmatched or
  unknown capability returns an empty list, not an error.
- `GET /health` — `{"status": "ok", "agent_count": <int>}`.

A lease expires automatically if not renewed; a background task sweeps
expired leases on a configurable interval (`LEASE_SWEEP_INTERVAL_SECONDS`,
default 10s), removing them entirely so the same `agent_id` can freely
re-register afterward. Lease-expiry logic is tested deterministically via
an injectable `Clock` (`FakeClock`), never real sleeping.

This service is not yet wired into `transaction-agent` or any other
service — that integration is deferred to a later prompt. No Orchestrator,
A2A routing, or additional specialist agents are implemented here.

Run it locally with `make registry-run`; test it with `make registry-test`.
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add Agent Registry section to README"
```

---

### Task 11: Full verification and preserved-behavior check

**Files:** none created; verification only.

**Interfaces:**
- Consumes: everything from Tasks 1-10.

- [ ] **Step 1: Run `make verify` from the repo root**

Run: `make verify`
Expected: Ruff format-check, Ruff lint, strict Mypy, the full pytest suite (all packages, including `agent-registry`'s new tests), and the `investigator-ui` production build all pass.

- [ ] **Step 2: Confirm Prompt 4's vertical slice is untouched**

Run: `git diff --stat <task-1-base-sha>..HEAD -- transaction-agent/src investigator-ui/src dispute-mcp-server/src`
Expected: empty output — this batch touched none of the Transaction Agent, investigator-ui, or dispute-mcp-server source files, per the "do not rewrite" constraint.

- [ ] **Step 3: If anything fails**

Fix the specific file the error points to. Do not weaken strictness anywhere. Re-run `make verify` until clean. Commit each fix separately.

- [ ] **Step 4: Confirm working tree is clean and pre-existing files untouched**

Run: `git status --short`
Expected: no output. Also confirm no commit in this batch touched `.gitignore` or `tmp/`.

---

### Task 12: Consolidated changelog

**Files:**
- Modify: `docs/COMMIT_LOG.md`

**Interfaces:** none.

- [ ] **Step 1: Append one consolidated entry**

Following the existing file's format (most-recent-first, directly below the `# Commit Log` header), add one entry summarizing every commit from Task 1 through Task 11 of this batch: files touched, what was built (lease-based Agent Registry: config, Clock, models reusing `SkillId`, repository, service, lease manager, API, Makefile targets, README section), and why (Prompt 5's standalone capability-discovery service, explicitly not yet integrated with `transaction-agent`).

- [ ] **Step 2: Commit**

```bash
git add docs/COMMIT_LOG.md
git commit -m "docs: add consolidated Prompt 5 changelog entry"
```

---

## Plan Self-Review Notes

- **Spec coverage:** every Scope bullet (Registration API, lease renewal, deregistration, capability discovery, agent listing, health endpoint, background lease expiry, structured logging) maps to Tasks 3/5/6/7/8. Every Lease Behaviour bullet (register, renew, deregister, automatic expiry, re-register) is covered by `test_service.py`. Every Discovery Behaviour bullet (find by capability, list agents, list capabilities, unknown capability, empty registry) is covered by both `test_service.py` and `test_api.py`. Every Tests bullet (registration, duplicate registration, lease renewal, lease expiry, deregistration, discovery, unknown capability, concurrent registrations) has a named test. "Existing Prompt 4 tests" is covered by Task 11's full `make verify` run plus the explicit untouched-source-directory diff check.
- **Placeholder scan:** no TBD/TODO; every step has complete, runnable code.
- **Type consistency:** `AgentRegistration`/`AgentRecord`/`AgentStatus` (Task 3) are used identically in `repository.py` (Task 5), `service.py` (Task 6), and `api.py` (Task 8); `RegistryService`'s method names and signatures (Task 6) match exactly what `lease_manager.py` (Task 7) and `api.py` (Task 8) call.
