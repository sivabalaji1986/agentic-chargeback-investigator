"""Case tool group: get_case, update_case, write_audit."""

from __future__ import annotations

import logging

from fastmcp import FastMCP

from chargeback_contracts.mcp import (
    CreateAuditEntryRequest,
    McpErrorInfo,
    McpStatus,
    McpWriteResponse,
    UpdateCaseStatusRequest,
)
from dispute_mcp_server.logging import log_tool_call
from dispute_mcp_server.models import CaseRecord
from dispute_mcp_server.repository import DisputeRepository, NotFoundError


def register_case_tools(
    mcp: FastMCP, repository: DisputeRepository, logger: logging.Logger
) -> None:
    @mcp.tool
    @log_tool_call(logger, "get_case", id_from=lambda case_id: case_id)
    def get_case(case_id: str) -> CaseRecord:
        """Get a chargeback case by ID."""
        return repository.get_case(case_id)

    @mcp.tool
    @log_tool_call(logger, "update_case", id_from=lambda request: request.case_id)
    def update_case(request: UpdateCaseStatusRequest) -> McpWriteResponse:
        """Update a case's status. Requires a non-blank idempotency key."""
        try:
            repository.update_case_status(request.case_id, request.new_status)
        except NotFoundError:
            return McpWriteResponse(
                status=McpStatus.FAILURE,
                audit_correlation_id=request.idempotency_key,
                error=McpErrorInfo(
                    error_code="case_not_found",
                    safe_message="No case exists with the given case_id.",
                ),
            )
        return McpWriteResponse(
            status=McpStatus.SUCCESS,
            audit_correlation_id=request.idempotency_key,
        )

    @mcp.tool
    @log_tool_call(logger, "write_audit", id_from=lambda request: request.case_id)
    def write_audit(request: CreateAuditEntryRequest) -> McpWriteResponse:
        """Append an audit log entry for a case. Requires a non-blank idempotency key."""
        try:
            audit_record = repository.append_audit_record(
                request.case_id, request.event_description, request.idempotency_key
            )
        except NotFoundError:
            return McpWriteResponse(
                status=McpStatus.FAILURE,
                audit_correlation_id=request.idempotency_key,
                error=McpErrorInfo(
                    error_code="case_not_found",
                    safe_message="No case exists with the given case_id.",
                ),
            )
        return McpWriteResponse(
            status=McpStatus.SUCCESS,
            audit_correlation_id=audit_record.audit_id,
        )
