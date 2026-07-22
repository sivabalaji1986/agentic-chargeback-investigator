"""AG-UI application event payloads.

These are the typed `value` payloads for `ag_ui.core.CustomEvent`
(`type=EventType.CUSTOM`) — not CustomEvent subclasses themselves, and not
the streaming server that would construct CustomEvent instances (out of
scope for this prompt). Official AG-UI event types come from
`ag_ui.core`; only application-owned payloads are defined here.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field, ValidationInfo, field_validator

from chargeback_contracts.common import ContractModel, require_non_blank, require_utc
from chargeback_contracts.evidence import EvidenceType
from chargeback_contracts.recommendation import MissingCapabilityWarning, RecommendationType
from chargeback_contracts.skills import DisputeType, SkillId


class AgUiEventPayload(ContractModel):
    """Correlation fields shared by every AG-UI custom event payload."""

    investigation_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    sequence: int | None = Field(default=None, ge=0)
    occurred_at: datetime
    agent_id: str | None = None
    skill_id: SkillId | None = None

    @field_validator("investigation_id", "case_id", "run_id")
    @classmethod
    def _non_blank(cls, value: str, info: ValidationInfo) -> str:
        assert info.field_name is not None
        return require_non_blank(value, field_name=info.field_name)

    @field_validator("occurred_at")
    @classmethod
    def _occurred_at(cls, value: datetime) -> datetime:
        return require_utc(value, field_name="occurred_at")


class InvestigationAcceptedEvent(AgUiEventPayload):
    event_name: Literal["investigation.accepted"] = "investigation.accepted"
    dispute_type: DisputeType
    requested_skill_ids: tuple[SkillId, ...] = ()


class CapabilityDiscoveryStartedEvent(AgUiEventPayload):
    event_name: Literal["capability_discovery.started"] = "capability_discovery.started"
    requested_skill_ids: tuple[SkillId, ...] = ()


class CapabilityDiscoveryCompletedEvent(AgUiEventPayload):
    event_name: Literal["capability_discovery.completed"] = "capability_discovery.completed"
    discovered_skill_ids: tuple[SkillId, ...] = ()
    missing_skill_ids: tuple[SkillId, ...] = ()


class SpecialistStartedEvent(AgUiEventPayload):
    event_name: Literal["specialist.started"] = "specialist.started"


class SpecialistProgressEvent(AgUiEventPayload):
    event_name: Literal["specialist.progress"] = "specialist.progress"
    message: str = Field(min_length=1)


class SpecialistFindingReceivedEvent(AgUiEventPayload):
    event_name: Literal["specialist.finding_received"] = "specialist.finding_received"
    finding_id: str = Field(min_length=1)


class MissingEvidenceIdentifiedEvent(AgUiEventPayload):
    event_name: Literal["evidence.missing_identified"] = "evidence.missing_identified"
    missing_evidence: tuple[EvidenceType, ...] = ()


class MissingCapabilityIdentifiedEvent(AgUiEventPayload):
    event_name: Literal["capability.missing_identified"] = "capability.missing_identified"
    warning: MissingCapabilityWarning


class PolicyInterpretationReceivedEvent(AgUiEventPayload):
    event_name: Literal["policy.interpretation_received"] = "policy.interpretation_received"


class RecommendationProducedEvent(AgUiEventPayload):
    event_name: Literal["recommendation.produced"] = "recommendation.produced"
    recommendation: RecommendationType


class ExplanationProducedEvent(AgUiEventPayload):
    event_name: Literal["explanation.produced"] = "explanation.produced"
    explanation: str = Field(min_length=1)


class ApprovalRequiredEvent(AgUiEventPayload):
    event_name: Literal["approval.required"] = "approval.required"


class InvestigationCompletedEvent(AgUiEventPayload):
    event_name: Literal["investigation.completed"] = "investigation.completed"
    final_status: str = Field(min_length=1)


class InvestigationFailedEvent(AgUiEventPayload):
    event_name: Literal["investigation.failed"] = "investigation.failed"
    reason: str = Field(min_length=1)
