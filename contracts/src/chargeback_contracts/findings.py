"""Specialist finding contracts.

Specialists investigate and report facts. A SpecialistFinding must never
carry the final Accept / Reject / Request More Evidence recommendation —
enforced structurally by this module simply defining no such field.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from chargeback_contracts.common import ContractModel, require_non_blank, require_utc
from chargeback_contracts.evidence import EvidenceRef, EvidenceType
from chargeback_contracts.skills import SkillId


class FindingStatus(StrEnum):
    """Completion state of a specialist's investigation."""

    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


class TransactionFindingDetails(ContractModel):
    """Structured facts produced by the Transaction specialist."""

    kind: Literal["transaction"] = "transaction"
    transaction_matched: bool
    posted_at: datetime | None = None
    merchant: str | None = None
    amount: Decimal | None = None
    currency: str | None = None
    authorization_reference: str | None = None
    related_transaction_ids: tuple[str, ...] = ()
    timeline_observations: tuple[str, ...] = ()


class CustomerHistoryFindingDetails(ContractModel):
    """Structured facts produced by the Customer History specialist.

    Also reused by ``mcp.py`` for the ``get_customer_history`` read result,
    since the shape of "customer history facts" is identical in both places.
    """

    kind: Literal["customer_history"] = "customer_history"
    previous_dispute_count: int = Field(ge=0)
    previous_refund_count: int = Field(ge=0)
    prior_similar_claim_ids: tuple[str, ...] = ()
    customer_tenure_days: int | None = Field(default=None, ge=0)
    observations: tuple[str, ...] = ()


class MerchantEvidenceFindingDetails(ContractModel):
    """Structured facts produced by the Merchant Evidence specialist."""

    kind: Literal["merchant_evidence"] = "merchant_evidence"
    evidence_ids_reviewed: tuple[str, ...] = ()
    merchant_acknowledgement: bool | None = None
    cancellation_evidence_found: bool | None = None
    delivery_evidence_found: bool | None = None
    refund_evidence_found: bool | None = None
    authenticity_observations: tuple[str, ...] = ()
    missing_evidence: tuple[EvidenceType, ...] = ()


FindingDetails = Annotated[
    TransactionFindingDetails | CustomerHistoryFindingDetails | MerchantEvidenceFindingDetails,
    Field(discriminator="kind"),
]


class SpecialistFinding(ContractModel):
    """Common envelope for a specialist's reported facts.

    Never carries a recommendation — ownership of the final recommendation
    stays with the deterministic recommendation engine, not the specialist.
    """

    finding_id: str = Field(min_length=1)
    investigation_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    producing_agent_id: str = Field(min_length=1)
    skill_id: SkillId
    status: FindingStatus
    summary: str = Field(min_length=1)
    details: FindingDetails
    evidence_refs_used: tuple[EvidenceRef, ...] = ()
    missing_evidence: tuple[EvidenceType, ...] = ()
    warnings: tuple[str, ...] = ()
    started_at: datetime
    completed_at: datetime | None = None
    a2a_task_id: str | None = None
    a2a_context_id: str | None = None

    @field_validator("finding_id", "investigation_id", "case_id", "producing_agent_id", "summary")
    @classmethod
    def _non_blank(cls, value: str, info: object) -> str:
        return require_non_blank(value, field_name=info.field_name)  # type: ignore[attr-defined]

    @field_validator("started_at")
    @classmethod
    def _started_at(cls, value: datetime) -> datetime:
        return require_utc(value, field_name="started_at")

    @field_validator("completed_at")
    @classmethod
    def _completed_at(cls, value: datetime | None) -> datetime | None:
        if value is not None:
            return require_utc(value, field_name="completed_at")
        return value

    @field_validator("a2a_task_id", "a2a_context_id")
    @classmethod
    def _blank_a2a_ids(cls, value: str | None, info: object) -> str | None:
        if value is not None:
            return require_non_blank(value, field_name=info.field_name)  # type: ignore[attr-defined]
        return value

    @model_validator(mode="after")
    def _validate_status_rules(self) -> SpecialistFinding:
        if self.status == FindingStatus.COMPLETED and self.completed_at is None:
            raise ValueError("completed findings require a completion timestamp")
        if self.status == FindingStatus.PARTIAL and not (self.warnings or self.missing_evidence):
            raise ValueError("partial findings must contain warnings or missing evidence")
        if self.completed_at is not None and self.completed_at < self.started_at:
            raise ValueError("completed_at cannot precede started_at")
        return self
