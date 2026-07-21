"""Tests for chargeback_contracts.skills."""

from chargeback_contracts.skills import (
    CORE_EVIDENCE_SKILL_IDS,
    DUPLICATE_TRANSACTION_SKILL_ID,
    POLICY_SKILL_ID,
    DisputeType,
    SkillId,
    required_skills_for,
)


def test_skill_id_stable_values() -> None:
    assert SkillId.TRANSACTION_INVESTIGATION.value == "transaction-investigation"
    assert SkillId.CUSTOMER_HISTORY_INVESTIGATION.value == "customer-history-investigation"
    assert SkillId.MERCHANT_EVIDENCE_INVESTIGATION.value == "merchant-evidence-investigation"
    assert SkillId.CHARGEBACK_POLICY_INTERPRETATION.value == "chargeback-policy-interpretation"
    assert (
        SkillId.DUPLICATE_TRANSACTION_INVESTIGATION.value
        == "duplicate-transaction-investigation"
    )


def test_dispute_type_stable_values() -> None:
    assert DisputeType.GOODS_NOT_RECEIVED.value == "goods_not_received"
    assert DisputeType.DUPLICATE_TRANSACTION.value == "duplicate_transaction"
    assert DisputeType.CANCELLED_SERVICE.value == "cancelled_service"
    assert DisputeType.MERCHANT_ERROR.value == "merchant_error"
    assert DisputeType.CARD_NOT_PRESENT_FRAUD.value == "card_not_present_fraud"
    assert DisputeType.OTHER.value == "other"


def test_core_evidence_skill_ids_excludes_policy_and_duplicate() -> None:
    assert POLICY_SKILL_ID not in CORE_EVIDENCE_SKILL_IDS
    assert DUPLICATE_TRANSACTION_SKILL_ID not in CORE_EVIDENCE_SKILL_IDS
    assert len(CORE_EVIDENCE_SKILL_IDS) == 3


def test_required_skills_for_appends_policy_last_by_default() -> None:
    skills = required_skills_for(DisputeType.GOODS_NOT_RECEIVED)
    assert skills[-1] == POLICY_SKILL_ID
    assert skills[:-1] == (
        SkillId.TRANSACTION_INVESTIGATION,
        SkillId.CUSTOMER_HISTORY_INVESTIGATION,
        SkillId.MERCHANT_EVIDENCE_INVESTIGATION,
    )


def test_required_skills_for_can_exclude_policy() -> None:
    skills = required_skills_for(DisputeType.OTHER, include_policy=False)
    assert skills == (SkillId.TRANSACTION_INVESTIGATION,)


def test_duplicate_transaction_dispute_requires_duplicate_skill() -> None:
    skills = required_skills_for(DisputeType.DUPLICATE_TRANSACTION, include_policy=False)
    assert DUPLICATE_TRANSACTION_SKILL_ID in skills
