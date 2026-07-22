"""Entrypoint: builds the FastMCP app and registers all tool groups."""

from __future__ import annotations

from fastmcp import FastMCP

from dispute_mcp_server.config import load_settings
from dispute_mcp_server.logging import configure_logging
from dispute_mcp_server.repository import DisputeRepository
from dispute_mcp_server.tools.case_tools import register_case_tools
from dispute_mcp_server.tools.customer_tools import register_customer_tools
from dispute_mcp_server.tools.merchant_tools import register_merchant_tools
from dispute_mcp_server.tools.transaction_tools import register_transaction_tools


def create_app() -> FastMCP:
    settings = load_settings()
    logger = configure_logging(settings.log_level)
    repository = DisputeRepository()

    mcp = FastMCP(settings.service_name)
    register_case_tools(mcp, repository, logger)
    register_transaction_tools(mcp, repository, logger)
    register_customer_tools(mcp, repository, logger)
    register_merchant_tools(mcp, repository, logger)
    return mcp


mcp = create_app()


if __name__ == "__main__":
    mcp.run()
