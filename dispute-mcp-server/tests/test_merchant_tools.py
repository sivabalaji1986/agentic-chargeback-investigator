"""Tests for the merchant tool group, via an in-memory fastmcp.Client."""

import pytest
from fastmcp import Client, FastMCP
from fastmcp.exceptions import ToolError

from dispute_mcp_server.logging import configure_logging
from dispute_mcp_server.repository import DisputeRepository
from dispute_mcp_server.tools.merchant_tools import register_merchant_tools


@pytest.fixture
def mcp() -> FastMCP:
    app = FastMCP("test-merchant-tools")
    register_merchant_tools(app, DisputeRepository(), configure_logging("INFO"))
    return app


async def test_get_merchant_evidence_returns_seeded_record(mcp: FastMCP) -> None:
    async with Client(mcp) as client:
        result = await client.call_tool("get_merchant_evidence", {"case_id": "CASE-1002"})
    assert result.data.acknowledgement is True


async def test_get_merchant_evidence_unknown_case_raises(mcp: FastMCP) -> None:
    async with Client(mcp) as client:
        with pytest.raises(ToolError):
            await client.call_tool("get_merchant_evidence", {"case_id": "CASE-NOPE"})


async def test_get_delivery_details_reflects_non_delivery(mcp: FastMCP) -> None:
    async with Client(mcp) as client:
        result = await client.call_tool("get_delivery_details", {"case_id": "CASE-1001"})
    assert result.data.delivered is False


async def test_get_delivery_details_reflects_delivery(mcp: FastMCP) -> None:
    async with Client(mcp) as client:
        result = await client.call_tool("get_delivery_details", {"case_id": "CASE-1002"})
    assert result.data.delivered is True
    assert result.data.tracking_number == "PS-773311"


async def test_get_cancellation_details_reflects_cancellation(mcp: FastMCP) -> None:
    async with Client(mcp) as client:
        result = await client.call_tool("get_cancellation_details", {"case_id": "CASE-1003"})
    assert result.data.cancelled is True
    assert result.data.confirmation_reference == "CANCEL-CONF-7788"


async def test_get_cancellation_details_unknown_case_raises(mcp: FastMCP) -> None:
    async with Client(mcp) as client:
        with pytest.raises(ToolError):
            await client.call_tool("get_cancellation_details", {"case_id": "CASE-NOPE"})
