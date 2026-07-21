"""Tests for chargeback_contracts.policy."""

import pytest
from chargeback_contracts.evidence import EvidenceType
from chargeback_contracts.policy import PolicyInterpretation
from chargeback_contracts.skills import DisputeType
from pydantic import ValidationError


def _valid_interpretation(**overrides: object) -> PolicyInterpretation:
    defaults: dict[str, object] = {
        "investigation_id": "INV-1",
        "dispute_type": DisputeType.GOODS_NOT_RECEIVED,
        "policy_version": "2026.1",
        "required_evidence": (EvidenceType.DELIVERY_PROOF,),
        "missing_evidence": (EvidenceType.DELIVERY_PROOF,),
        "interpretation_summary": "Delivery proof required and not yet provided.",
        "producing_agent_id": "policy-agent",
    }
    defaults.update(overrides)
    return PolicyInterpretation(**defaults)  # type: ignore[arg-type]


def test_valid_interpretation_round_trips_through_json() -> None:
    interpretation = _valid_interpretation()
    restored = PolicyInterpretation.model_validate_json(interpretation.model_dump_json())
    assert restored == interpretation


def test_has_no_recommendation_field() -> None:
    assert "recommendation" not in PolicyInterpretation.model_fields


def test_rejects_blank_policy_version() -> None:
    with pytest.raises(ValidationError):
        _valid_interpretation(policy_version="   ")


def test_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError):
        _valid_interpretation(unexpected_field="nope")


def test_rejects_blank_a2a_task_id_when_supplied() -> None:
    with pytest.raises(ValidationError, match="must not be blank"):
        _valid_interpretation(a2a_task_id="   ")
