"""In-process client for the existing dispute-mcp-server.

Reuses the same server object dispute-mcp-server's own tests use
(fastmcp.Client(mcp_app)) rather than inventing a new transport or
duplicating lookup logic -- dispute-mcp-server remains stdio-only.
"""

from __future__ import annotations

from fastmcp import Client
from fastmcp.exceptions import ToolError

from dispute_mcp_server.main import mcp as dispute_mcp_app


class TransactionLookupError(Exception):
    """Raised when the case/transaction cannot be found via dispute-mcp-server."""


async def get_case_and_transaction(
    case_id: str,
) -> tuple[dict[str, object], dict[str, object]]:
    """Fetch a case and its transaction from dispute-mcp-server.

    Returns (case_data, transaction_data) as plain dicts (the MCP tool
    result's structured content), or raises TransactionLookupError.
    """
    async with Client(dispute_mcp_app) as client:
        try:
            case_result = await client.call_tool("get_case", {"case_id": case_id})
        except ToolError as exc:
            raise TransactionLookupError(f"case not found: {case_id}") from exc
        case_data = case_result.structured_content
        if case_data is None:
            raise TransactionLookupError(f"case not found: {case_id}")

        transaction_id = case_data["transaction_id"]
        transaction_result = await client.call_tool(
            "get_transaction", {"transaction_id": transaction_id}
        )
        transaction_data = transaction_result.structured_content
        if transaction_data is None:
            raise TransactionLookupError(f"transaction not found: {transaction_id}")

    return case_data, transaction_data
