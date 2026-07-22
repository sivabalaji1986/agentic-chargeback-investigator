"""Unit tests for llm_client.py using httpx.MockTransport (no real network)."""

from __future__ import annotations

import json

import httpx
import pytest

from transaction_agent.llm_client import FakeExplanationClient, OllamaExplanationClient


async def test_fake_client_returns_fixed_explanation() -> None:
    client = FakeExplanationClient(fixed_explanation="Example explanation.")
    result = await client.generate_explanation(dispute_summary="x")
    assert result == "Example explanation."


async def test_ollama_client_sends_think_false_and_json_format() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={"message": {"content": '{"explanation": "Real explanation text."}'}},
        )

    client = OllamaExplanationClient(
        base_url="http://fake-ollama:11434",
        model="qwen3.5:latest",
        transport=httpx.MockTransport(handler),
    )
    result = await client.generate_explanation(dispute_summary="Customer disputes a charge.")

    assert result == "Real explanation text."
    body = captured["body"]
    assert isinstance(body, dict)
    assert body["model"] == "qwen3.5:latest"
    assert body["think"] is False
    assert body["format"] == "json"


async def test_ollama_client_rejects_malformed_json_content() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"message": {"content": "not json"}})

    client = OllamaExplanationClient(
        base_url="http://fake-ollama:11434",
        model="qwen3.5:latest",
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(json.JSONDecodeError):
        await client.generate_explanation(dispute_summary="x")


async def test_ollama_client_rejects_empty_explanation() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"message": {"content": '{"explanation": "   "}'}})

    client = OllamaExplanationClient(
        base_url="http://fake-ollama:11434",
        model="qwen3.5:latest",
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(ValueError, match="empty or non-string"):
        await client.generate_explanation(dispute_summary="x")
