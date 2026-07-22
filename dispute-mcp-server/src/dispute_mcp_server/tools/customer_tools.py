"""Customer tool group: get_customer_profile, get_prior_disputes,
get_refund_history."""

from __future__ import annotations

import logging

from fastmcp import FastMCP

from dispute_mcp_server.logging import log_tool_call
from dispute_mcp_server.models import (
    CustomerProfileRecord,
    PriorDisputeRecord,
    RefundHistoryEntry,
)
from dispute_mcp_server.repository import DisputeRepository


def register_customer_tools(
    mcp: FastMCP, repository: DisputeRepository, logger: logging.Logger
) -> None:
    @mcp.tool
    @log_tool_call(logger, "get_customer_profile", id_from=lambda customer_id: customer_id)
    def get_customer_profile(customer_id: str) -> CustomerProfileRecord:
        """Get a customer profile by ID."""
        return repository.get_customer_profile(customer_id)

    @mcp.tool
    @log_tool_call(logger, "get_prior_disputes", id_from=lambda customer_id: customer_id)
    def get_prior_disputes(customer_id: str) -> tuple[PriorDisputeRecord, ...]:
        """Get a customer's prior dispute history (may be empty)."""
        return repository.get_prior_disputes(customer_id)

    @mcp.tool
    @log_tool_call(logger, "get_refund_history", id_from=lambda customer_id: customer_id)
    def get_refund_history(customer_id: str) -> tuple[RefundHistoryEntry, ...]:
        """Get a customer's refund history (may be empty)."""
        return repository.get_refund_history(customer_id)
