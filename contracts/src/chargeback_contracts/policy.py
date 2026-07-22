"""Policy interpretation contracts.

The Policy Agent interprets policy but never decides the final
recommendation — enforced structurally by this module defining no
recommendation field, and by running only after the evidence specialists
(see chargeback_contracts.skills.required_skills_for).
"""

from __future__ import annotations

from pydantic import Field, ValidationInfo, field_validator

from chargeback_contracts.common import ContractModel, require_non_blank
from chargeback_contracts.evidence import EvidenceType
from chargeback_contracts.skills import DisputeType


class PolicyInterpretation(ContractModel):
    """The Policy specialist's interpretation of applicable chargeback policy."""

    investigation_id: str = Field(min_length=1)
    dispute_type: DisputeType
    policy_version: str = Field(min_length=1)
    cited_sections: tuple[str, ...] = ()
    applicable_rules: tuple[str, ...] = ()
    required_evidence: tuple[EvidenceType, ...] = ()
    satisfied_evidence: tuple[EvidenceType, ...] = ()
    missing_evidence: tuple[EvidenceType, ...] = ()
    exceptions_or_escalations: tuple[str, ...] = ()
    interpretation_summary: str = Field(min_length=1)
    source_references: tuple[str, ...] = ()
    producing_agent_id: str = Field(min_length=1)
    a2a_task_id: str | None = None
    a2a_context_id: str | None = None

    @field_validator(
        "investigation_id", "policy_version", "interpretation_summary", "producing_agent_id"
    )
    @classmethod
    def _non_blank(cls, value: str, info: ValidationInfo) -> str:
        assert info.field_name is not None
        return require_non_blank(value, field_name=info.field_name)

    @field_validator("a2a_task_id", "a2a_context_id")
    @classmethod
    def _blank_a2a_ids(cls, value: str | None, info: ValidationInfo) -> str | None:
        if value is not None:
            assert info.field_name is not None
            return require_non_blank(value, field_name=info.field_name)
        return value
