"""Dispute intake contracts."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import Field, field_validator

from chargeback_contracts.common import (
    ContractModel,
    require_currency_code,
    require_non_blank,
    require_positive_amount,
    require_utc,
)
from chargeback_contracts.evidence import EvidenceRef
from chargeback_contracts.skills import DisputeType, SkillId


class SourceChannel(str, Enum):
    """Channel through which the customer submitted the dispute."""

    EMAIL = "email"
    CONTACT_CENTRE = "contact_centre"
    WEB_FORM = "web_form"
    CHATBOT = "chatbot"


class InvestigationRequest(ContractModel):
    """Intake payload describing a single chargeback dispute to investigate."""

    investigation_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    transaction_id: str = Field(min_length=1)
    source_channel: SourceChannel
    customer_narrative: str = Field(min_length=1)
    dispute_type: DisputeType
    amount: Decimal
    currency: str
    submitted_at: datetime
    evidence_refs: tuple[EvidenceRef, ...] = ()
    requested_skill_ids: tuple[SkillId, ...] = ()
    a2a_context_id: str | None = None

    @field_validator("investigation_id", "case_id", "transaction_id", "customer_narrative")
    @classmethod
    def _non_blank(cls, value: str, info: object) -> str:
        return require_non_blank(value, field_name=info.field_name)  # type: ignore[attr-defined]

    @field_validator("currency")
    @classmethod
    def _currency(cls, value: str) -> str:
        return require_currency_code(value)

    @field_validator("amount")
    @classmethod
    def _amount(cls, value: Decimal) -> Decimal:
        return require_positive_amount(value)

    @field_validator("submitted_at")
    @classmethod
    def _submitted_at(cls, value: datetime) -> datetime:
        return require_utc(value, field_name="submitted_at")

    @field_validator("a2a_context_id")
    @classmethod
    def _context_id(cls, value: str | None) -> str | None:
        if value is not None:
            return require_non_blank(value, field_name="a2a_context_id")
        return value
