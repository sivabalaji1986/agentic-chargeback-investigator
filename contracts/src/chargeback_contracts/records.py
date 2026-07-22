"""Final investigation record, suitable for audit persistence.

A completed InvestigationRecord requires an InvestigatorDecision — this is
what makes mandatory human approval structurally enforced rather than a
convention. A partial or failed investigation may exist without a final
decision, but its status must accurately reflect that state.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from chargeback_contracts.common import ContractModel, require_non_blank, require_utc
from chargeback_contracts.decisions import InvestigatorDecision
from chargeback_contracts.dispute import InvestigationRequest
from chargeback_contracts.findings import SpecialistFinding
from chargeback_contracts.policy import PolicyInterpretation
from chargeback_contracts.recommendation import (
    InvestigationRecommendation,
    MissingCapabilityWarning,
)
from chargeback_contracts.skills import SkillId


class WorkflowStatus(StrEnum):
    """The investigation's overall workflow state."""

    IN_PROGRESS = "in_progress"
    PARTIAL = "partial"
    COMPLETED = "completed"
    FAILED = "failed"


class InvestigationRecord(ContractModel):
    """The durable record of one chargeback investigation, for audit persistence.

    `recommendation.explanation` is the explanation generated alongside the
    deterministic recommendation; the top-level `explanation` field is the
    current explanation surfaced to the investigator and may be
    independently regenerated (e.g. by an LLM) without touching the
    immutable deterministic recommendation fields.
    """

    request: InvestigationRequest
    discovered_skill_ids: tuple[SkillId, ...] = ()
    missing_capability_warnings: tuple[MissingCapabilityWarning, ...] = ()
    specialist_findings: tuple[SpecialistFinding, ...] = ()
    policy_interpretation: PolicyInterpretation | None = None
    recommendation: InvestigationRecommendation | None = None
    explanation: str | None = None
    investigator_decision: InvestigatorDecision | None = None
    created_at: datetime
    completed_at: datetime | None = None
    status: WorkflowStatus
    audit_correlation_id: str = Field(min_length=1)

    @field_validator("audit_correlation_id")
    @classmethod
    def _audit_correlation_id(cls, value: str) -> str:
        return require_non_blank(value, field_name="audit_correlation_id")

    @field_validator("created_at")
    @classmethod
    def _created_at(cls, value: datetime) -> datetime:
        return require_utc(value, field_name="created_at")

    @field_validator("completed_at")
    @classmethod
    def _completed_at(cls, value: datetime | None) -> datetime | None:
        if value is not None:
            return require_utc(value, field_name="completed_at")
        return value

    @model_validator(mode="after")
    def _validate_workflow_rules(self) -> InvestigationRecord:
        if self.status == WorkflowStatus.COMPLETED and self.investigator_decision is None:
            raise ValueError("a completed InvestigationRecord requires an InvestigatorDecision")
        if self.completed_at is not None and self.completed_at < self.created_at:
            raise ValueError("completed_at cannot precede created_at")
        return self
