"""Tests for chargeback_contracts.agui."""

from datetime import datetime, timezone

from chargeback_contracts.agui import (
    ApprovalRequiredEvent,
    CapabilityDiscoveryCompletedEvent,
    CapabilityDiscoveryStartedEvent,
    ExplanationProducedEvent,
    InvestigationAcceptedEvent,
    InvestigationCompletedEvent,
    InvestigationFailedEvent,
    MissingCapabilityIdentifiedEvent,
    MissingEvidenceIdentifiedEvent,
    PolicyInterpretationReceivedEvent,
    RecommendationProducedEvent,
    SpecialistFindingReceivedEvent,
    SpecialistProgressEvent,
    SpecialistStartedEvent,
)
from chargeback_contracts.evidence import EvidenceType
from chargeback_contracts.recommendation import MissingCapabilityWarning, RecommendationType
from chargeback_contracts.skills import DisputeType, SkillId

_CORRELATION = {
    "investigation_id": "INV-1",
    "case_id": "CASE-1",
    "run_id": "RUN-1",
    "occurred_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
}


def test_all_fourteen_event_payloads_round_trip_through_json() -> None:
    events = [
        InvestigationAcceptedEvent(
            **_CORRELATION, dispute_type=DisputeType.GOODS_NOT_RECEIVED
        ),
        CapabilityDiscoveryStartedEvent(**_CORRELATION),
        CapabilityDiscoveryCompletedEvent(
            **_CORRELATION, discovered_skill_ids=(SkillId.TRANSACTION_INVESTIGATION,)
        ),
        SpecialistStartedEvent(**_CORRELATION),
        SpecialistProgressEvent(**_CORRELATION, message="Checking transaction records."),
        SpecialistFindingReceivedEvent(**_CORRELATION, finding_id="FIND-1"),
        MissingEvidenceIdentifiedEvent(
            **_CORRELATION, missing_evidence=(EvidenceType.DELIVERY_PROOF,)
        ),
        MissingCapabilityIdentifiedEvent(
            **_CORRELATION,
            warning=MissingCapabilityWarning(
                required_skill_id=SkillId.DUPLICATE_TRANSACTION_INVESTIGATION,
                message="Not registered yet.",
                can_continue_partially=True,
                affected_area="duplicate check",
                discovered_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            ),
        ),
        PolicyInterpretationReceivedEvent(**_CORRELATION),
        RecommendationProducedEvent(
            **_CORRELATION, recommendation=RecommendationType.ACCEPT_CHARGEBACK
        ),
        ExplanationProducedEvent(**_CORRELATION, explanation="Evidence supports the customer."),
        ApprovalRequiredEvent(**_CORRELATION),
        InvestigationCompletedEvent(**_CORRELATION, final_status="completed"),
        InvestigationFailedEvent(**_CORRELATION, reason="specialist timeout"),
    ]
    assert len(events) == 14
    for event in events:
        restored = type(event).model_validate_json(event.model_dump_json())
        assert restored == event


def test_event_name_is_stable_and_distinct_per_event() -> None:
    names = {
        InvestigationAcceptedEvent(
            **_CORRELATION, dispute_type=DisputeType.OTHER
        ).event_name,
        CapabilityDiscoveryStartedEvent(**_CORRELATION).event_name,
        CapabilityDiscoveryCompletedEvent(**_CORRELATION).event_name,
        SpecialistStartedEvent(**_CORRELATION).event_name,
        SpecialistProgressEvent(**_CORRELATION, message="x").event_name,
        SpecialistFindingReceivedEvent(**_CORRELATION, finding_id="F").event_name,
        MissingEvidenceIdentifiedEvent(**_CORRELATION).event_name,
        PolicyInterpretationReceivedEvent(**_CORRELATION).event_name,
        RecommendationProducedEvent(
            **_CORRELATION, recommendation=RecommendationType.REJECT_CHARGEBACK
        ).event_name,
        ExplanationProducedEvent(**_CORRELATION, explanation="x").event_name,
        ApprovalRequiredEvent(**_CORRELATION).event_name,
        InvestigationCompletedEvent(**_CORRELATION, final_status="completed").event_name,
        InvestigationFailedEvent(**_CORRELATION, reason="x").event_name,
    }
    assert len(names) == 13  # MissingCapabilityIdentifiedEvent omitted here for brevity; distinct-name check
