"""Tests for chargeback_contracts.evidence."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from chargeback_contracts.evidence import EvidenceRef, EvidenceType


def _valid_evidence_ref(**overrides: object) -> EvidenceRef:
    defaults: dict[str, object] = {
        "evidence_id": "EVID-1",
        "case_id": "CASE-1",
        "evidence_type": EvidenceType.RECEIPT,
        "display_name": "receipt.pdf",
        "media_type": "application/pdf",
        "uri": "evidence://case-1/receipt.pdf",
        "uploaded_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "source": "web_form",
    }
    defaults.update(overrides)
    return EvidenceRef(**defaults)  # type: ignore[arg-type]


def test_valid_evidence_ref_round_trips_through_json() -> None:
    ref = _valid_evidence_ref()
    restored = EvidenceRef.model_validate_json(ref.model_dump_json())
    assert restored == ref


def test_evidence_type_stable_values() -> None:
    assert EvidenceType.CUSTOMER_DECLARATION.value == "customer_declaration"
    assert EvidenceType.TRANSACTION_STATEMENT.value == "transaction_statement"
    assert EvidenceType.MERCHANT_EMAIL.value == "merchant_email"
    assert EvidenceType.MERCHANT_CHAT.value == "merchant_chat"
    assert EvidenceType.RECEIPT.value == "receipt"
    assert EvidenceType.INVOICE.value == "invoice"
    assert EvidenceType.CANCELLATION_CONFIRMATION.value == "cancellation_confirmation"
    assert EvidenceType.DELIVERY_PROOF.value == "delivery_proof"
    assert EvidenceType.REFUND_REQUEST.value == "refund_request"
    assert EvidenceType.POLICE_REPORT.value == "police_report"
    assert EvidenceType.SCREENSHOT.value == "screenshot"
    assert EvidenceType.OTHER.value == "other"


def test_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError):
        _valid_evidence_ref(unexpected_field="nope")


def test_rejects_local_filesystem_path() -> None:
    with pytest.raises(ValidationError, match="evidence uri must use one of"):
        _valid_evidence_ref(uri="/etc/passwd")


def test_rejects_file_scheme() -> None:
    with pytest.raises(ValidationError, match="evidence uri must use one of"):
        _valid_evidence_ref(uri="file:///etc/passwd")


def test_rejects_path_traversal_within_evidence_scheme() -> None:
    with pytest.raises(ValidationError, match="path traversal"):
        _valid_evidence_ref(uri="evidence://case-1/../../../etc/passwd")


def test_rejects_blank_evidence_id() -> None:
    with pytest.raises(ValidationError):
        _valid_evidence_ref(evidence_id="   ")


def test_rejects_naive_uploaded_at() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        _valid_evidence_ref(uploaded_at=datetime(2026, 1, 1))  # noqa: DTZ001
