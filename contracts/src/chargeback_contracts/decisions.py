"""Human-decision contracts.

No write-side MCP command may be represented as approved without an
InvestigatorDecision — this module is what makes human approval
explicit and mandatory rather than implied.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import Field, ValidationInfo, field_validator

from chargeback_contracts.a2ui import InvestigatorAction
from chargeback_contracts.common import ContractModel, require_non_blank, require_utc
from chargeback_contracts.recommendation import RecommendationType


class InvestigatorDecision(ContractModel):
    """A recorded human decision on an investigation's recommendation."""

    decision_id: str = Field(min_length=1)
    investigation_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    investigator_id: str = Field(min_length=1)
    selected_action: InvestigatorAction
    comments: str | None = None
    recommendation_shown: RecommendationType
    decided_at: datetime
    a2a_task_id: str | None = None
    a2a_context_id: str | None = None

    @field_validator("decision_id", "investigation_id", "case_id", "investigator_id")
    @classmethod
    def _non_blank(cls, value: str, info: ValidationInfo) -> str:
        assert info.field_name is not None
        return require_non_blank(value, field_name=info.field_name)

    @field_validator("decided_at")
    @classmethod
    def _decided_at(cls, value: datetime) -> datetime:
        return require_utc(value, field_name="decided_at")

    @field_validator("a2a_task_id", "a2a_context_id")
    @classmethod
    def _blank_a2a_ids(cls, value: str | None, info: ValidationInfo) -> str | None:
        if value is not None:
            assert info.field_name is not None
            return require_non_blank(value, field_name=info.field_name)
        return value
