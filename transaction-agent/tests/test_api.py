"""Tests for the FastAPI app's three endpoints."""

from __future__ import annotations

import json
import logging

import pytest
from fastapi.testclient import TestClient

from transaction_agent.api import create_app
from transaction_agent.llm_client import FakeExplanationClient


def _parse_sse(text: str) -> list[dict[str, object]]:
    events = []
    for raw_line in text.strip().split("\n\n"):
        if not raw_line.strip():
            continue
        assert raw_line.startswith("data: ")
        events.append(json.loads(raw_line[len("data: ") :]))
    return events


def test_agent_run_streams_five_milestones_for_seeded_case() -> None:
    app = create_app(explanation_client=FakeExplanationClient())
    client = TestClient(app)
    response = client.post(
        "/agent/run",
        json={
            "threadId": "thread-1",
            "runId": "run-1",
            "state": {},
            "messages": [],
            "tools": [],
            "context": [],
            "forwardedProps": {"case_id": "CASE-1001"},
        },
    )
    assert response.status_code == 200
    events = _parse_sse(response.text)
    custom_names = [e["name"] for e in events if e["type"] == "CUSTOM"]
    assert custom_names == [
        "investigation.accepted",
        "specialist.started",
        "specialist.finding_received",
        "recommendation.produced",
        "investigation.completed",
    ]


def test_agent_run_missing_case_id_returns_422() -> None:
    app = create_app(explanation_client=FakeExplanationClient())
    client = TestClient(app)
    response = client.post(
        "/agent/run",
        json={
            "threadId": "thread-1",
            "runId": "run-1",
            "state": {},
            "messages": [],
            "tools": [],
            "context": [],
            "forwardedProps": {},
        },
    )
    assert response.status_code == 422


def test_agent_run_unknown_case_returns_404() -> None:
    app = create_app(explanation_client=FakeExplanationClient())
    client = TestClient(app)
    response = client.post(
        "/agent/run",
        json={
            "threadId": "thread-1",
            "runId": "run-1",
            "state": {},
            "messages": [],
            "tools": [],
            "context": [],
            "forwardedProps": {"case_id": "CASE-NOPE"},
        },
    )
    assert response.status_code == 404


def test_intake_defaults_to_seeded_case_1001() -> None:
    app = create_app(explanation_client=FakeExplanationClient())
    client = TestClient(app)
    response = client.post("/intake", json={})
    assert response.status_code == 200
    events = _parse_sse(response.text)
    assert events[0]["type"] == "RUN_STARTED"


def test_actions_decision_returns_204_and_logs(caplog: pytest.LogCaptureFixture) -> None:
    app = create_app(explanation_client=FakeExplanationClient())
    client = TestClient(app)
    with caplog.at_level(logging.INFO, logger="transaction_agent"):
        response = client.post(
            "/actions/decision",
            json={
                "decision_id": "DEC-1",
                "investigation_id": "CASE-1001",
                "case_id": "CASE-1001",
                "investigator_id": "inv-jane",
                "selected_action": "approve_recommendation",
                "recommendation_shown": "request_more_evidence",
                "decided_at": "2026-01-01T00:00:00Z",
            },
        )
    assert response.status_code == 204
    assert any("investigator_decision" in r.message for r in caplog.records)


def test_actions_decision_rejects_unknown_field() -> None:
    app = create_app(explanation_client=FakeExplanationClient())
    client = TestClient(app)
    response = client.post(
        "/actions/decision",
        json={
            "decision_id": "DEC-1",
            "investigation_id": "CASE-1001",
            "case_id": "CASE-1001",
            "investigator_id": "inv-jane",
            "selected_action": "approve_recommendation",
            "recommendation_shown": "request_more_evidence",
            "decided_at": "2026-01-01T00:00:00Z",
            "unexpected_field": "nope",
        },
    )
    assert response.status_code == 422
