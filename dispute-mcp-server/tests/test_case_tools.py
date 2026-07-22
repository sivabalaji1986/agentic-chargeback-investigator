"""Tests for the case tool group, via an in-memory fastmcp.Client."""

import pytest
from fastmcp import Client, FastMCP
from fastmcp.exceptions import ToolError

from chargeback_contracts.mcp import (
    CreateAuditEntryRequest,
    McpStatus,
    UpdateCaseStatusRequest,
)
from dispute_mcp_server.logging import configure_logging
from dispute_mcp_server.repository import DisputeRepository
from dispute_mcp_server.tools.case_tools import register_case_tools


@pytest.fixture
def repository() -> DisputeRepository:
    return DisputeRepository()


@pytest.fixture
def mcp(repository: DisputeRepository) -> FastMCP:
    app = FastMCP("test-case-tools")
    register_case_tools(app, repository, configure_logging("INFO"))
    return app


async def test_get_case_returns_seeded_case(mcp: FastMCP) -> None:
    async with Client(mcp) as client:
        result = await client.call_tool("get_case", {"case_id": "CASE-1001"})
    assert result.data.case_id == "CASE-1001"
    assert result.data.customer_id == "CUST-3001"


async def test_get_case_unknown_id_raises_tool_error(mcp: FastMCP) -> None:
    async with Client(mcp) as client:
        with pytest.raises(ToolError):
            await client.call_tool("get_case", {"case_id": "CASE-NOPE"})


async def test_update_case_succeeds_and_persists_within_process(mcp: FastMCP) -> None:
    async with Client(mcp) as client:
        response = await client.call_tool(
            "update_case",
            {
                "request": UpdateCaseStatusRequest(
                    case_id="CASE-1001",
                    idempotency_key="idem-1",
                    new_status="closed",
                ).model_dump(mode="json")
            },
        )
        assert response.data.status == McpStatus.SUCCESS.value

        updated = await client.call_tool("get_case", {"case_id": "CASE-1001"})
        assert updated.data.status == "closed"


async def test_update_case_unknown_id_returns_failure_not_exception(mcp: FastMCP) -> None:
    async with Client(mcp) as client:
        response = await client.call_tool(
            "update_case",
            {
                "request": UpdateCaseStatusRequest(
                    case_id="CASE-NOPE",
                    idempotency_key="idem-2",
                    new_status="closed",
                ).model_dump(mode="json")
            },
        )
    assert response.data.status == McpStatus.FAILURE.value
    assert response.data.error.error_code == "case_not_found"


async def test_write_audit_succeeds(mcp: FastMCP) -> None:
    async with Client(mcp) as client:
        response = await client.call_tool(
            "write_audit",
            {
                "request": CreateAuditEntryRequest(
                    case_id="CASE-1002",
                    idempotency_key="idem-3",
                    event_description="Investigator reviewed merchant evidence.",
                ).model_dump(mode="json")
            },
        )
    assert response.data.status == McpStatus.SUCCESS.value


async def test_write_audit_unknown_case_returns_failure(mcp: FastMCP) -> None:
    async with Client(mcp) as client:
        response = await client.call_tool(
            "write_audit",
            {
                "request": CreateAuditEntryRequest(
                    case_id="CASE-NOPE",
                    idempotency_key="idem-4",
                    event_description="x",
                ).model_dump(mode="json")
            },
        )
    assert response.data.status == McpStatus.FAILURE.value


async def test_write_audit_failure_leaves_no_partial_audit_record(
    mcp: FastMCP, repository: DisputeRepository
) -> None:
    # Locks in the atomicity guarantee: append_audit_record checks case
    # existence before creating any record, so a failed write must leave
    # the audit log exactly as it was, not with a partial/orphaned entry.
    async with Client(mcp) as client:
        await client.call_tool(
            "write_audit",
            {
                "request": CreateAuditEntryRequest(
                    case_id="CASE-NOPE",
                    idempotency_key="idem-5",
                    event_description="should not be recorded",
                ).model_dump(mode="json")
            },
        )
    assert repository._audit_log == []
