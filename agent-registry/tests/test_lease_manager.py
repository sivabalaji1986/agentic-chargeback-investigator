"""Tests for agent_registry.lease_manager.

These use a tiny real sweep_interval_seconds (not a FakeClock) because
this module's job is the scheduling loop itself, not expiry correctness
(fully covered, deterministically, in test_registry_service.py). Kept fast with
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
        super().__init__(
            repository=AgentRepository(), clock=FakeClock(), lease_duration_seconds=30.0
        )
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
