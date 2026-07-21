"""Tests for chargeback_contracts.common."""

from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from chargeback_contracts.common import (
    ContractModel,
    require_currency_code,
    require_non_blank,
    require_percentage,
    require_positive_amount,
    require_utc,
)
from pydantic import ValidationError


class _Example(ContractModel):
    name: str


def test_contract_model_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        _Example(name="ok", extra_field="not allowed")


def test_require_non_blank_rejects_blank() -> None:
    with pytest.raises(ValueError, match="must not be blank"):
        require_non_blank("   ", field_name="case_id")


def test_require_non_blank_accepts_value() -> None:
    assert require_non_blank("CASE-1", field_name="case_id") == "CASE-1"


def test_require_utc_rejects_naive_datetime() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        require_utc(datetime(2026, 1, 1), field_name="submitted_at")  # noqa: DTZ001


def test_require_utc_normalizes_to_utc() -> None:
    aware = datetime(2026, 1, 1, tzinfo=UTC)
    assert require_utc(aware, field_name="submitted_at") == aware


def test_require_utc_converts_non_utc_offset_to_utc() -> None:
    ist = timezone(timedelta(hours=5, minutes=30))
    non_utc = datetime(2026, 1, 1, tzinfo=ist)
    normalized = require_utc(non_utc, field_name="submitted_at")
    assert normalized.tzinfo == UTC
    assert normalized == datetime(2025, 12, 31, 18, 30, tzinfo=UTC)


def test_require_currency_code_rejects_lowercase() -> None:
    with pytest.raises(ValueError, match="ISO 4217"):
        require_currency_code("usd")


def test_require_currency_code_rejects_wrong_length() -> None:
    with pytest.raises(ValueError, match="ISO 4217"):
        require_currency_code("US")


def test_require_currency_code_accepts_valid() -> None:
    assert require_currency_code("USD") == "USD"


def test_require_positive_amount_rejects_zero_and_negative() -> None:
    with pytest.raises(ValueError, match="positive"):
        require_positive_amount(Decimal("0"))
    with pytest.raises(ValueError, match="positive"):
        require_positive_amount(Decimal("-1.00"))


def test_require_positive_amount_accepts_positive() -> None:
    assert require_positive_amount(Decimal("12.50")) == Decimal("12.50")


def test_require_percentage_rejects_out_of_bounds() -> None:
    with pytest.raises(ValueError, match="between 0 and 100"):
        require_percentage(Decimal("-1"))
    with pytest.raises(ValueError, match="between 0 and 100"):
        require_percentage(Decimal("101"))


def test_require_percentage_accepts_bounds() -> None:
    assert require_percentage(Decimal("0")) == Decimal("0")
    assert require_percentage(Decimal("100")) == Decimal("100")
