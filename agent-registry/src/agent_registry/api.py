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
