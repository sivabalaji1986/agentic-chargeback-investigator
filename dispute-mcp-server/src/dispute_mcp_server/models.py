"""Local response models for dispute-mcp-server's read tools.

These are package-owned, not part of chargeback_contracts: Prompt 2
deliberately left the case/transaction/customer/merchant business schema
undefined, and this package is where that schema now lives. Write-tool
requests/responses instead reuse chargeback_contracts.mcp's existing
envelope contracts directly (see tools/case_tools.py) — those are generic
enough to need no business-specific richness of their own.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from chargeback_contracts.skills import DisputeType
from pydantic import BaseModel, ConfigDict, Field


class DisputeMcpModel(BaseModel):
    """Base class for every local response model in this package."""

    model_config = ConfigDict(extra="forbid")


class CaseRecord(DisputeMcpModel):
    case_id: str = Field(min_length=1)
    customer_id: str = Field(min_length=1)
    merchant_id: str = Field(min_length=1)
    transaction_id: str = Field(min_length=1)
    dispute_type: DisputeType
    status: str = Field(min_length=1)
    opened_at: datetime
    amount: Decimal
    currency: str


class TransactionRecord(DisputeMcpModel):
    transaction_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    customer_id: str = Field(min_length=1)
    merchant_id: str = Field(min_length=1)
    amount: Decimal
    currency: str
    posted_at: datetime
    description: str = Field(min_length=1)


class AuthorizationRecord(DisputeMcpModel):
    transaction_id: str = Field(min_length=1)
    authorization_code: str = Field(min_length=1)
    authorized_at: datetime
    amount: Decimal
    currency: str
    approved: bool


class SettlementRecord(DisputeMcpModel):
    transaction_id: str = Field(min_length=1)
    settlement_id: str = Field(min_length=1)
    settled_at: datetime
    amount: Decimal
    currency: str


class RefundOrReversalRecord(DisputeMcpModel):
    transaction_id: str = Field(min_length=1)
    refund_id: str = Field(min_length=1)
    refunded_at: datetime
    amount: Decimal
    currency: str
    reason: str = Field(min_length=1)


class CustomerProfileRecord(DisputeMcpModel):
    customer_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    email: str = Field(min_length=1)
    customer_since: datetime
    tenure_days: int = Field(ge=0)


class PriorDisputeRecord(DisputeMcpModel):
    dispute_id: str = Field(min_length=1)
    customer_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    dispute_type: DisputeType
    outcome: str = Field(min_length=1)
    resolved_at: datetime


class RefundHistoryEntry(DisputeMcpModel):
    refund_id: str = Field(min_length=1)
    customer_id: str = Field(min_length=1)
    transaction_id: str = Field(min_length=1)
    amount: Decimal
    currency: str
    refunded_at: datetime


class MerchantEvidenceRecord(DisputeMcpModel):
    case_id: str = Field(min_length=1)
    merchant_id: str = Field(min_length=1)
    acknowledgement: bool
    evidence_summary: str = Field(min_length=1)
    submitted_at: datetime


class DeliveryDetailsRecord(DisputeMcpModel):
    case_id: str = Field(min_length=1)
    delivered: bool
    delivery_date: datetime | None = None
    carrier: str | None = None
    tracking_number: str | None = None


class CancellationDetailsRecord(DisputeMcpModel):
    case_id: str = Field(min_length=1)
    cancelled: bool
    cancellation_date: datetime | None = None
    confirmation_reference: str | None = None


class AuditRecord(DisputeMcpModel):
    audit_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    event_description: str = Field(min_length=1)
    recorded_at: datetime
    idempotency_key: str = Field(min_length=1)
