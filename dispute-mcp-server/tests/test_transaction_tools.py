"""Tests for the transaction tool group, via an in-memory fastmcp.Client."""

import pytest
from fastmcp import Client, FastMCP
from fastmcp.exceptions import ToolError

from dispute_mcp_server.logging import configure_logging
from dispute_mcp_server.repository import DisputeRepository
from dispute_mcp_server.tools.transaction_tools import register_transaction_tools


@pytest.fixture
def mcp() -> FastMCP:
    app = FastMCP("test-transaction-tools")
    register_transaction_tools(app, DisputeRepository(), configure_logging("INFO"))
    return app


async def test_get_transaction_returns_seeded_record(mcp: FastMCP) -> None:
    async with Client(mcp) as client:
        result = await client.call_tool("get_transaction", {"transaction_id": "TXN-2001"})
    assert result.data.transaction_id == "TXN-2001"
    assert result.data.case_id == "CASE-1001"


async def test_get_transaction_unknown_id_raises(mcp: FastMCP) -> None:
    async with Client(mcp) as client:
        with pytest.raises(ToolError):
            await client.call_tool("get_transaction", {"transaction_id": "TXN-NOPE"})


async def test_get_authorization_returns_seeded_record(mcp: FastMCP) -> None:
    async with Client(mcp) as client:
        result = await client.call_tool("get_authorization", {"transaction_id": "TXN-2001"})
    assert result.data.authorization_code == "AUTH-9001"
    assert result.data.approved is True


async def test_get_settlement_returns_seeded_record(mcp: FastMCP) -> None:
    async with Client(mcp) as client:
        result = await client.call_tool("get_settlement", {"transaction_id": "TXN-2002"})
    assert result.data.settlement_id == "SETL-8002"


async def test_get_refund_or_reversal_returns_populated_list(mcp: FastMCP) -> None:
    async with Client(mcp) as client:
        result = await client.call_tool("get_refund_or_reversal", {"transaction_id": "TXN-2002"})
    assert len(result.data) == 1
    assert result.data[0].refund_id == "REFUND-7001"


async def test_get_refund_or_reversal_returns_empty_list_when_none(mcp: FastMCP) -> None:
    async with Client(mcp) as client:
        result = await client.call_tool("get_refund_or_reversal", {"transaction_id": "TXN-2001"})
    assert len(result.data) == 0


async def test_get_refund_or_reversal_unknown_transaction_raises(mcp: FastMCP) -> None:
    async with Client(mcp) as client:
        with pytest.raises(ToolError):
            await client.call_tool("get_refund_or_reversal", {"transaction_id": "TXN-NOPE"})
