"""Merchant tool group: get_merchant_evidence, get_delivery_details,
get_cancellation_details."""

from __future__ import annotations

import logging

from fastmcp import FastMCP

from dispute_mcp_server.logging import log_tool_call
from dispute_mcp_server.models import (
    CancellationDetailsRecord,
    DeliveryDetailsRecord,
    MerchantEvidenceRecord,
)
from dispute_mcp_server.repository import DisputeRepository


def register_merchant_tools(
    mcp: FastMCP, repository: DisputeRepository, logger: logging.Logger
) -> None:
    @mcp.tool
    @log_tool_call(logger, "get_merchant_evidence", id_from=lambda case_id: case_id)
    def get_merchant_evidence(case_id: str) -> MerchantEvidenceRecord:
        """Get the merchant's submitted evidence for a case."""
        return repository.get_merchant_evidence(case_id)

    @mcp.tool
    @log_tool_call(logger, "get_delivery_details", id_from=lambda case_id: case_id)
    def get_delivery_details(case_id: str) -> DeliveryDetailsRecord:
        """Get delivery details for a case."""
        return repository.get_delivery_details(case_id)

    @mcp.tool
    @log_tool_call(logger, "get_cancellation_details", id_from=lambda case_id: case_id)
    def get_cancellation_details(case_id: str) -> CancellationDetailsRecord:
        """Get cancellation details for a case."""
        return repository.get_cancellation_details(case_id)
