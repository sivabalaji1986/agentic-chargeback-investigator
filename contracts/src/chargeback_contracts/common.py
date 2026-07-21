"""Shared primitives used across the contract layer.

Leaf module: common.py must never import from any sibling contract module.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

_CURRENCY_CODE_RE = re.compile(r"^[A-Z]{3}$")


class ContractModel(BaseModel):
    """Base class for every application-owned contract model.

    Rejects unknown fields so producers and consumers stay in lockstep
    across service boundaries.
    """

    model_config = ConfigDict(extra="forbid")


def require_non_blank(value: str, *, field_name: str) -> str:
    """Reject empty or whitespace-only identifiers."""
    if not value or not value.strip():
        raise ValueError(f"{field_name} must not be blank")
    return value


def require_utc(value: datetime, *, field_name: str) -> datetime:
    """Require a timezone-aware datetime, normalized to UTC."""
    if value.tzinfo is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value.astimezone(timezone.utc)


def require_currency_code(value: str) -> str:
    """Validate an ISO 4217 three-letter uppercase currency code."""
    if not _CURRENCY_CODE_RE.match(value):
        raise ValueError("currency must be a three-letter uppercase ISO 4217 code")
    return value


def require_positive_amount(value: Decimal) -> Decimal:
    """Require a strictly positive monetary amount."""
    if value <= 0:
        raise ValueError("amount must be positive")
    return value


def require_percentage(value: Decimal) -> Decimal:
    """Require a percentage value within the inclusive bounds [0, 100]."""
    if value < 0 or value > 100:
        raise ValueError("percentage must be between 0 and 100")
    return value
