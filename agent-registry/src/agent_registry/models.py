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
