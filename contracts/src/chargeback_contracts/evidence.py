"""Evidence reference contracts.

Evidence references carry a secure pointer to evidence content; they must
never carry raw file bytes, and must never expose a local filesystem path.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import Field, field_validator

from chargeback_contracts.common import ContractModel, require_non_blank, require_utc

ALLOWED_EVIDENCE_URI_SCHEMES: tuple[str, ...] = ("evidence://",)


class EvidenceType(str, Enum):
    """Supported evidence categories for a chargeback investigation."""

    CUSTOMER_DECLARATION = "customer_declaration"
    TRANSACTION_STATEMENT = "transaction_statement"
    MERCHANT_EMAIL = "merchant_email"
    MERCHANT_CHAT = "merchant_chat"
    RECEIPT = "receipt"
    INVOICE = "invoice"
    CANCELLATION_CONFIRMATION = "cancellation_confirmation"
    DELIVERY_PROOF = "delivery_proof"
    REFUND_REQUEST = "refund_request"
    POLICE_REPORT = "police_report"
    SCREENSHOT = "screenshot"
    OTHER = "other"


class EvidenceRef(ContractModel):
    """A pointer to evidence content — never the content itself."""

    evidence_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    evidence_type: EvidenceType
    display_name: str = Field(min_length=1)
    media_type: str = Field(min_length=1)
    uri: str = Field(min_length=1)
    uploaded_at: datetime
    source: str = Field(min_length=1)
    checksum: str | None = None
    description: str | None = None

    @field_validator("evidence_id", "case_id", "display_name", "media_type", "source")
    @classmethod
    def _non_blank(cls, value: str, info: object) -> str:
        return require_non_blank(value, field_name=info.field_name)  # type: ignore[attr-defined]

    @field_validator("uri")
    @classmethod
    def _safe_uri(cls, value: str) -> str:
        if not value.startswith(ALLOWED_EVIDENCE_URI_SCHEMES):
            raise ValueError(
                f"evidence uri must use one of {ALLOWED_EVIDENCE_URI_SCHEMES}, got: {value!r}"
            )
        return value

    @field_validator("uploaded_at")
    @classmethod
    def _uploaded_at(cls, value: datetime) -> datetime:
        return require_utc(value, field_name="uploaded_at")
