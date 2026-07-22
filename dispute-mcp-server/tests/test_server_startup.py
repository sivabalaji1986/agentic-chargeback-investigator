"""Server startup and tool discovery tests."""

from fastmcp import Client

from dispute_mcp_server.main import create_app

EXPECTED_TOOL_NAMES = {
    "get_case",
    "update_case",
    "write_audit",
    "get_transaction",
    "get_authorization",
    "get_settlement",
    "get_refund_or_reversal",
    "get_customer_profile",
    "get_prior_disputes",
    "get_refund_history",
    "get_merchant_evidence",
    "get_delivery_details",
    "get_cancellation_details",
}


async def test_app_starts_and_exposes_exactly_thirteen_tools() -> None:
    app = create_app()
    async with Client(app) as client:
        tools = await client.list_tools()
    tool_names = {tool.name for tool in tools}
    assert tool_names == EXPECTED_TOOL_NAMES
    assert len(EXPECTED_TOOL_NAMES) == 13


async def test_creating_the_app_twice_does_not_error() -> None:
    # Confirms tool registration has no hidden global/shared state that
    # breaks on a second instantiation (e.g. two test runs in one process).
    first = create_app()
    second = create_app()
    async with Client(first) as client:
        first_tools = {t.name for t in await client.list_tools()}
    async with Client(second) as client:
        second_tools = {t.name for t in await client.list_tools()}
    assert first_tools == second_tools == EXPECTED_TOOL_NAMES
