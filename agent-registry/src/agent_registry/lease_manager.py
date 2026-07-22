"""Background lease-sweep task lifecycle, used by api.py's FastAPI lifespan.

The sweep *logic* lives in RegistryService.sweep_expired(), independently
and deterministically tested with a FakeClock; this module only owns
starting/stopping the periodic background asyncio task around it.
"""

from __future__ import annotations

import asyncio
import logging

from agent_registry.service import RegistryService

logger = logging.getLogger("agent_registry")


class LeaseManager:
    def __init__(self, *, service: RegistryService, sweep_interval_seconds: float) -> None:
        self._service = service
        self._sweep_interval_seconds = sweep_interval_seconds
        self._task: asyncio.Task[None] | None = None

    async def _run(self) -> None:
        while True:
            await asyncio.sleep(self._sweep_interval_seconds)
            try:
                await self._service.sweep_expired()
            except Exception:
                logger.exception("lease sweep failed")

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
