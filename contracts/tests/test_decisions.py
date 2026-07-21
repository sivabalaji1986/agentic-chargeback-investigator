"""Tests for chargeback_contracts.decisions."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from chargeback_contracts.a2ui import InvestigatorAction
from chargeback_contracts.decisions import InvestigatorDecision
from chargeback_contracts.recommendation import RecommendationType


def _valid_decision(**overrides: object) -> InvestigatorDecision:
    defaults: dict[str, object] = {
        "decision_id": "DEC-1",
        "investigation_id": "INV-1",
        "case_id": "CASE-1",
        "investigator_id": "inv-jane",
        "selected_action": InvestigatorAction.APPROVE_RECOMMENDATION,
        "recommendation_shown": RecommendationType.ACCEPT_CHARGEBACK,
        "decided_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }
    defaults.update(overrides)
    return InvestigatorDecision(**defaults)  # type: ignore[arg-type]


def test_valid_decision_round_trips_through_json() -> None:
    decision = _valid_decision()
    restored = InvestigatorDecision.model_validate_json(decision.model_dump_json())
    assert restored == decision


def test_requires_explicit_investigator_id() -> None:
    with pytest.raises(ValidationError):
        _valid_decision(investigator_id="   ")


def test_requires_decision_timestamp() -> None:
    with pytest.raises(ValidationError):
        _valid_decision(decided_at=None)


def test_rejects_naive_decided_at() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        _valid_decision(decided_at=datetime(2026, 1, 1))  # noqa: DTZ001


def test_comments_are_optional() -> None:
    decision = _valid_decision()
    assert decision.comments is None


def test_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError):
        _valid_decision(unexpected_field="nope")
