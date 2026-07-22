"""Environment-backed settings for agent-registry."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    service_name: str
    lease_duration_seconds: float
    lease_sweep_interval_seconds: float
    log_level: str


def load_settings() -> Settings:
    return Settings(
        service_name=os.environ.get("REGISTRY_SERVICE_NAME", "agent-registry"),
        lease_duration_seconds=float(os.environ.get("LEASE_DURATION_SECONDS", "30")),
        lease_sweep_interval_seconds=float(
            os.environ.get("LEASE_SWEEP_INTERVAL_SECONDS", "10")
        ),
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
    )
