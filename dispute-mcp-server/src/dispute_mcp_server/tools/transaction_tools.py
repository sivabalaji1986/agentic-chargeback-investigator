"""Transaction tool group: get_transaction, get_authorization, get_settlement,
get_refund_or_reversal."""

from __future__ import annotations

import logging

from fastmcp import FastMCP

from dispute_mcp_server.logging import log_tool_call
from dispute_mcp_server.models import (
    AuthorizationRecord,
    RefundOrReversalRecord,
    SettlementRecord,
    TransactionRecord,
)
from dispute_mcp_server.repository import DisputeRepository


def register_transaction_tools(
    mcp: FastMCP, repository: DisputeRepository, logger: logging.Logger
) -> None:
    @mcp.tool
    @log_tool_call(logger, "get_transaction", id_from=lambda transaction_id: transaction_id)
    def get_transaction(transaction_id: str) -> TransactionRecord:
        """Get a transaction by ID."""
        return repository.get_transaction(transaction_id)

    @mcp.tool
    @log_tool_call(logger, "get_authorization", id_from=lambda transaction_id: transaction_id)
    def get_authorization(transaction_id: str) -> AuthorizationRecord:
        """Get the authorization for a transaction."""
        return repository.get_authorization(transaction_id)

    @mcp.tool
    @log_tool_call(logger, "get_settlement", id_from=lambda transaction_id: transaction_id)
    def get_settlement(transaction_id: str) -> SettlementRecord:
        """Get the settlement for a transaction."""
        return repository.get_settlement(transaction_id)

    @mcp.tool
    @log_tool_call(logger, "get_refund_or_reversal", id_from=lambda transaction_id: transaction_id)
    def get_refund_or_reversal(transaction_id: str) -> tuple[RefundOrReversalRecord, ...]:
        """Get any refunds or reversals for a transaction (may be empty)."""
        return repository.get_refunds_or_reversals(transaction_id)
