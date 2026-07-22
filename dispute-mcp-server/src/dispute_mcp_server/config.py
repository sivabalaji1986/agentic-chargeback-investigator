"""Environment-backed settings for dispute-mcp-server."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    service_name: str
    log_level: str


def load_settings() -> Settings:
    return Settings(
        service_name=os.environ.get("MCP_SERVICE_NAME", "dispute-mcp-server"),
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
    )
