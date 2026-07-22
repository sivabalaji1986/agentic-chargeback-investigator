"""Tests for agent_registry.clock."""

from __future__ import annotations

from datetime import UTC, datetime

from agent_registry.clock import FakeClock, SystemClock


def test_system_clock_returns_timezone_aware_utc_now() -> None:
    clock = SystemClock()
    result = clock.now()
    assert result.tzinfo is not None
    offset = result.utcoffset()
    assert offset is not None
    assert offset.total_seconds() == 0


def test_fake_clock_starts_at_a_fixed_point_by_default() -> None:
    clock = FakeClock()
    assert clock.now() == datetime(2026, 1, 1, tzinfo=UTC)


def test_fake_clock_can_start_at_an_explicit_point() -> None:
    start = datetime(2020, 6, 15, 12, 0, 0, tzinfo=UTC)
    clock = FakeClock(start=start)
    assert clock.now() == start


def test_fake_clock_advance_moves_time_forward_by_exact_seconds() -> None:
    clock = FakeClock(start=datetime(2026, 1, 1, tzinfo=UTC))
    clock.advance(90)
    assert clock.now() == datetime(2026, 1, 1, 0, 1, 30, tzinfo=UTC)
