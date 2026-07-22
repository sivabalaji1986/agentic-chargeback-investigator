"""Integration tests for service.py's run_investigation.

Uses real seeded CASE-1001/TXN-2001 data (fetched via mcp_client, itself
tested in Task 3) and FakeExplanationClient (no live LLM needed here --
the live LLM path is validated separately in test_llm_client_live_ollama.py).
"""

from __future__ import annotations

import json

from ag_ui.core import EventType

from transaction_agent.llm_client import FakeExplanationClient
from transaction_agent.mcp_client import get_case_and_transaction
from transaction_agent.service import run_investigation


def _parse_sse_events(lines: list[str]) -> list[dict[str, object]]:
    events = []
    for line in lines:
        assert line.startswith("data: ")
        events.append(json.loads(line[len("data: ") :].strip()))
    return events


async def _run_for_case_1001(explanation_client: FakeExplanationClient) -> list[dict[str, object]]:
    case_data, transaction_data = await get_case_and_transaction("CASE-1001")
    lines = [
        line
        async for line in run_investigation(
            case_data=case_data,
            transaction_data=transaction_data,
            thread_id="thread-1",
            run_id="run-1",
            explanation_client=explanation_client,
        )
    ]
    return _parse_sse_events(lines)


async def test_run_investigation_yields_five_milestones_plus_run_bookends() -> None:
    events = await _run_for_case_1001(FakeExplanationClient())
    types = [e["type"] for e in events]
    assert types[0] == EventType.RUN_STARTED.value
    assert types[-1] == EventType.RUN_FINISHED.value

    custom_names = [e["name"] for e in events if e["type"] == EventType.CUSTOM.value]
    assert custom_names == [
        "investigation.accepted",
        "specialist.started",
        "specialist.finding_received",
        "recommendation.produced",
        "investigation.completed",
    ]


async def test_run_investigation_final_result_is_a_valid_decision_card_envelope() -> None:
    events = await _run_for_case_1001(
        FakeExplanationClient(fixed_explanation="Fixed test explanation.")
    )
    run_finished = events[-1]
    envelope = run_finished["result"]
    assert isinstance(envelope, dict)
    assert envelope["version"] == "0.9"
    assert envelope["investigation_id"] == "CASE-1001"
    card = envelope["components"][0]
    assert card["component_type"] == "decision_card"
    assert card["explanation"] == "Fixed test explanation."
    assert card["recommendation"] == "request_more_evidence"
    assert set(envelope["allowed_actions"]) == {
        "approve_recommendation",
        "reject_recommendation",
        "request_more_evidence",
    }


async def test_run_investigation_dispute_type_matches_seeded_case() -> None:
    events = await _run_for_case_1001(FakeExplanationClient())
    accepted = next(e for e in events if e.get("name") == "investigation.accepted")
    value = accepted["value"]
    assert isinstance(value, dict)
    assert value["dispute_type"] == "goods_not_received"
