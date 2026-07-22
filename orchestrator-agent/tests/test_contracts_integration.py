"""Proves orchestrator-agent can consume the shared contracts package."""

from datetime import UTC, datetime
from decimal import Decimal

from chargeback_contracts import DisputeType, InvestigationRequest, SourceChannel


def test_can_construct_and_round_trip_an_investigation_request() -> None:
    request = InvestigationRequest(
        investigation_id="INV-1",
        case_id="CASE-1",
        transaction_id="TXN-1",
        source_channel=SourceChannel.WEB_FORM,
        customer_narrative="Item never arrived.",
        dispute_type=DisputeType.GOODS_NOT_RECEIVED,
        amount=Decimal("25.00"),
        currency="USD",
        submitted_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    restored = InvestigationRequest.model_validate_json(request.model_dump_json())
    assert restored == request
