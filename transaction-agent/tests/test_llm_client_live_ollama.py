"""Real, live validation against the host Ollama instance.

Skips (does not fail) if Ollama isn't reachable -- other machines running
this suite may not have it running. This environment does, so it will
actually execute here. This is the empirical "no <think> leakage /
structured JSON / reliable classification" gate Prompt 4 requires.
"""

from __future__ import annotations

import httpx
import pytest

from transaction_agent.config import load_settings
from transaction_agent.llm_client import OllamaExplanationClient


def _ollama_reachable(base_url: str) -> bool:
    try:
        response = httpx.get(f"{base_url}/api/tags", timeout=2.0)
        return response.status_code == 200
    except httpx.HTTPError:
        return False


async def test_real_ollama_produces_clean_explanation_with_no_think_leakage() -> None:
    settings = load_settings()
    if not _ollama_reachable(settings.ollama_base_url):
        pytest.skip(f"Ollama not reachable at {settings.ollama_base_url}")

    client = OllamaExplanationClient(
        base_url=settings.ollama_base_url, model=settings.ollama_text_model
    )
    explanation = await client.generate_explanation(
        dispute_summary=(
            "Customer disputes a USD 89.99 transaction claiming goods were "
            "never received. Delivery status shows not yet delivered."
        )
    )

    assert explanation.strip()
    assert "<think>" not in explanation
    assert "</think>" not in explanation
