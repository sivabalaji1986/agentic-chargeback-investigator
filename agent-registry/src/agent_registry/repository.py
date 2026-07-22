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
