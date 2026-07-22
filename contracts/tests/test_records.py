"""Tests for chargeback_contracts.records."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from chargeback_contracts.a2ui import InvestigatorAction
from chargeback_contracts.decisions import InvestigatorDecision
from chargeback_contracts.dispute import InvestigationRequest, SourceChannel
from chargeback_contracts.recommendation import RecommendationType
from chargeback_contracts.records import InvestigationRecord, WorkflowStatus
from chargeback_contracts.skills import DisputeType
from pydantic import ValidationError


def _base_request() -> InvestigationRequest:
    return InvestigationRequest(
        investigation_id="INV-1",
        case_id="CASE-1",
        transaction_id="TXN-1",
        source_channel=SourceChannel.WEB_FORM,
        customer_narrative="Item never arrived.",
        dispute_type=DisputeType.GOODS_NOT_RECEIVED,
        amount=Decimal("50.00"),
        currency="USD",
        submitted_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def _decision() -> InvestigatorDecision:
    return InvestigatorDecision(
        decision_id="DEC-1",
        investigation_id="INV-1",
        case_id="CASE-1",
        investigator_id="inv-jane",
        selected_action=InvestigatorAction.APPROVE_RECOMMENDATION,
        recommendation_shown=RecommendationType.ACCEPT_CHARGEBACK,
        decided_at=datetime(2026, 1, 2, tzinfo=UTC),
    )


def test_completed_record_requires_investigator_decision() -> None:
    with pytest.raises(ValidationError, match="requires an InvestigatorDecision"):
        InvestigationRecord(
            request=_base_request(),
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
            completed_at=datetime(2026, 1, 2, tzinfo=UTC),
            status=WorkflowStatus.COMPLETED,
            audit_correlation_id="AUD-1",
        )


def test_completed_record_with_decision_is_valid_and_round_trips() -> None:
    record = InvestigationRecord(
        request=_base_request(),
        investigator_decision=_decision(),
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        completed_at=datetime(2026, 1, 2, tzinfo=UTC),
        status=WorkflowStatus.COMPLETED,
        audit_correlation_id="AUD-1",
    )
    restored = InvestigationRecord.model_validate_json(record.model_dump_json())
    assert restored == record


def test_partial_record_without_decision_is_valid() -> None:
    record = InvestigationRecord(
        request=_base_request(),
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        status=WorkflowStatus.PARTIAL,
        audit_correlation_id="AUD-1",
    )
    assert record.investigator_decision is None
    assert record.status == WorkflowStatus.PARTIAL


def test_failed_record_without_decision_is_valid() -> None:
    record = InvestigationRecord(
        request=_base_request(),
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        status=WorkflowStatus.FAILED,
        audit_correlation_id="AUD-1",
    )
    assert record.status == WorkflowStatus.FAILED


def test_completed_at_cannot_precede_created_at() -> None:
    with pytest.raises(ValidationError, match="cannot precede created_at"):
        InvestigationRecord(
            request=_base_request(),
            investigator_decision=_decision(),
            created_at=datetime(2026, 1, 2, tzinfo=UTC),
            completed_at=datetime(2026, 1, 1, tzinfo=UTC),
            status=WorkflowStatus.COMPLETED,
            audit_correlation_id="AUD-1",
        )


def test_rejects_blank_audit_correlation_id() -> None:
    with pytest.raises(ValidationError, match="must not be blank"):
        InvestigationRecord(
            request=_base_request(),
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
            status=WorkflowStatus.IN_PROGRESS,
            audit_correlation_id="   ",
        )


def test_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError):
        InvestigationRecord(  # type: ignore[call-arg]
            request=_base_request(),
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
            status=WorkflowStatus.IN_PROGRESS,
            audit_correlation_id="AUD-1",
            unexpected_field="nope",
        )
