"""Tests for structured logging module."""

from __future__ import annotations

import json
import logging


def test_json_formatter():
    """JSONFormatter produces valid JSON output."""
    from app.observability.logging import JSONFormatter

    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Test message",
        args=None,
        exc_info=None,
    )
    output = formatter.format(record)
    parsed = json.loads(output)
    assert parsed["level"] == "INFO"
    assert parsed["message"] == "Test message"
    assert "timestamp" in parsed
    assert parsed["service"] == "llm-eval-api"


def test_json_formatter_with_exception():
    """JSONFormatter includes exception info."""
    from app.observability.logging import JSONFormatter

    formatter = JSONFormatter()
    try:
        raise ValueError("test error")
    except ValueError:
        import sys

        exc_info = sys.exc_info()
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Error occurred",
            args=None,
            exc_info=exc_info,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert "exception" in parsed
        assert "ValueError" in parsed["exception"]


def test_json_formatter_with_extra_fields():
    """JSONFormatter includes extra fields from record."""
    from app.observability.logging import JSONFormatter

    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="With extras",
        args=None,
        exc_info=None,
    )
    record.request_id = "req-123"
    record.job_id = "job-456"
    record.duration_ms = 42.5

    output = formatter.format(record)
    parsed = json.loads(output)
    assert parsed["request_id"] == "req-123"
    assert parsed["job_id"] == "job-456"
    assert parsed["duration_ms"] == 42.5


def test_configure_structured_logging():
    """configure_structured_logging does not crash."""
    from app.observability.logging import configure_structured_logging

    configure_structured_logging("INFO")
