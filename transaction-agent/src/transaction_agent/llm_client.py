"""LLM client for generating investigation explanations.

The recommendation itself is never LLM-generated in this prompt -- only
the explanation text. See
docs/superpowers/specs/2026-07-22-vertical-slice-design.md.
"""

from __future__ import annotations

import json
from typing import Protocol

import httpx


class ExplanationClient(Protocol):
    async def generate_explanation(self, *, dispute_summary: str) -> str: ...


class OllamaExplanationClient:
    """Real client: calls the host Ollama /api/chat endpoint.

    Uses think=false (validated during design research to produce no
    <think> leakage) and format=json (validated to produce reliably
    parseable structured output for a well-scoped prompt).
    """

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        timeout_seconds: float = 30.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = base_url
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    async def generate_explanation(self, *, dispute_summary: str) -> str:
        async with httpx.AsyncClient(
            timeout=self._timeout_seconds, transport=self._transport
        ) as client:
            response = await client.post(
                f"{self._base_url}/api/chat",
                json={
                    "model": self._model,
                    "think": False,
                    "stream": False,
                    "format": "json",
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are a chargeback investigation assistant. "
                                'Respond only with JSON matching: {"explanation": string}. '
                                "The explanation must be 1-2 sentences, factual, and reference "
                                "only the details given. Do not include any other text."
                            ),
                        },
                        {"role": "user", "content": dispute_summary},
                    ],
                },
            )
            response.raise_for_status()
            payload = response.json()
        content = payload["message"]["content"]
        parsed = json.loads(content)
        explanation = parsed["explanation"]
        if not isinstance(explanation, str) or not explanation.strip():
            raise ValueError("Ollama returned an empty or non-string explanation")
        return explanation


class FakeExplanationClient:
    """Deterministic stand-in for tests that don't need a live LLM."""

    def __init__(
        self, *, fixed_explanation: str = "Delivery proof has not yet been provided."
    ) -> None:
        self._fixed_explanation = fixed_explanation

    async def generate_explanation(self, *, dispute_summary: str) -> str:
        return self._fixed_explanation
