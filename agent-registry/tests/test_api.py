"""Tests for the FastAPI app's registration/renewal/deregistration/discovery/health endpoints."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from agent_registry.api import create_app
from agent_registry.clock import FakeClock


def _registration_payload(agent_id: str = "agent-1") -> dict[str, object]:
    return {
        "agent_id": agent_id,
        "agent_name": f"Agent {agent_id}",
        "endpoint": f"http://localhost:9000/{agent_id}",
        "version": "0.1.0",
        "capabilities": ["transaction-investigation"],
    }


def test_register_new_agent_returns_201() -> None:
    with TestClient(create_app(clock=FakeClock())) as client:
        response = client.post("/agents", json=_registration_payload())
    assert response.status_code == 201
    assert response.json()["agent_id"] == "agent-1"


def test_register_existing_agent_id_returns_200_and_refreshes() -> None:
    with TestClient(create_app(clock=FakeClock())) as client:
        client.post("/agents", json=_registration_payload())
        response = client.post("/agents", json=_registration_payload())
    assert response.status_code == 200


def test_register_rejects_unknown_field() -> None:
    with TestClient(create_app(clock=FakeClock())) as client:
        payload = _registration_payload()
        payload["unexpected"] = "nope"
        response = client.post("/agents", json=payload)
    assert response.status_code == 422


def test_renew_returns_200_with_a_later_lease_expiry() -> None:
    clock = FakeClock(start=datetime(2026, 1, 1, tzinfo=UTC))
    with TestClient(create_app(clock=clock)) as client:
        initial = client.post("/agents", json=_registration_payload()).json()
        clock.advance(5)
        response = client.post("/agents/agent-1/renew")
        renewed = response.json()
    assert response.status_code == 200
    assert renewed["lease_expires_at"] > initial["lease_expires_at"]


def test_renew_unknown_agent_returns_404() -> None:
    with TestClient(create_app(clock=FakeClock())) as client:
        response = client.post("/agents/nope/renew")
    assert response.status_code == 404


def test_deregister_returns_204() -> None:
    with TestClient(create_app(clock=FakeClock())) as client:
        client.post("/agents", json=_registration_payload())
        response = client.delete("/agents/agent-1")
    assert response.status_code == 204


def test_deregister_unknown_agent_returns_404() -> None:
    with TestClient(create_app(clock=FakeClock())) as client:
        response = client.delete("/agents/nope")
    assert response.status_code == 404


def test_list_agents_on_empty_registry_returns_empty_list() -> None:
    with TestClient(create_app(clock=FakeClock())) as client:
        response = client.get("/agents")
    assert response.status_code == 200
    assert response.json() == []


def test_list_agents_returns_registered_agents() -> None:
    with TestClient(create_app(clock=FakeClock())) as client:
        client.post("/agents", json=_registration_payload())
        response = client.get("/agents")
    assert [agent["agent_id"] for agent in response.json()] == ["agent-1"]


def test_list_capabilities_returns_distinct_capabilities() -> None:
    with TestClient(create_app(clock=FakeClock())) as client:
        client.post("/agents", json=_registration_payload())
        response = client.get("/agents/capabilities")
    assert response.json() == ["transaction-investigation"]


def test_discover_returns_matching_agents() -> None:
    with TestClient(create_app(clock=FakeClock())) as client:
        client.post("/agents", json=_registration_payload())
        response = client.get(
            "/agents/discover", params={"capability": "transaction-investigation"}
        )
    assert [agent["agent_id"] for agent in response.json()] == ["agent-1"]


def test_discover_unknown_capability_returns_empty_list() -> None:
    with TestClient(create_app(clock=FakeClock())) as client:
        client.post("/agents", json=_registration_payload())
        response = client.get(
            "/agents/discover", params={"capability": "chargeback-policy-interpretation"}
        )
    assert response.status_code == 200
    assert response.json() == []


def test_discover_rejects_an_invalid_capability_value() -> None:
    with TestClient(create_app(clock=FakeClock())) as client:
        response = client.get("/agents/discover", params={"capability": "not-a-real-capability"})
    assert response.status_code == 422


def test_health_returns_status_ok_and_agent_count() -> None:
    with TestClient(create_app(clock=FakeClock())) as client:
        client.post("/agents", json=_registration_payload())
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "agent_count": 1}
