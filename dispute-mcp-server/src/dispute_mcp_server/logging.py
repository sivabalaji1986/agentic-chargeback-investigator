"""Structured logging for MCP tool calls.

Logs only the tool name, one relevant identifier, success/failure, and
duration — never full record contents, free-text comments, or raw
exception bodies.
"""

from __future__ import annotations

import functools
import logging
import time
from collections.abc import Callable
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
T = TypeVar("T")

_LOGGER_NAME = "dispute_mcp_server"


def configure_logging(level: str) -> logging.Logger:
    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(level)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
    return logger


def log_tool_call(
    logger: logging.Logger, tool_name: str, id_from: Callable[..., str | None]
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Wrap a tool function, logging its outcome without its full payload."""

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            record_id = id_from(*args, **kwargs)
            started = time.monotonic()
            try:
                result = func(*args, **kwargs)
            except Exception as exc:
                duration_ms = (time.monotonic() - started) * 1000
                logger.warning(
                    "tool=%s id=%s outcome=failure duration_ms=%.2f error=%s",
                    tool_name,
                    record_id,
                    duration_ms,
                    type(exc).__name__,
                )
                raise
            duration_ms = (time.monotonic() - started) * 1000
            logger.info(
                "tool=%s id=%s outcome=success duration_ms=%.2f",
                tool_name,
                record_id,
                duration_ms,
            )
            return result

        return wrapper

    return decorator
