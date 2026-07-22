"""Tests for the chargeback_contracts public import surface."""

import chargeback_contracts as contracts


def test_module_imports() -> None:
    assert contracts is not None


def test_every_declared_export_is_actually_importable() -> None:
    for name in contracts.__all__:
        assert hasattr(contracts, name), f"{name} is declared in __all__ but missing"


def test_no_duplicate_a2a_protocol_model_names_defined_locally() -> None:
    reserved_a2a_names = {
        "AgentCard",
        "AgentSkill",
        "Task",
        "Message",
        "Artifact",
        "Part",
        "TaskState",
    }
    assert reserved_a2a_names.isdisjoint(contracts.__all__)


def test_key_contracts_importable_from_package_root() -> None:
    assert contracts.InvestigationRequest is not None
    assert contracts.SpecialistFinding is not None
    assert contracts.PolicyInterpretation is not None
    assert contracts.InvestigationRecommendation is not None
    assert contracts.InvestigatorDecision is not None
    assert contracts.InvestigationRecord is not None
    assert contracts.A2uiEnvelope is not None
    assert contracts.A2UI_VERSION == "0.9"
