"""Core investigation run logic: builds the AG-UI event sequence and the
final A2UI decision-card envelope.

This is the reusable piece a future Orchestrator calls the same way this
prompt's endpoints do -- it has no dependency on how the run was
triggered, and does not look up data itself (the caller fetches
case/transaction data first, so a not-found case can be rejected before
any streaming response begins).
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime

from ag_ui.core import (
    CustomEvent,
    EventType,
    RunFinishedEvent,
    RunFinishedSuccessOutcome,
    RunStartedEvent,
)
from ag_ui.encoder import EventEncoder

from chargeback_contracts.a2ui import A2UI_VERSION, A2uiEnvelope, DecisionCard, InvestigatorAction
from chargeback_contracts.agui import (
    InvestigationAcceptedEvent,
    InvestigationCompletedEvent,
    RecommendationProducedEvent,
    SpecialistFindingReceivedEvent,
    SpecialistStartedEvent,
)
from chargeback_contracts.recommendation import RecommendationType
from chargeback_contracts.skills import DisputeType, SkillId
from transaction_agent.llm_client import ExplanationClient

MOCK_RECOMMENDATION = RecommendationType.REQUEST_MORE_EVIDENCE

_ENCODER = EventEncoder()


async def run_investigation(
    *,
    case_data: dict[str, object],
    transaction_data: dict[str, object],
    thread_id: str,
    run_id: str,
    explanation_client: ExplanationClient,
) -> AsyncIterator[str]:
    """Yield SSE-encoded AG-UI event strings for a single investigation run."""
    case_id = str(case_data["case_id"])
    dispute_type = DisputeType(str(case_data["dispute_type"]))

    yield _ENCODER.encode(RunStartedEvent(thread_id=thread_id, run_id=run_id))

    accepted = InvestigationAcceptedEvent(
        investigation_id=case_id,
        case_id=case_id,
        run_id=run_id,
        occurred_at=datetime.now(UTC),
        dispute_type=dispute_type,
        requested_skill_ids=(SkillId.TRANSACTION_INVESTIGATION,),
    )
    yield _ENCODER.encode(
        CustomEvent(
            type=EventType.CUSTOM, name=accepted.event_name, value=accepted.model_dump(mode="json")
        )
    )

    started = SpecialistStartedEvent(
        investigation_id=case_id,
        case_id=case_id,
        run_id=run_id,
        occurred_at=datetime.now(UTC),
        agent_id="transaction-agent",
        skill_id=SkillId.TRANSACTION_INVESTIGATION,
    )
    yield _ENCODER.encode(
        CustomEvent(
            type=EventType.CUSTOM, name=started.event_name, value=started.model_dump(mode="json")
        )
    )

    finding_id = f"FIND-{uuid.uuid4().hex[:8]}"
    finding_received = SpecialistFindingReceivedEvent(
        investigation_id=case_id,
        case_id=case_id,
        run_id=run_id,
        occurred_at=datetime.now(UTC),
        agent_id="transaction-agent",
        skill_id=SkillId.TRANSACTION_INVESTIGATION,
        finding_id=finding_id,
    )
    yield _ENCODER.encode(
        CustomEvent(
            type=EventType.CUSTOM,
            name=finding_received.event_name,
            value=finding_received.model_dump(mode="json"),
        )
    )

    dispute_summary = (
        f"Customer disputes a {transaction_data['currency']} {transaction_data['amount']} "
        f"transaction ({dispute_type.value}). Transaction description: "
        f"{transaction_data['description']}."
    )
    explanation = await explanation_client.generate_explanation(dispute_summary=dispute_summary)

    recommendation_event = RecommendationProducedEvent(
        investigation_id=case_id,
        case_id=case_id,
        run_id=run_id,
        occurred_at=datetime.now(UTC),
        recommendation=MOCK_RECOMMENDATION,
    )
    yield _ENCODER.encode(
        CustomEvent(
            type=EventType.CUSTOM,
            name=recommendation_event.event_name,
            value=recommendation_event.model_dump(mode="json"),
        )
    )

    completed = InvestigationCompletedEvent(
        investigation_id=case_id,
        case_id=case_id,
        run_id=run_id,
        occurred_at=datetime.now(UTC),
        final_status="completed",
    )
    yield _ENCODER.encode(
        CustomEvent(
            type=EventType.CUSTOM,
            name=completed.event_name,
            value=completed.model_dump(mode="json"),
        )
    )

    decision_card = DecisionCard(
        investigation_id=case_id,
        recommendation=MOCK_RECOMMENDATION,
        explanation=explanation,
    )
    envelope = A2uiEnvelope(
        version=A2UI_VERSION,
        surface_id=f"decision-{case_id}",
        investigation_id=case_id,
        components=(decision_card,),
        allowed_actions=(
            InvestigatorAction.APPROVE_RECOMMENDATION,
            InvestigatorAction.REJECT_RECOMMENDATION,
            InvestigatorAction.REQUEST_MORE_EVIDENCE,
        ),
        generated_at=datetime.now(UTC),
    )

    yield _ENCODER.encode(
        RunFinishedEvent(
            thread_id=thread_id,
            run_id=run_id,
            outcome=RunFinishedSuccessOutcome(type="success"),
            result=envelope.model_dump(mode="json"),
        )
    )
