"""Deterministic, internally-consistent seeded mock data.

Every ID below is stable and cross-referenced (case -> transaction ->
customer -> merchant) so later prompts can rely on the same identifiers.
This is the only place mock data is defined; repository.py only reads it.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from chargeback_contracts.skills import DisputeType
from dispute_mcp_server.models import (
    AuthorizationRecord,
    CancellationDetailsRecord,
    CaseRecord,
    CustomerProfileRecord,
    DeliveryDetailsRecord,
    MerchantEvidenceRecord,
    PriorDisputeRecord,
    RefundHistoryEntry,
    RefundOrReversalRecord,
    SettlementRecord,
    TransactionRecord,
)

CASES: dict[str, CaseRecord] = {
    "CASE-1001": CaseRecord(
        case_id="CASE-1001",
        customer_id="CUST-3001",
        merchant_id="MERCH-4001",
        transaction_id="TXN-2001",
        dispute_type=DisputeType.GOODS_NOT_RECEIVED,
        status="open",
        opened_at=datetime(2026, 6, 1, 9, 0, tzinfo=UTC),
        amount=Decimal("89.99"),
        currency="USD",
    ),
    "CASE-1002": CaseRecord(
        case_id="CASE-1002",
        customer_id="CUST-3002",
        merchant_id="MERCH-4001",
        transaction_id="TXN-2002",
        dispute_type=DisputeType.DUPLICATE_TRANSACTION,
        status="open",
        opened_at=datetime(2026, 6, 3, 14, 30, tzinfo=UTC),
        amount=Decimal("45.00"),
        currency="USD",
    ),
    "CASE-1003": CaseRecord(
        case_id="CASE-1003",
        customer_id="CUST-3003",
        merchant_id="MERCH-4002",
        transaction_id="TXN-2003",
        dispute_type=DisputeType.CANCELLED_SERVICE,
        status="open",
        opened_at=datetime(2026, 6, 5, 11, 15, tzinfo=UTC),
        amount=Decimal("120.50"),
        currency="USD",
    ),
}

TRANSACTIONS: dict[str, TransactionRecord] = {
    "TXN-2001": TransactionRecord(
        transaction_id="TXN-2001",
        case_id="CASE-1001",
        customer_id="CUST-3001",
        merchant_id="MERCH-4001",
        amount=Decimal("89.99"),
        currency="USD",
        posted_at=datetime(2026, 5, 28, 10, 5, tzinfo=UTC),
        description="Online purchase - Widget Pro",
    ),
    "TXN-2002": TransactionRecord(
        transaction_id="TXN-2002",
        case_id="CASE-1002",
        customer_id="CUST-3002",
        merchant_id="MERCH-4001",
        amount=Decimal("45.00"),
        currency="USD",
        posted_at=datetime(2026, 6, 1, 8, 40, tzinfo=UTC),
        description="Online purchase - Accessory Bundle",
    ),
    "TXN-2003": TransactionRecord(
        transaction_id="TXN-2003",
        case_id="CASE-1003",
        customer_id="CUST-3003",
        merchant_id="MERCH-4002",
        amount=Decimal("120.50"),
        currency="USD",
        posted_at=datetime(2026, 5, 20, 16, 0, tzinfo=UTC),
        description="Subscription service - Annual Plan",
    ),
}

AUTHORIZATIONS: dict[str, AuthorizationRecord] = {
    "TXN-2001": AuthorizationRecord(
        transaction_id="TXN-2001",
        authorization_code="AUTH-9001",
        authorized_at=datetime(2026, 5, 28, 10, 4, tzinfo=UTC),
        amount=Decimal("89.99"),
        currency="USD",
        approved=True,
    ),
    "TXN-2002": AuthorizationRecord(
        transaction_id="TXN-2002",
        authorization_code="AUTH-9002",
        authorized_at=datetime(2026, 6, 1, 8, 39, tzinfo=UTC),
        amount=Decimal("45.00"),
        currency="USD",
        approved=True,
    ),
    "TXN-2003": AuthorizationRecord(
        transaction_id="TXN-2003",
        authorization_code="AUTH-9003",
        authorized_at=datetime(2026, 5, 20, 15, 59, tzinfo=UTC),
        amount=Decimal("120.50"),
        currency="USD",
        approved=True,
    ),
}

SETTLEMENTS: dict[str, SettlementRecord] = {
    "TXN-2001": SettlementRecord(
        transaction_id="TXN-2001",
        settlement_id="SETL-8001",
        settled_at=datetime(2026, 5, 29, 2, 0, tzinfo=UTC),
        amount=Decimal("89.99"),
        currency="USD",
    ),
    "TXN-2002": SettlementRecord(
        transaction_id="TXN-2002",
        settlement_id="SETL-8002",
        settled_at=datetime(2026, 6, 2, 2, 0, tzinfo=UTC),
        amount=Decimal("45.00"),
        currency="USD",
    ),
    "TXN-2003": SettlementRecord(
        transaction_id="TXN-2003",
        settlement_id="SETL-8003",
        settled_at=datetime(2026, 5, 21, 2, 0, tzinfo=UTC),
        amount=Decimal("120.50"),
        currency="USD",
    ),
}

REFUNDS_OR_REVERSALS: dict[str, tuple[RefundOrReversalRecord, ...]] = {
    "TXN-2001": (),
    "TXN-2002": (
        RefundOrReversalRecord(
            transaction_id="TXN-2002",
            refund_id="REFUND-7001",
            refunded_at=datetime(2026, 6, 4, 9, 0, tzinfo=UTC),
            amount=Decimal("45.00"),
            currency="USD",
            reason="Duplicate charge reversed by merchant",
        ),
    ),
    "TXN-2003": (),
}

CUSTOMER_PROFILES: dict[str, CustomerProfileRecord] = {
    "CUST-3001": CustomerProfileRecord(
        customer_id="CUST-3001",
        display_name="Jane Doe",
        email="jane.doe@example.com",
        customer_since=datetime(2022, 3, 1, tzinfo=UTC),
        tenure_days=1584,
    ),
    "CUST-3002": CustomerProfileRecord(
        customer_id="CUST-3002",
        display_name="John Smith",
        email="john.smith@example.com",
        customer_since=datetime(2023, 7, 15, tzinfo=UTC),
        tenure_days=1082,
    ),
    "CUST-3003": CustomerProfileRecord(
        customer_id="CUST-3003",
        display_name="Amara Chen",
        email="amara.chen@example.com",
        customer_since=datetime(2020, 11, 20, tzinfo=UTC),
        tenure_days=1979,
    ),
}

PRIOR_DISPUTES: dict[str, tuple[PriorDisputeRecord, ...]] = {
    "CUST-3001": (
        PriorDisputeRecord(
            dispute_id="PRIORDISP-5001",
            customer_id="CUST-3001",
            case_id="CASE-0501",
            dispute_type=DisputeType.MERCHANT_ERROR,
            outcome="reject_chargeback",
            resolved_at=datetime(2025, 9, 10, tzinfo=UTC),
        ),
    ),
    "CUST-3002": (),
    "CUST-3003": (
        PriorDisputeRecord(
            dispute_id="PRIORDISP-5002",
            customer_id="CUST-3003",
            case_id="CASE-0502",
            dispute_type=DisputeType.CARD_NOT_PRESENT_FRAUD,
            outcome="accept_chargeback",
            resolved_at=datetime(2024, 12, 2, tzinfo=UTC),
        ),
        PriorDisputeRecord(
            dispute_id="PRIORDISP-5003",
            customer_id="CUST-3003",
            case_id="CASE-0503",
            dispute_type=DisputeType.GOODS_NOT_RECEIVED,
            outcome="request_more_evidence",
            resolved_at=datetime(2025, 3, 18, tzinfo=UTC),
        ),
    ),
}

REFUND_HISTORY: dict[str, tuple[RefundHistoryEntry, ...]] = {
    "CUST-3001": (
        RefundHistoryEntry(
            refund_id="REFUNDHIST-6001",
            customer_id="CUST-3001",
            transaction_id="TXN-1501",
            amount=Decimal("15.00"),
            currency="USD",
            refunded_at=datetime(2025, 11, 1, tzinfo=UTC),
        ),
    ),
    "CUST-3002": (),
    "CUST-3003": (
        RefundHistoryEntry(
            refund_id="REFUNDHIST-6002",
            customer_id="CUST-3003",
            transaction_id="TXN-1502",
            amount=Decimal("30.00"),
            currency="USD",
            refunded_at=datetime(2025, 4, 22, tzinfo=UTC),
        ),
    ),
}

MERCHANT_EVIDENCE: dict[str, MerchantEvidenceRecord] = {
    "CASE-1001": MerchantEvidenceRecord(
        case_id="CASE-1001",
        merchant_id="MERCH-4001",
        acknowledgement=False,
        evidence_summary="Merchant has not responded to the evidence request.",
        submitted_at=datetime(2026, 6, 2, tzinfo=UTC),
    ),
    "CASE-1002": MerchantEvidenceRecord(
        case_id="CASE-1002",
        merchant_id="MERCH-4001",
        acknowledgement=True,
        evidence_summary="Merchant confirms the duplicate charge and has reversed it.",
        submitted_at=datetime(2026, 6, 4, tzinfo=UTC),
    ),
    "CASE-1003": MerchantEvidenceRecord(
        case_id="CASE-1003",
        merchant_id="MERCH-4002",
        acknowledgement=True,
        evidence_summary=(
            "Merchant acknowledges the cancellation request but has not yet uploaded confirmation."
        ),
        submitted_at=datetime(2026, 6, 6, tzinfo=UTC),
    ),
}

DELIVERY_DETAILS: dict[str, DeliveryDetailsRecord] = {
    "CASE-1001": DeliveryDetailsRecord(
        case_id="CASE-1001",
        delivered=False,
        delivery_date=None,
        carrier=None,
        tracking_number=None,
    ),
    "CASE-1002": DeliveryDetailsRecord(
        case_id="CASE-1002",
        delivered=True,
        delivery_date=datetime(2026, 6, 1, 18, 0, tzinfo=UTC),
        carrier="ParcelSwift",
        tracking_number="PS-773311",
    ),
    "CASE-1003": DeliveryDetailsRecord(
        case_id="CASE-1003",
        delivered=True,
        delivery_date=datetime(2026, 5, 20, 16, 30, tzinfo=UTC),
        carrier=None,
        tracking_number=None,
    ),
}

CANCELLATION_DETAILS: dict[str, CancellationDetailsRecord] = {
    "CASE-1001": CancellationDetailsRecord(
        case_id="CASE-1001",
        cancelled=False,
        cancellation_date=None,
        confirmation_reference=None,
    ),
    "CASE-1002": CancellationDetailsRecord(
        case_id="CASE-1002",
        cancelled=False,
        cancellation_date=None,
        confirmation_reference=None,
    ),
    "CASE-1003": CancellationDetailsRecord(
        case_id="CASE-1003",
        cancelled=True,
        cancellation_date=datetime(2026, 6, 4, 12, 0, tzinfo=UTC),
        confirmation_reference="CANCEL-CONF-7788",
    ),
}
