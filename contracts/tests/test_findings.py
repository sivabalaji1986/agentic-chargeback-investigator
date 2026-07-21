"""Tests for chargeback_contracts.findings."""

from datetime import UTC, datetime

import pytest
from chargeback_contracts.findings import (
    CustomerHistoryFindingDetails,
    FindingStatus,
    MerchantEvidenceFindingDetails,
    SpecialistFinding,
    TransactionFindingDetails,
)
from chargeback_contracts.skills import SkillId
from pydantic import ValidationError


def _completed_finding(**overrides: object) -> SpecialistFinding:
    defaults: dict[str, object] = {
        "finding_id": "FIND-1",
        "investigation_id": "INV-1",
        "case_id": "CASE-1",
        "producing_agent_id": "transaction-agent",
        "skill_id": SkillId.TRANSACTION_INVESTIGATION,
        "status": FindingStatus.COMPLETED,
        "summary": "Transaction confirmed as posted.",
        "details": TransactionFindingDetails(transaction_matched=True),
        "started_at": datetime(2026, 1, 1, tzinfo=UTC),
        "completed_at": datetime(2026, 1, 1, 1, tzinfo=UTC),
    }
    defaults.update(overrides)
    return SpecialistFinding(**defaults)  # type: ignore[arg-type]


def test_completed_finding_round_trips_through_json() -> None:
    finding = _completed_finding()
    restored = SpecialistFinding.model_validate_json(finding.model_dump_json())
    assert restored == finding


def test_discriminated_details_round_trip_for_each_kind() -> None:
    customer_history = _completed_finding(
        skill_id=SkillId.CUSTOMER_HISTORY_INVESTIGATION,
        details=CustomerHistoryFindingDetails(previous_dispute_count=2, previous_refund_count=1),
    )
    merchant_evidence = _completed_finding(
        skill_id=SkillId.MERCHANT_EVIDENCE_INVESTIGATION,
        details=MerchantEvidenceFindingDetails(merchant_acknowledgement=True),
    )
    for finding in (customer_history, merchant_evidence):
        restored = SpecialistFinding.model_validate_json(finding.model_dump_json())
        assert restored == finding
        assert type(restored.details) is type(finding.details)


def test_finding_has_no_recommendation_field() -> None:
    assert "recommendation" not in SpecialistFinding.model_fields


def test_completed_status_requires_completed_at() -> None:
    with pytest.raises(ValidationError, match="require a completion timestamp"):
        _completed_finding(completed_at=None)


def test_completed_at_cannot_precede_started_at() -> None:
    with pytest.raises(ValidationError, match="cannot precede started_at"):
        _completed_finding(
            started_at=datetime(2026, 1, 2, tzinfo=UTC),
            completed_at=datetime(2026, 1, 1, tzinfo=UTC),
        )


def test_partial_status_requires_warnings_or_missing_evidence() -> None:
    with pytest.raises(ValidationError, match="warnings or missing evidence"):
        _completed_finding(
            status=FindingStatus.PARTIAL,
            completed_at=None,
            warnings=(),
            missing_evidence=(),
        )


def test_partial_status_accepts_warnings() -> None:
    finding = _completed_finding(
        status=FindingStatus.PARTIAL, completed_at=None, warnings=("delay",)
    )
    assert finding.status == FindingStatus.PARTIAL


def test_failed_status_requires_non_blank_summary() -> None:
    with pytest.raises(ValidationError):
        _completed_finding(status=FindingStatus.FAILED, completed_at=None, summary="   ")


def test_rejects_blank_a2a_task_id_when_supplied() -> None:
    with pytest.raises(ValidationError, match="must not be blank"):
        _completed_finding(a2a_task_id="   ")
