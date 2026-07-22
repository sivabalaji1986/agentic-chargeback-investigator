"""Tests for chargeback_contracts.dispute."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from chargeback_contracts.dispute import InvestigationRequest, SourceChannel
from chargeback_contracts.skills import DisputeType, SkillId


def _valid_request(**overrides: object) -> InvestigationRequest:
    defaults: dict[str, object] = {
        "investigation_id": "INV-1",
        "case_id": "CASE-1",
        "transaction_id": "TXN-1",
        "source_channel": SourceChannel.WEB_FORM,
        "customer_narrative": "Item never arrived.",
        "dispute_type": DisputeType.GOODS_NOT_RECEIVED,
        "amount": Decimal("99.99"),
        "currency": "USD",
        "submitted_at": datetime(2026, 1, 1, tzinfo=UTC),
        "requested_skill_ids": (SkillId.TRANSACTION_INVESTIGATION,),
    }
    defaults.update(overrides)
    return InvestigationRequest(**defaults)  # type: ignore[arg-type]


def test_valid_request_round_trips_through_json() -> None:
    request = _valid_request()
    restored = InvestigationRequest.model_validate_json(request.model_dump_json())
    assert restored == request


def test_source_channel_stable_values() -> None:
    assert SourceChannel.EMAIL.value == "email"
    assert SourceChannel.CONTACT_CENTRE.value == "contact_centre"
    assert SourceChannel.WEB_FORM.value == "web_form"
    assert SourceChannel.CHATBOT.value == "chatbot"


def test_rejects_non_positive_amount() -> None:
    with pytest.raises(ValidationError, match="positive"):
        _valid_request(amount=Decimal("0"))


def test_rejects_lowercase_currency() -> None:
    with pytest.raises(ValidationError, match="ISO 4217"):
        _valid_request(currency="usd")


def test_rejects_naive_submitted_at() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        _valid_request(submitted_at=datetime(2026, 1, 1))  # noqa: DTZ001


def test_rejects_blank_context_id_when_supplied() -> None:
    with pytest.raises(ValidationError, match="must not be blank"):
        _valid_request(a2a_context_id="   ")


def test_allows_omitted_context_id() -> None:
    request = _valid_request()
    assert request.a2a_context_id is None


def test_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError):
        _valid_request(unexpected_field="nope")
