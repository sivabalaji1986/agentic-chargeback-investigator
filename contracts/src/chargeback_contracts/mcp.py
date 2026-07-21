"""MCP boundary contracts for the future mock MCP tool groups.

Application-owned request/response shapes only — this module does not
implement MCP tools or clients, and stays separate from the official MCP
protocol implementation.

`get_case` / `get_transaction` intentionally stay minimal: no case or
transaction business record schema exists anywhere in this contract layer
(inventing one would be a mock business service, out of scope for this
prompt) — the real shape is owned by the prompt that implements
dispute-mcp-server. `get_customer_history` and `get_merchant_evidence` /
`list_case_documents` reuse the already-defined
`CustomerHistoryFindingDetails` and `EvidenceRef` shapes, since a specialist
finding and an MCP read of the same domain data should look the same.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field, field_validator

from chargeback_contracts.common import ContractModel, require_non_blank
from chargeback_contracts.decisions import InvestigatorDecision
from chargeback_contracts.evidence import EvidenceRef, EvidenceType
from chargeback_contracts.findings import CustomerHistoryFindingDetails


class McpStatus(StrEnum):
    """Success/failure status for an MCP-facing operation."""

    SUCCESS = "success"
    FAILURE = "failure"


class McpErrorInfo(ContractModel):
    error_code: str = Field(min_length=1)
    safe_message: str = Field(min_length=1)


# --- Read-side ---


class GetCaseRequest(ContractModel):
    case_id: str = Field(min_length=1)


class GetCaseResponse(ContractModel):
    status: McpStatus
    case_id: str = Field(min_length=1)
    found: bool
    error: McpErrorInfo | None = None


class GetTransactionRequest(ContractModel):
    transaction_id: str = Field(min_length=1)


class GetTransactionResponse(ContractModel):
    status: McpStatus
    transaction_id: str = Field(min_length=1)
    found: bool
    error: McpErrorInfo | None = None


class GetCustomerHistoryRequest(ContractModel):
    case_id: str = Field(min_length=1)


class GetCustomerHistoryResponse(ContractModel):
    status: McpStatus
    case_id: str = Field(min_length=1)
    result: CustomerHistoryFindingDetails | None = None
    error: McpErrorInfo | None = None


class GetMerchantEvidenceRequest(ContractModel):
    case_id: str = Field(min_length=1)


class GetMerchantEvidenceResponse(ContractModel):
    status: McpStatus
    case_id: str = Field(min_length=1)
    evidence_refs: tuple[EvidenceRef, ...] = ()
    error: McpErrorInfo | None = None


class ListCaseDocumentsRequest(ContractModel):
    case_id: str = Field(min_length=1)


class ListCaseDocumentsResponse(ContractModel):
    status: McpStatus
    case_id: str = Field(min_length=1)
    documents: tuple[EvidenceRef, ...] = ()
    error: McpErrorInfo | None = None


# --- Write-side ---


class McpWriteRequestBase(ContractModel):
    """Every write-side MCP request must carry an idempotency key."""

    case_id: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=1)

    @field_validator("idempotency_key")
    @classmethod
    def _non_blank_idempotency_key(cls, value: str) -> str:
        return require_non_blank(value, field_name="idempotency_key")


class CreateEvidenceRequestTaskRequest(McpWriteRequestBase):
    requested_evidence_types: tuple[EvidenceType, ...] = ()
    message_to_customer: str = Field(min_length=1)


class UpdateCaseStatusRequest(McpWriteRequestBase):
    new_status: str = Field(min_length=1)


class CreateAuditEntryRequest(McpWriteRequestBase):
    investigator_decision: InvestigatorDecision | None = None
    event_description: str = Field(min_length=1)


class McpWriteResponse(ContractModel):
    status: McpStatus
    audit_correlation_id: str = Field(min_length=1)
    error: McpErrorInfo | None = None
