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
    await repository.upsert(
        _record("agent-2", capabilities=(SkillId.CHARGEBACK_POLICY_INTERPRETATION,))
    )
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
            capabilities=(
                SkillId.TRANSACTION_INVESTIGATION,
                SkillId.CHARGEBACK_POLICY_INTERPRETATION,
            ),
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
