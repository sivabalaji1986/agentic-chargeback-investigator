"""Tests for agent_registry.logging."""

from __future__ import annotations

import logging

from agent_registry.logging import configure_logging


def test_configure_logging_sets_the_requested_level() -> None:
    logger = configure_logging("DEBUG")
    assert logger.level == logging.DEBUG
    assert logger.name == "agent_registry"


def test_configure_logging_attaches_exactly_one_handler_even_if_called_twice() -> None:
    first = configure_logging("INFO")
    second = configure_logging("WARNING")
    assert first is second
    assert len(second.handlers) == 1
    assert second.level == logging.WARNING
