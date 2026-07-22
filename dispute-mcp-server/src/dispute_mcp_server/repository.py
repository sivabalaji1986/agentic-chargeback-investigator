"""Repository layer: owns seeded data behind typed lookup methods.

No business decisions happen here — only reads, and the two narrow
mutations (case status, audit log) that update_case/write_audit need.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from dispute_mcp_server import seed_data
from dispute_mcp_server.models import (
    AuditRecord,
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


class NotFoundError(Exception):
    """Raised when a requested identifier has no seeded record."""


class DisputeRepository:
    """In-memory repository over the seeded mock data.

    Mutations (update_case_status, append_audit_record) only affect this
    process's in-memory copy — no persistence across restarts, since
    nothing in this prompt requires it.
    """

    def __init__(self) -> None:
        self._cases: dict[str, CaseRecord] = dict(seed_data.CASES)
        self._audit_log: list[AuditRecord] = []

    def get_case(self, case_id: str) -> CaseRecord:
        try:
            return self._cases[case_id]
        except KeyError:
            raise NotFoundError(f"case not found: {case_id}") from None

    def update_case_status(self, case_id: str, new_status: str) -> CaseRecord:
        current = self.get_case(case_id)
        updated = current.model_copy(update={"status": new_status})
        self._cases[case_id] = updated
        return updated

    def append_audit_record(
        self, case_id: str, event_description: str, idempotency_key: str
    ) -> AuditRecord:
        if case_id not in self._cases:
            raise NotFoundError(f"case not found: {case_id}")
        record = AuditRecord(
            audit_id=f"AUDIT-{uuid.uuid4().hex[:8]}",
            case_id=case_id,
            event_description=event_description,
            recorded_at=datetime.now(UTC),
            idempotency_key=idempotency_key,
        )
        self._audit_log.append(record)
        return record

    def get_transaction(self, transaction_id: str) -> TransactionRecord:
        try:
            return seed_data.TRANSACTIONS[transaction_id]
        except KeyError:
            raise NotFoundError(f"transaction not found: {transaction_id}") from None

    def get_authorization(self, transaction_id: str) -> AuthorizationRecord:
        try:
            return seed_data.AUTHORIZATIONS[transaction_id]
        except KeyError:
            raise NotFoundError(f"transaction not found: {transaction_id}") from None

    def get_settlement(self, transaction_id: str) -> SettlementRecord:
        try:
            return seed_data.SETTLEMENTS[transaction_id]
        except KeyError:
            raise NotFoundError(f"transaction not found: {transaction_id}") from None

    def get_refunds_or_reversals(self, transaction_id: str) -> tuple[RefundOrReversalRecord, ...]:
        try:
            return seed_data.REFUNDS_OR_REVERSALS[transaction_id]
        except KeyError:
            raise NotFoundError(f"transaction not found: {transaction_id}") from None

    def get_customer_profile(self, customer_id: str) -> CustomerProfileRecord:
        try:
            return seed_data.CUSTOMER_PROFILES[customer_id]
        except KeyError:
            raise NotFoundError(f"customer not found: {customer_id}") from None

    def get_prior_disputes(self, customer_id: str) -> tuple[PriorDisputeRecord, ...]:
        if customer_id not in seed_data.CUSTOMER_PROFILES:
            raise NotFoundError(f"customer not found: {customer_id}")
        return seed_data.PRIOR_DISPUTES.get(customer_id, ())

    def get_refund_history(self, customer_id: str) -> tuple[RefundHistoryEntry, ...]:
        if customer_id not in seed_data.CUSTOMER_PROFILES:
            raise NotFoundError(f"customer not found: {customer_id}")
        return seed_data.REFUND_HISTORY.get(customer_id, ())

    def get_merchant_evidence(self, case_id: str) -> MerchantEvidenceRecord:
        try:
            return seed_data.MERCHANT_EVIDENCE[case_id]
        except KeyError:
            raise NotFoundError(f"case not found: {case_id}") from None

    def get_delivery_details(self, case_id: str) -> DeliveryDetailsRecord:
        try:
            return seed_data.DELIVERY_DETAILS[case_id]
        except KeyError:
            raise NotFoundError(f"case not found: {case_id}") from None

    def get_cancellation_details(self, case_id: str) -> CancellationDetailsRecord:
        try:
            return seed_data.CANCELLATION_DETAILS[case_id]
        except KeyError:
            raise NotFoundError(f"case not found: {case_id}") from None
