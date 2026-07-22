"""A2UI application-owned payloads for the investigator decision interface.

No official A2UI SDK exists; every model here is application-owned. The
A2UI specification/protocol version this project targets is exactly
"0.9" — enforced via the Literal type on A2uiEnvelope.version.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field, ValidationInfo, field_validator

from chargeback_contracts.common import ContractModel, require_non_blank, require_utc
from chargeback_contracts.evidence import EvidenceRef, EvidenceType
from chargeback_contracts.recommendation import MissingCapabilityWarning, RecommendationType

A2UI_VERSION: Literal["0.9"] = "0.9"


class InvestigatorAction(StrEnum):
    """Human decisions available on the investigator decision interface.

    These represent human decisions, not autonomous agent actions.
    """

    APPROVE_RECOMMENDATION = "approve_recommendation"
    REJECT_RECOMMENDATION = "reject_recommendation"
    REQUEST_MORE_EVIDENCE = "request_more_evidence"


class DecisionCard(ContractModel):
    """Distinguishes the deterministic recommendation from its explanation."""

    component_type: Literal["decision_card"] = "decision_card"
    investigation_id: str = Field(min_length=1)
    recommendation: RecommendationType
    explanation: str = Field(min_length=1)
    policy_references: tuple[str, ...] = ()
    missing_evidence: tuple[EvidenceType, ...] = ()
    has_warnings: bool = False


class EvidenceChecklistItem(ContractModel):
    evidence_type: EvidenceType
    satisfied: bool
    evidence_ref: EvidenceRef | None = None


class EvidenceChecklist(ContractModel):
    component_type: Literal["evidence_checklist"] = "evidence_checklist"
    investigation_id: str = Field(min_length=1)
    items: tuple[EvidenceChecklistItem, ...] = ()


class SpecialistFindingsSummary(ContractModel):
    component_type: Literal["specialist_findings_summary"] = "specialist_findings_summary"
    investigation_id: str = Field(min_length=1)
    finding_summaries: tuple[str, ...] = ()


class MissingCapabilityWarningPanel(ContractModel):
    component_type: Literal["missing_capability_warning_panel"] = "missing_capability_warning_panel"
    investigation_id: str = Field(min_length=1)
    warnings: tuple[MissingCapabilityWarning, ...] = ()


class RecommendedNextAction(ContractModel):
    action: InvestigatorAction
    label: str = Field(min_length=1)


class RecommendedNextActions(ContractModel):
    component_type: Literal["recommended_next_actions"] = "recommended_next_actions"
    investigation_id: str = Field(min_length=1)
    actions: tuple[RecommendedNextAction, ...] = ()


class ApprovalPreview(ContractModel):
    component_type: Literal["approval_preview"] = "approval_preview"
    investigation_id: str = Field(min_length=1)
    recommendation: RecommendationType
    summary: str = Field(min_length=1)


class FinalDecisionConfirmation(ContractModel):
    component_type: Literal["final_decision_confirmation"] = "final_decision_confirmation"
    investigation_id: str = Field(min_length=1)
    decision_id: str = Field(min_length=1)
    action: InvestigatorAction
    confirmed_at: datetime

    @field_validator("confirmed_at")
    @classmethod
    def _confirmed_at(cls, value: datetime) -> datetime:
        return require_utc(value, field_name="confirmed_at")


A2uiComponent = Annotated[
    DecisionCard
    | EvidenceChecklist
    | SpecialistFindingsSummary
    | MissingCapabilityWarningPanel
    | RecommendedNextActions
    | ApprovalPreview
    | FinalDecisionConfirmation,
    Field(discriminator="component_type"),
]


class A2uiEnvelope(ContractModel):
    """Envelope wrapping the components rendered on the decision interface."""

    version: Literal["0.9"]
    surface_id: str = Field(min_length=1)
    investigation_id: str = Field(min_length=1)
    components: tuple[A2uiComponent, ...] = ()
    allowed_actions: tuple[InvestigatorAction, ...] = ()
    generated_at: datetime

    @field_validator("surface_id", "investigation_id")
    @classmethod
    def _non_blank(cls, value: str, info: ValidationInfo) -> str:
        assert info.field_name is not None
        return require_non_blank(value, field_name=info.field_name)

    @field_validator("generated_at")
    @classmethod
    def _generated_at(cls, value: datetime) -> datetime:
        return require_utc(value, field_name="generated_at")
