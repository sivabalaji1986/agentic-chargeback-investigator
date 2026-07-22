"""Compatibility tests against the real, official A2A SDK types.

Spec requirement #18 ("compatibility with official A2A identifiers/types used
by the contracts") is not satisfied by round-tripping our own contract
models through JSON, since that only ever exercises our own string fields
against each other. These tests instead construct real `a2a.types.Task` /
`a2a.types.Message` objects -- the protobuf-backed classes shipped by the
`a2a-sdk` dependency -- and feed their genuine `.id` / `.context_id` values
into our `a2a_task_id` / `a2a_context_id` contract fields. This proves the
two are actually interoperable (both are plain strings at the wire level),
not merely assumed to be compatible because they share a name.
"""

from __future__ import annotations

from datetime import UTC, datetime

from a2a.types import Message, Role, Task
from chargeback_contracts.a2ui import InvestigatorAction
from chargeback_contracts.decisions import InvestigatorDecision
from chargeback_contracts.findings import (
    FindingStatus,
    SpecialistFinding,
    TransactionFindingDetails,
)
from chargeback_contracts.recommendation import RecommendationType
from chargeback_contracts.skills import SkillId


def test_real_a2a_task_and_message_ids_feed_specialist_finding() -> None:
    # Real, protobuf-backed A2A SDK objects -- not a mock or a local lookalike.
    task = Task(id="task-1", context_id="ctx-1")
    message = Message(
        message_id="msg-1",
        context_id="ctx-1",
        task_id="task-1",
        role=Role.ROLE_AGENT,
        parts=[],
    )
    assert message.task_id == task.id
    assert message.context_id == task.context_id

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
        a2a_task_id=task.id,
        a2a_context_id=task.context_id,
    )
    restored = SpecialistFinding.model_validate_json(finding.model_dump_json())
    assert restored == finding
    assert restored.a2a_task_id == task.id
    assert restored.a2a_context_id == task.context_id


def test_real_a2a_task_id_and_context_id_feed_investigator_decision() -> None:
    # Real, protobuf-backed A2A SDK object.
    task = Task(id="task-2", context_id="ctx-2")

    decision = InvestigatorDecision(
        decision_id="DEC-1",
        investigation_id="INV-1",
        case_id="CASE-1",
        investigator_id="inv-jane",
        selected_action=InvestigatorAction.APPROVE_RECOMMENDATION,
        recommendation_shown=RecommendationType.ACCEPT_CHARGEBACK,
        decided_at=datetime(2026, 1, 1, tzinfo=UTC),
        a2a_task_id=task.id,
        a2a_context_id=task.context_id,
    )
    restored = InvestigatorDecision.model_validate_json(decision.model_dump_json())
    assert restored == decision
    assert restored.a2a_task_id == "task-2"
    assert restored.a2a_context_id == "ctx-2"
