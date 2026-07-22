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
