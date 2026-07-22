"""Environment-backed settings for transaction-agent."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    service_name: str
    ollama_base_url: str
    ollama_text_model: str
    log_level: str


def load_settings() -> Settings:
    return Settings(
        service_name=os.environ.get("SERVICE_NAME", "transaction-agent"),
        ollama_base_url=os.environ.get("OLLAMA_BASE_URL", "http://host.docker.internal:11434"),
        ollama_text_model=os.environ.get("OLLAMA_TEXT_MODEL", "qwen3.5:latest"),
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
    )
