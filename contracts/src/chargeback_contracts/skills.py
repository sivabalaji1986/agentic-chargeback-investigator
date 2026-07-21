"""Skill identifiers, dispute types, and the deterministic mapping between
them.

This module represents the dependency between evidence specialists and the
Policy specialist declaratively — it does not execute orchestration.
"""

from __future__ import annotations

from enum import StrEnum


class SkillId(StrEnum):
    """Stable skill identifiers shared by the Agent Registry, agents, and Orchestrator."""

    TRANSACTION_INVESTIGATION = "transaction-investigation"
    CUSTOMER_HISTORY_INVESTIGATION = "customer-history-investigation"
    MERCHANT_EVIDENCE_INVESTIGATION = "merchant-evidence-investigation"
    CHARGEBACK_POLICY_INTERPRETATION = "chargeback-policy-interpretation"
    DUPLICATE_TRANSACTION_INVESTIGATION = "duplicate-transaction-investigation"


class DisputeType(StrEnum):
    """Supported initial chargeback dispute classifications."""

    GOODS_NOT_RECEIVED = "goods_not_received"
    DUPLICATE_TRANSACTION = "duplicate_transaction"
    CANCELLED_SERVICE = "cancelled_service"
    MERCHANT_ERROR = "merchant_error"
    CARD_NOT_PRESENT_FRAUD = "card_not_present_fraud"
    OTHER = "other"


CORE_EVIDENCE_SKILL_IDS: frozenset[SkillId] = frozenset(
    {
        SkillId.TRANSACTION_INVESTIGATION,
        SkillId.CUSTOMER_HISTORY_INVESTIGATION,
        SkillId.MERCHANT_EVIDENCE_INVESTIGATION,
    }
)

POLICY_SKILL_ID: SkillId = SkillId.CHARGEBACK_POLICY_INTERPRETATION

DUPLICATE_TRANSACTION_SKILL_ID: SkillId = SkillId.DUPLICATE_TRANSACTION_INVESTIGATION

_DISPUTE_TYPE_MAPPED_SKILLS: dict[DisputeType, tuple[SkillId, ...]] = {
    DisputeType.GOODS_NOT_RECEIVED: (
        SkillId.TRANSACTION_INVESTIGATION,
        SkillId.CUSTOMER_HISTORY_INVESTIGATION,
        SkillId.MERCHANT_EVIDENCE_INVESTIGATION,
    ),
    DisputeType.DUPLICATE_TRANSACTION: (
        SkillId.TRANSACTION_INVESTIGATION,
        SkillId.DUPLICATE_TRANSACTION_INVESTIGATION,
    ),
    DisputeType.CANCELLED_SERVICE: (
        SkillId.TRANSACTION_INVESTIGATION,
        SkillId.MERCHANT_EVIDENCE_INVESTIGATION,
    ),
    DisputeType.MERCHANT_ERROR: (
        SkillId.TRANSACTION_INVESTIGATION,
        SkillId.MERCHANT_EVIDENCE_INVESTIGATION,
    ),
    DisputeType.CARD_NOT_PRESENT_FRAUD: (
        SkillId.TRANSACTION_INVESTIGATION,
        SkillId.CUSTOMER_HISTORY_INVESTIGATION,
    ),
    DisputeType.OTHER: (SkillId.TRANSACTION_INVESTIGATION,),
}


def required_skills_for(
    dispute_type: DisputeType, *, include_policy: bool = True
) -> tuple[SkillId, ...]:
    """Return the deterministic skill IDs required to investigate a dispute type.

    The evidence-specialist skills always run first; the Policy skill (when
    ``include_policy`` is true, the default) is appended last, since Policy
    interprets findings only after the evidence specialists have reported.
    """
    mapped = _DISPUTE_TYPE_MAPPED_SKILLS[dispute_type]
    if include_policy:
        return (*mapped, POLICY_SKILL_ID)
    return mapped
