"""Structured logging for agent-registry.

Mirrors dispute-mcp-server's logging.py deliberately: an explicit
logger.setLevel(...) plus a manually-attached StreamHandler, never
logging.basicConfig. Prompt 4 found that relying on something else to
call logging.basicConfig is easy to silently omit entirely (transaction-
agent's INFO logs were dropped in the real running process until that gap
was found via live browser verification and fixed) -- this explicit
pattern has no such gap.
"""

from __future__ import annotations

import logging

_LOGGER_NAME = "agent_registry"


def configure_logging(level: str) -> logging.Logger:
    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(level)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
    return logger
