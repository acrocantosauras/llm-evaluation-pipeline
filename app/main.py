import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import baselines, datasets, evaluations, health, jobs, profiles, runs
from app.core.config import get_settings

settings = get_settings()

logging.basicConfig(level=settings.LOG_LEVEL.upper())
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        description="Production-grade LLM Evaluation & Quality-Gate Platform API",
        version="0.3.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(evaluations.router)
    app.include_router(runs.router)
    app.include_router(jobs.router)
    app.include_router(baselines.router)
    app.include_router(profiles.router)
    app.include_router(datasets.router)

    logger.info("Application started: env=%s", settings.APP_ENV)

    return app


app = create_app()
