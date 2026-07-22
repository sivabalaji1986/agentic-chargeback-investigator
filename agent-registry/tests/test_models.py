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
        capabilities=(SkillId.TRANSACTION_INVESTIGATION,),
    )
    assert registration.agent_id == "transaction-agent-1"


def test_agent_registration_capabilities_reuse_the_shared_skill_id_enum() -> None:
    registration = AgentRegistration(
        agent_id="transaction-agent-1",
        agent_name="Transaction Agent",
        endpoint="http://localhost:8010",
        version="0.1.0",
        capabilities=(SkillId.TRANSACTION_INVESTIGATION,),
    )
    assert registration.capabilities[0] is SkillId.TRANSACTION_INVESTIGATION
    assert registration.capabilities[0] == "transaction-investigation"  # type: ignore[comparison-overlap]


def test_agent_registration_requires_at_least_one_capability() -> None:
    with pytest.raises(ValidationError):
        AgentRegistration(
            agent_id="agent-1",
            agent_name="Agent",
            endpoint="http://localhost:9000",
            version="0.1.0",
            capabilities=(),
        )


def test_agent_registration_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError):
        AgentRegistration(
            agent_id="agent-1",
            agent_name="Agent",
            endpoint="http://localhost:9000",
            version="0.1.0",
            capabilities=(SkillId.TRANSACTION_INVESTIGATION,),
            unexpected="nope",  # type: ignore[call-arg]
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
