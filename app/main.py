import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import (
    auth,
    baselines,
    datasets,
    evaluations,
    health,
    jobs,
    profiles,
    runs,
)
from app.core.config import get_settings
from app.observability import metrics
from app.observability.logging import configure_structured_logging
from app.observability.tracing import init_tracing

settings = get_settings()

# Logging setup: JSON structured logs in production/ci, human-readable otherwise.
if settings.APP_ENV in ("production", "ci"):
    configure_structured_logging(settings.LOG_LEVEL)
else:
    logging.basicConfig(
        level=settings.LOG_LEVEL.upper(),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle — startup/shutdown hooks."""
    if settings.OPENTELEMETRY_ENABLED:
        # Safe no-op if OpenTelemetry packages are not installed.
        init_tracing(settings.OPENTELEMETRY_ENDPOINT or None, service_name="llm-eval-api")
    logger.info("Starting application: env=%s", settings.APP_ENV)
    yield
    logger.info("Shutting down application")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        description="Production-grade LLM Evaluation & Quality-Gate Platform API",
        version="0.4.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    # Request timing + correlation-ID + metrics middleware
    @app.middleware("http")
    async def timing_middleware(request: Request, call_next):
        # Correlation ID: honor an inbound X-Request-ID or generate one.
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        start = time.time()
        response = await call_next(request)
        duration = time.time() - start
        duration_ms = round(duration * 1000, 2)

        response.headers["X-Response-Time"] = f"{duration_ms}ms"
        response.headers["X-Request-ID"] = request_id

        # Use the matched route template (not the raw path) to bound metric cardinality.
        route = request.scope.get("route")
        path_label = getattr(route, "path", request.url.path)
        metrics.inc_api_requests(request.method, path_label, response.status_code)
        metrics.observe_api_duration(request.method, path_label, duration)

        # Structured log with correlation ID
        logger.info(
            "%s %s %d %sms",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            extra={
                "request_id": request_id,
                "duration_ms": duration_ms,
                "event": "http_request",
            },
        )
        return response

    # Routes
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(evaluations.router)
    app.include_router(runs.router)
    app.include_router(jobs.router)
    app.include_router(baselines.router)
    app.include_router(profiles.router)
    app.include_router(datasets.router)

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        logger.exception("Unhandled exception: request_id=%s path=%s", request_id, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
            headers={"X-Request-ID": request_id},
        )

    logger.info("Application created: env=%s", settings.APP_ENV)

    return app


app = create_app()
