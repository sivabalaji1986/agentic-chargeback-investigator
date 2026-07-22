"""Tests for dispute_mcp_server.logging's log_tool_call wrapper."""

import logging

import pytest

from dispute_mcp_server.logging import configure_logging, log_tool_call


def test_configure_logging_returns_a_named_logger() -> None:
    logger = configure_logging("INFO")
    assert logger.name == "dispute_mcp_server"
    assert logger.level == logging.INFO


def test_log_tool_call_logs_success_with_id_and_duration(
    caplog: pytest.LogCaptureFixture,
) -> None:
    logger = configure_logging("INFO")

    @log_tool_call(logger, "get_case", id_from=lambda case_id: case_id)
    def get_case(case_id: str) -> str:
        return f"found {case_id}"

    with caplog.at_level(logging.INFO, logger="dispute_mcp_server"):
        result = get_case("CASE-1001")

    assert result == "found CASE-1001"
    assert any(
        "tool=get_case" in r.message
        and "id=CASE-1001" in r.message
        and "outcome=success" in r.message
        for r in caplog.records
    )


def test_log_tool_call_logs_failure_without_leaking_exception_body(
    caplog: pytest.LogCaptureFixture,
) -> None:
    logger = configure_logging("INFO")

    @log_tool_call(logger, "get_case", id_from=lambda case_id: case_id)
    def get_case(case_id: str) -> str:
        raise ValueError("some sensitive internal detail")

    with caplog.at_level(logging.INFO, logger="dispute_mcp_server"):
        with pytest.raises(ValueError, match="some sensitive internal detail"):
            get_case("CASE-NOPE")

    failure_logs = [r for r in caplog.records if "outcome=failure" in r.message]
    assert len(failure_logs) == 1
    assert "tool=get_case" in failure_logs[0].message
    assert "id=CASE-NOPE" in failure_logs[0].message
    assert "ValueError" in failure_logs[0].message
    assert "some sensitive internal detail" not in failure_logs[0].message
