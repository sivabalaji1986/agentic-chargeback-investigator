"""Tests for chargeback_contracts.a2ui."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from chargeback_contracts.a2ui import (
    A2UI_VERSION,
    A2uiEnvelope,
    ApprovalPreview,
    DecisionCard,
    FinalDecisionConfirmation,
    InvestigatorAction,
)
from chargeback_contracts.recommendation import RecommendationType


def _valid_envelope(**overrides: object) -> A2uiEnvelope:
    defaults: dict[str, object] = {
        "version": A2UI_VERSION,
        "surface_id": "decision-surface-1",
        "investigation_id": "INV-1",
        "components": (
            DecisionCard(
                investigation_id="INV-1",
                recommendation=RecommendationType.ACCEPT_CHARGEBACK,
                explanation="Evidence supports acceptance.",
            ),
        ),
        "allowed_actions": (InvestigatorAction.APPROVE_RECOMMENDATION,),
        "generated_at": datetime(2026, 1, 1, tzinfo=UTC),
    }
    defaults.update(overrides)
    return A2uiEnvelope(**defaults)  # type: ignore[arg-type]


def test_valid_envelope_round_trips_through_json() -> None:
    envelope = _valid_envelope()
    restored = A2uiEnvelope.model_validate_json(envelope.model_dump_json())
    assert restored == envelope
    assert type(restored.components[0]) is DecisionCard


def test_version_must_be_exactly_0_9() -> None:
    with pytest.raises(ValidationError):
        _valid_envelope(version="1.0")


def test_allowed_actions_are_human_decisions_only() -> None:
    envelope = _valid_envelope()
    assert all(isinstance(a, InvestigatorAction) for a in envelope.allowed_actions)


def test_discriminated_components_round_trip_for_final_decision_confirmation() -> None:
    envelope = _valid_envelope(
        components=(
            FinalDecisionConfirmation(
                investigation_id="INV-1",
                decision_id="DEC-1",
                action=InvestigatorAction.APPROVE_RECOMMENDATION,
                confirmed_at=datetime(2026, 1, 1, tzinfo=UTC),
            ),
        )
    )
    restored = A2uiEnvelope.model_validate_json(envelope.model_dump_json())
    assert type(restored.components[0]) is FinalDecisionConfirmation


def test_discriminated_components_round_trip_for_approval_preview() -> None:
    envelope = _valid_envelope(
        components=(
            ApprovalPreview(
                investigation_id="INV-1",
                recommendation=RecommendationType.REJECT_CHARGEBACK,
                summary="Policy does not support this claim.",
            ),
        )
    )
    restored = A2uiEnvelope.model_validate_json(envelope.model_dump_json())
    assert type(restored.components[0]) is ApprovalPreview


def test_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError):
        _valid_envelope(unexpected_field="nope")


def test_investigator_action_stable_values() -> None:
    assert InvestigatorAction.APPROVE_RECOMMENDATION.value == "approve_recommendation"
    assert InvestigatorAction.REJECT_RECOMMENDATION.value == "reject_recommendation"
    assert InvestigatorAction.REQUEST_MORE_EVIDENCE.value == "request_more_evidence"
