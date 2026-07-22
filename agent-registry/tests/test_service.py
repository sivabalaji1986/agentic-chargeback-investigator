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
        capabilities=(SkillId.TRANSACTION_INVESTIGATION,),
    )


def _service(
    clock: FakeClock | None = None, lease_duration_seconds: float = 30.0
) -> RegistryService:
    return RegistryService(
        repository=AgentRepository(),
        clock=clock if clock is not None else FakeClock(),
        lease_duration_seconds=lease_duration_seconds,
    )


@pytest.mark.asyncio
async def test_register_new_agent_returns_record_and_is_new_true() -> None:
    service = _service(
        FakeClock(start=datetime(2026, 1, 1, tzinfo=UTC)), lease_duration_seconds=30.0
    )
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
