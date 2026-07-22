"""Tests for chargeback_contracts.mcp."""

from datetime import UTC, datetime

import pytest
from chargeback_contracts.a2ui import InvestigatorAction
from chargeback_contracts.decisions import InvestigatorDecision
from chargeback_contracts.findings import CustomerHistoryFindingDetails
from chargeback_contracts.mcp import (
    CreateAuditEntryRequest,
    CreateEvidenceRequestTaskRequest,
    GetCaseResponse,
    GetCustomerHistoryResponse,
    McpStatus,
    McpWriteResponse,
    UpdateCaseStatusRequest,
)
from chargeback_contracts.recommendation import RecommendationType
from pydantic import ValidationError


def test_get_case_response_round_trips_through_json() -> None:
    response = GetCaseResponse(status=McpStatus.SUCCESS, case_id="CASE-1", found=True)
    restored = GetCaseResponse.model_validate_json(response.model_dump_json())
    assert restored == response


def test_get_customer_history_response_reuses_finding_details_shape() -> None:
    response = GetCustomerHistoryResponse(
        status=McpStatus.SUCCESS,
        case_id="CASE-1",
        result=CustomerHistoryFindingDetails(previous_dispute_count=1, previous_refund_count=0),
    )
    restored = GetCustomerHistoryResponse.model_validate_json(response.model_dump_json())
    assert restored == response


def test_write_request_requires_idempotency_key() -> None:
    with pytest.raises(ValidationError):
        UpdateCaseStatusRequest(case_id="CASE-1", idempotency_key="", new_status="closed")


def test_write_request_rejects_blank_idempotency_key() -> None:
    with pytest.raises(ValidationError, match="must not be blank"):
        UpdateCaseStatusRequest(case_id="CASE-1", idempotency_key="   ", new_status="closed")


def test_create_audit_entry_can_carry_investigator_decision() -> None:
    decision = InvestigatorDecision(
        decision_id="DEC-1",
        investigation_id="INV-1",
        case_id="CASE-1",
        investigator_id="inv-jane",
        selected_action=InvestigatorAction.APPROVE_RECOMMENDATION,
        recommendation_shown=RecommendationType.ACCEPT_CHARGEBACK,
        decided_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    request = CreateAuditEntryRequest(
        case_id="CASE-1",
        idempotency_key="idem-1",
        investigator_decision=decision,
        event_description="Investigator approved the recommendation.",
    )
    restored = CreateAuditEntryRequest.model_validate_json(request.model_dump_json())
    assert restored == request


def test_write_response_round_trips_through_json() -> None:
    response = McpWriteResponse(status=McpStatus.SUCCESS, audit_correlation_id="AUD-1")
    restored = McpWriteResponse.model_validate_json(response.model_dump_json())
    assert restored == response


def test_evidence_request_task_rejects_unknown_field() -> None:
    with pytest.raises(ValidationError):
        CreateEvidenceRequestTaskRequest(  # type: ignore[call-arg]
            case_id="CASE-1",
            idempotency_key="idem-1",
            message_to_customer="Please provide delivery proof.",
            unexpected_field="nope",
        )
