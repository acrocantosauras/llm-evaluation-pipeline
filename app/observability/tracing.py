"""OpenTelemetry tracing configuration.

Tracing is optional — if opentelemetry packages are not installed,
the tracing functions become no-ops and the application runs without traces.
"""

from __future__ import annotations

import logging
from collections.abc import Generator
from contextlib import contextmanager

logger = logging.getLogger(__name__)

_tracer = None
_initialized = False


def init_tracing(endpoint: str | None = None, service_name: str = "llm-eval-api") -> None:
    """Initialize OpenTelemetry tracing with OTLP exporter."""
    global _tracer, _initialized
    if _initialized:
        return

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource.create({"service.name": service_name})
        provider = TracerProvider(resource=resource)

        if endpoint:
            try:
                from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

                exporter = OTLPSpanExporter(endpoint=endpoint)
                provider.add_span_processor(BatchSpanProcessor(exporter))
                logger.info("OpenTelemetry exporter configured: endpoint=%s", endpoint)
            except ImportError:
                logger.warning("OTLP exporter not installed — tracing to console only")

        trace.set_tracer_provider(provider)
        _tracer = trace.get_tracer(service_name)
        _initialized = True
        logger.info("OpenTelemetry tracing initialized")
    except ImportError:
        logger.info("OpenTelemetry packages not installed — tracing disabled")
        _initialized = True  # Don't retry


@contextmanager
def trace_span(name: str, attributes: dict | None = None) -> Generator[None, None, None]:
    """Context manager that creates a tracing span (no-op if tracing unavailable)."""
    global _tracer
    if _tracer is None:
        yield
        return

    from opentelemetry.trace import StatusCode

    span = _tracer.start_span(name)
    if attributes:
        for k, v in attributes.items():
            if isinstance(v, (str, int, float, bool)):
                span.set_attribute(k, v)
    try:
        yield
        span.set_status(StatusCode.OK)
    except Exception as exc:
        span.set_status(StatusCode.ERROR, str(exc))
        span.record_exception(exc)
        raise
    finally:
        span.end()
