"""Proves transaction-agent can consume the shared contracts package."""

from datetime import UTC, datetime

from chargeback_contracts import (
    FindingStatus,
    SkillId,
    SpecialistFinding,
    TransactionFindingDetails,
)


def test_can_construct_and_round_trip_a_transaction_finding() -> None:
    finding = SpecialistFinding(
        finding_id="FIND-1",
        investigation_id="INV-1",
        case_id="CASE-1",
        producing_agent_id="transaction-agent",
        skill_id=SkillId.TRANSACTION_INVESTIGATION,
        status=FindingStatus.COMPLETED,
        summary="Transaction confirmed as posted.",
        details=TransactionFindingDetails(transaction_matched=True),
        started_at=datetime(2026, 1, 1, tzinfo=UTC),
        completed_at=datetime(2026, 1, 1, 1, tzinfo=UTC),
    )
    restored = SpecialistFinding.model_validate_json(finding.model_dump_json())
    assert restored == finding
