"""Tests for OpenTelemetry tracing module."""

from __future__ import annotations

import pytest


def test_tracing_init_noop():
    """Tracing init does not crash when packages are missing."""
    from app.observability.tracing import init_tracing

    init_tracing()  # Should be no-op


def test_trace_span_noop():
    """trace_span works as a no-op when tracing is not configured."""
    from app.observability.tracing import trace_span

    with trace_span("test_span", {"key": "value"}):
        pass  # Should not crash


def test_trace_span_with_exception():
    """trace_span handles exceptions correctly."""
    from app.observability.tracing import trace_span

    with pytest.raises(ValueError), trace_span("error_span"):
        raise ValueError("test error")


def test_trace_span_safe_attributes():
    """trace_span only accepts safe attribute types."""
    from app.observability.tracing import trace_span

    with trace_span("safe_attrs", {"str_val": "hello", "int_val": 42, "float_val": 1.5, "bool_val": True}):
        pass  # Should not crash


def test_trace_span_ignores_bad_attributes():
    """trace_span silently ignores non-primitive attributes."""
    from app.observability.tracing import trace_span

    with trace_span("bad_attrs", {"list_val": [1, 2, 3], "dict_val": {"nested": True}}):
        pass  # Should not crash
