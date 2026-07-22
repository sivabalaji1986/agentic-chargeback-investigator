"""Tests for mcp_client.py, using the real dispute-mcp-server in-process.

Real seed data (from Prompt 3), no mocking needed -- this is a genuine
integration test.
"""

from __future__ import annotations

import pytest

from transaction_agent.mcp_client import TransactionLookupError, get_case_and_transaction


async def test_get_case_and_transaction_returns_real_seeded_data() -> None:
    case_data, transaction_data = await get_case_and_transaction("CASE-1001")
    assert case_data["case_id"] == "CASE-1001"
    assert case_data["customer_id"] == "CUST-3001"
    assert transaction_data["transaction_id"] == "TXN-2001"
    assert transaction_data["case_id"] == "CASE-1001"


async def test_get_case_and_transaction_unknown_case_raises() -> None:
    with pytest.raises(TransactionLookupError):
        await get_case_and_transaction("CASE-NOPE")
