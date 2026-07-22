"""Tests for agent_registry.config."""

from __future__ import annotations

from pytest import MonkeyPatch

from agent_registry.config import load_settings


def test_load_settings_uses_documented_defaults(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.delenv("REGISTRY_SERVICE_NAME", raising=False)
    monkeypatch.delenv("LEASE_DURATION_SECONDS", raising=False)
    monkeypatch.delenv("LEASE_SWEEP_INTERVAL_SECONDS", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)

    settings = load_settings()

    assert settings.service_name == "agent-registry"
    assert settings.lease_duration_seconds == 30.0
    assert settings.lease_sweep_interval_seconds == 10.0
    assert settings.log_level == "INFO"


def test_load_settings_reads_environment_overrides(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("REGISTRY_SERVICE_NAME", "registry-test")
    monkeypatch.setenv("LEASE_DURATION_SECONDS", "5")
    monkeypatch.setenv("LEASE_SWEEP_INTERVAL_SECONDS", "1")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    settings = load_settings()

    assert settings.service_name == "registry-test"
    assert settings.lease_duration_seconds == 5.0
    assert settings.lease_sweep_interval_seconds == 1.0
    assert settings.log_level == "DEBUG"
