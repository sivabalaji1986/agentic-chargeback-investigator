"""Tests for the customer tool group, via an in-memory fastmcp.Client."""

import pytest
from fastmcp import Client, FastMCP
from fastmcp.exceptions import ToolError

from dispute_mcp_server.logging import configure_logging
from dispute_mcp_server.repository import DisputeRepository
from dispute_mcp_server.tools.customer_tools import register_customer_tools


@pytest.fixture
def mcp() -> FastMCP:
    app = FastMCP("test-customer-tools")
    register_customer_tools(app, DisputeRepository(), configure_logging("INFO"))
    return app


async def test_get_customer_profile_returns_seeded_record(mcp: FastMCP) -> None:
    async with Client(mcp) as client:
        result = await client.call_tool("get_customer_profile", {"customer_id": "CUST-3001"})
    assert result.data.display_name == "Jane Doe"


async def test_get_customer_profile_unknown_id_raises(mcp: FastMCP) -> None:
    async with Client(mcp) as client:
        with pytest.raises(ToolError):
            await client.call_tool("get_customer_profile", {"customer_id": "CUST-NOPE"})


async def test_get_prior_disputes_returns_populated_list(mcp: FastMCP) -> None:
    async with Client(mcp) as client:
        result = await client.call_tool("get_prior_disputes", {"customer_id": "CUST-3003"})
    assert len(result.data) == 2


async def test_get_prior_disputes_returns_empty_list_when_none(mcp: FastMCP) -> None:
    async with Client(mcp) as client:
        result = await client.call_tool("get_prior_disputes", {"customer_id": "CUST-3002"})
    assert len(result.data) == 0


async def test_get_prior_disputes_unknown_customer_raises(mcp: FastMCP) -> None:
    async with Client(mcp) as client:
        with pytest.raises(ToolError):
            await client.call_tool("get_prior_disputes", {"customer_id": "CUST-NOPE"})


async def test_get_refund_history_returns_populated_list(mcp: FastMCP) -> None:
    async with Client(mcp) as client:
        result = await client.call_tool("get_refund_history", {"customer_id": "CUST-3001"})
    assert len(result.data) == 1


async def test_get_refund_history_returns_empty_list_when_none(mcp: FastMCP) -> None:
    async with Client(mcp) as client:
        result = await client.call_tool("get_refund_history", {"customer_id": "CUST-3002"})
    assert len(result.data) == 0


async def test_get_refund_history_unknown_customer_raises(mcp: FastMCP) -> None:
    async with Client(mcp) as client:
        with pytest.raises(ToolError):
            await client.call_tool("get_refund_history", {"customer_id": "CUST-NOPE"})
