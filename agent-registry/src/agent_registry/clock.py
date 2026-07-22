"""Injectable clock so lease-expiry logic is deterministically testable.

Real lease expiry would otherwise require tests to sleep for as long as
the lease duration. `FakeClock` lets tests advance time instantly instead.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime: ...


class SystemClock:
    """Real wall-clock time, used by the running service."""

    def now(self) -> datetime:
        return datetime.now(UTC)


class FakeClock:
    """Test-controlled clock that only moves when explicitly advanced."""

    def __init__(self, *, start: datetime | None = None) -> None:
        self._current = start if start is not None else datetime(2026, 1, 1, tzinfo=UTC)

    def now(self) -> datetime:
        return self._current

    def advance(self, seconds: float) -> None:
        self._current = self._current + timedelta(seconds=seconds)
