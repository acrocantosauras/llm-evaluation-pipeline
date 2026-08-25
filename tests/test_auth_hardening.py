"""Tests for authentication hardening.

- The development "first project" fallback must be EXPLICITLY enabled via
  ALLOW_DEV_AUTH_FALLBACK and never applies in production/CI.
- Production fails closed on missing config / invalid credentials.
"""

import os
import sys
import types
from unittest.mock import MagicMock

import pytest


@pytest.fixture()
def prod_env():
    """Force production settings cache to reset around each test."""
    from app.core.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _mock_heavy_modules():
    mock_pipeline = types.ModuleType("evaluator.pipeline")

    class MockPipeline:
        def evaluate(self, conversation, context):
            return {
                "relevance": 0.85,
                "hallucination": {"fraction_supported": 1.0, "flags": [], "details": []},
                "latency_ms": 42.5,
                "estimated_cost": 0.001,
            }

    mock_pipeline.EvaluationPipeline = MockPipeline
    for mod_name, mod in [
        ("evaluator.relevance", types.ModuleType("evaluator.relevance")),
        ("evaluator.hallucination", types.ModuleType("evaluator.hallucination")),
        ("evaluator.latency", types.ModuleType("evaluator.latency")),
        ("evaluator.cost", types.ModuleType("evaluator.cost")),
        ("evaluator.pipeline", mock_pipeline),
    ]:
        if mod is not mock_pipeline:
            if mod_name == "evaluator.relevance":
                mod.relevance_score = MagicMock(return_value=0.85)
            elif mod_name == "evaluator.hallucination":
                mod.hallucination_report = MagicMock(
                    return_value={"fraction_supported": 1.0, "flags": [], "details": []}
                )
            elif mod_name == "evaluator.latency":
                mod.measure_latency = MagicMock(return_value=42.5)
            elif mod_name == "evaluator.cost":
                mod.estimate_cost = MagicMock(return_value=0.001)
        sys.modules[mod_name] = mod


def _cleanup_modules():
    for m in [
        "evaluator.relevance",
        "evaluator.hallucination",
        "evaluator.latency",
        "evaluator.cost",
        "evaluator.pipeline",
    ]:
        sys.modules.pop(m, None)


@pytest.fixture()
def dev_client():
    """TestClient in development mode with a seeded project, no explicit fallback flag."""
    _mock_heavy_modules()

    import fakeredis
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    import app.db.models  # noqa: F401
    from app.core.config import get_settings
    from app.db.base import Base
    from app.db.models import Project
    from app.db.session import get_db
    from app.main import app
    from app.services import redis_queue as rq

    original_app_env = os.environ.get("APP_ENV")
    original_fallback = os.environ.get("ALLOW_DEV_AUTH_FALLBACK")
    os.environ["APP_ENV"] = "development"
    os.environ.pop("ALLOW_DEV_AUTH_FALLBACK", None)  # NOT explicitly enabled
    get_settings.cache_clear()

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def set_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    seed = TestSession()
    seed.add(Project(name="seed-project", description="Seeded"))
    seed.commit()
    seed.close()

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    fake = fakeredis.FakeRedis(decode_responses=True)
    original_get_redis = rq.get_redis_client
    rq.get_redis_client = lambda: fake

    from fastapi.testclient import TestClient

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c

    app.dependency_overrides.clear()
    rq.get_redis_client = original_get_redis
    fake.flushall()

    if original_app_env is None:
        os.environ.pop("APP_ENV", None)
    else:
        os.environ["APP_ENV"] = original_app_env
    if original_fallback is not None:
        os.environ["ALLOW_DEV_AUTH_FALLBACK"] = original_fallback
    get_settings.cache_clear()
    _cleanup_modules()


def test_dev_without_explicit_flag_fails_closed(dev_client):
    """Development mode WITHOUT ALLOW_DEV_AUTH_FALLBACK must not silently authenticate."""
    resp = dev_client.get("/api/v1/runs")
    assert resp.status_code == 401


def test_dev_with_explicit_flag_allows_fallback(dev_client, monkeypatch):
    """Development mode WITH the explicit flag falls back to a default project."""
    from app.core.config import get_settings

    monkeypatch.setenv("ALLOW_DEV_AUTH_FALLBACK", "true")
    get_settings.cache_clear()
    try:
        resp = dev_client.get("/api/v1/runs")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0
    finally:
        get_settings.cache_clear()


def test_production_ignores_dev_fallback_flag(prod_env, monkeypatch):
    """Even with the flag set, production must fail closed without credentials."""
    _mock_heavy_modules()

    import fakeredis
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    import app.db.models  # noqa: F401
    from app.core.config import get_settings
    from app.db.base import Base
    from app.db.models import Project
    from app.db.session import get_db
    from app.main import app
    from app.services import redis_queue as rq

    original_app_env = os.environ.get("APP_ENV")
    os.environ["APP_ENV"] = "production"
    monkeypatch.setenv("ALLOW_DEV_AUTH_FALLBACK", "true")  # must be ignored
    get_settings.cache_clear()

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    seed = TestSession()
    seed.add(Project(name="p", description=""))
    seed.commit()
    seed.close()

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    fake = fakeredis.FakeRedis(decode_responses=True)
    original = rq.get_redis_client
    rq.get_redis_client = lambda: fake

    try:
        from fastapi.testclient import TestClient

        with TestClient(app, raise_server_exceptions=False) as c:
            assert c.get("/api/v1/runs").status_code == 401
            assert (
                c.post("/api/v1/evaluations", json={"conversation": {}, "context": [{"text": "x"}]}).status_code == 401
            )
    finally:
        app.dependency_overrides.clear()
        rq.get_redis_client = original
        fake.flushall()
        if original_app_env is None:
            os.environ.pop("APP_ENV", None)
        else:
            os.environ["APP_ENV"] = original_app_env
        get_settings.cache_clear()
        _cleanup_modules()
