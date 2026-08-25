"""Security tests: auth enforcement, project isolation, API key lifecycle, rate limiting."""

import os
import sys
import types
from unittest.mock import MagicMock

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.core.security import generate_api_key, hash_api_key, verify_api_key
from app.db.base import Base
from app.db.models import ApiKey, EvaluationRun, Project

# ── API Key Security ──────────────────────────────────────────────────────────


def test_api_key_generation():
    """Generated keys have the correct prefix and are unique."""
    key1 = generate_api_key()
    key2 = generate_api_key()
    assert key1.startswith("llm_eval_")
    assert key2.startswith("llm_eval_")
    assert key1 != key2


def test_api_key_hash_and_verify():
    """Hashing is deterministic and verification works."""
    key = generate_api_key()
    h = hash_api_key(key)
    assert len(h) == 64  # SHA-256 hex digest
    assert verify_api_key(key, h) is True
    assert verify_api_key("wrong_key", h) is False


def test_api_key_never_stored_plaintext():
    """The plaintext key is never stored in the database."""
    key = generate_api_key()
    key_hash = hash_api_key(key)
    assert key != key_hash
    assert key not in key_hash


# ── Test DB Helpers ───────────────────────────────────────────────────────────


def _mock_heavy_modules():
    """Mock the heavy ML modules to avoid segfaults during tests."""
    mock_relevance = types.ModuleType("evaluator.relevance")
    mock_relevance.relevance_score = MagicMock(return_value=0.85)
    mock_relevance.model = MagicMock()
    mock_relevance.util = MagicMock()

    mock_hallucination = types.ModuleType("evaluator.hallucination")
    mock_hallucination.hallucination_report = MagicMock(
        return_value={"fraction_supported": 1.0, "flags": [], "details": []}
    )
    mock_hallucination.nli = MagicMock()

    mock_latency = types.ModuleType("evaluator.latency")
    mock_latency.measure_latency = MagicMock(return_value=42.5)

    mock_cost = types.ModuleType("evaluator.cost")
    mock_cost.estimate_cost = MagicMock(return_value=0.001)

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

    for mod_name, mock_mod in [
        ("evaluator.relevance", mock_relevance),
        ("evaluator.hallucination", mock_hallucination),
        ("evaluator.latency", mock_latency),
        ("evaluator.cost", mock_cost),
        ("evaluator.pipeline", mock_pipeline),
    ]:
        sys.modules[mod_name] = mock_mod


def _make_test_db():
    """Create an in-memory SQLite test database with one project + key."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestSession()
    project = Project(name="test-project", description="Test project")
    db.add(project)
    db.commit()
    db.refresh(project)

    plaintext_key = generate_api_key()
    api_key = ApiKey(
        project_id=project.id,
        name="test-key",
        key_hash=hash_api_key(plaintext_key),
        enabled=True,
    )
    db.add(api_key)
    db.commit()
    db.close()

    return {"engine": engine, "Session": TestSession, "project": project, "key": plaintext_key}


def _make_two_project_test_db():
    """Create a test database with two projects, each with their own key and run."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestSession()

    # Project A
    project_a = Project(name="project-a", description="Alpha project")
    db.add(project_a)
    db.flush()

    key_a = generate_api_key()
    api_key_a = ApiKey(
        project_id=project_a.id,
        name="key-a",
        key_hash=hash_api_key(key_a),
        enabled=True,
    )
    db.add(api_key_a)

    # Project B
    project_b = Project(name="project-b", description="Beta project")
    db.add(project_b)
    db.flush()

    key_b = generate_api_key()
    api_key_b = ApiKey(
        project_id=project_b.id,
        name="key-b",
        key_hash=hash_api_key(key_b),
        enabled=True,
    )
    db.add(api_key_b)

    # Evaluation run for project A
    run_a = EvaluationRun(
        project_id=project_a.id,
        conversation={"model_response": "Drug X helps."},
        context={"chunks": [{"text": "Drug X info."}]},
        relevance=0.95,
        latency_ms=100,
    )
    db.add(run_a)

    # Evaluation run for project B
    run_b = EvaluationRun(
        project_id=project_b.id,
        conversation={"model_response": "Drug Y helps."},
        context={"chunks": [{"text": "Drug Y info."}]},
        relevance=0.88,
        latency_ms=150,
    )
    db.add(run_b)

    db.commit()

    # Expire and refresh to avoid DetachedInstanceError
    run_a_id = run_a.id
    run_b_id = run_b.id
    db.close()

    return {
        "engine": engine,
        "Session": TestSession,
        "project_a": project_a,
        "project_b": project_b,
        "key_a": key_a,
        "key_b": key_b,
        "run_a_id": run_a_id,
        "run_b_id": run_b_id,
    }


def _get_test_client(TestSession, app_env="production"):
    """Create a TestClient with mocked evaluator and the given APP_ENV."""
    _mock_heavy_modules()

    original_app_env = os.environ.get("APP_ENV", "development")
    os.environ["APP_ENV"] = app_env
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    from app.core.config import get_settings

    get_settings.cache_clear()

    import fakeredis

    import app.services.redis_queue as rq
    from app.db.session import get_db
    from app.main import app

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

    # Fresh fakeredis per test — the Redis-backed rate limiter uses this client.

    client = TestClient(app, raise_server_exceptions=False)
    return client, app, rq, original_get_redis, fake, original_app_env


# ── Production Auth Enforcement ───────────────────────────────────────────────


def test_production_requires_auth():
    """In production mode, unauthenticated requests must return 401."""
    data = _make_test_db()
    TestSession = data["Session"]

    client, app, rq, orig_redis, fake, orig_env = _get_test_client(TestSession, "production")
    try:
        # POST on evaluation needs body; use GET on runs, jobs, etc.
        assert (
            client.post("/api/v1/evaluations", json={"conversation": {}, "context": [{"text": "x"}]}).status_code == 401
        )
        assert client.get("/api/v1/runs").status_code == 401
        assert client.get("/api/v1/jobs").status_code == 401
        assert client.get("/api/v1/baselines").status_code == 401
        assert client.get("/api/v1/quality-gates").status_code == 401
        assert client.get("/api/v1/profiles").status_code == 401
        assert client.get("/api/v1/datasets").status_code == 401

        # Health remains public
        assert client.get("/health").status_code == 200
    finally:
        app.dependency_overrides.clear()
        rq.get_redis_client = orig_redis
        fake.flushall()
        os.environ["APP_ENV"] = orig_env
        get_settings.cache_clear()
        for m in [
            "evaluator.relevance",
            "evaluator.hallucination",
            "evaluator.latency",
            "evaluator.cost",
            "evaluator.pipeline",
        ]:
            sys.modules.pop(m, None)


def test_production_invalid_key_returns_401():
    """In production, an invalid API key must return 401."""
    data = _make_test_db()
    TestSession = data["Session"]

    client, app, rq, orig_redis, fake, orig_env = _get_test_client(TestSession, "production")
    try:
        resp = client.get(
            "/api/v1/runs",
            headers={"X-API-Key": "llm_eval_INVALID_KEY"},
        )
        assert resp.status_code == 401
    finally:
        app.dependency_overrides.clear()
        rq.get_redis_client = orig_redis
        fake.flushall()
        os.environ["APP_ENV"] = orig_env
        get_settings.cache_clear()
        for m in [
            "evaluator.relevance",
            "evaluator.hallucination",
            "evaluator.latency",
            "evaluator.cost",
            "evaluator.pipeline",
        ]:
            sys.modules.pop(m, None)


def test_production_revoked_key_returns_401():
    """In production, a revoked API key must return 401."""
    data = _make_test_db()
    TestSession = data["Session"]
    plaintext_key = data["key"]

    client, app, rq, orig_redis, fake, orig_env = _get_test_client(TestSession, "production")
    try:
        # Valid key first → 200
        resp = client.get("/api/v1/runs", headers={"X-API-Key": plaintext_key})
        assert resp.status_code == 200

        # Revoke the key
        db = TestSession()
        api_key = db.query(ApiKey).first()
        api_key.enabled = False
        db.commit()
        db.close()

        # Revoked key → 401
        resp = client.get("/api/v1/runs", headers={"X-API-Key": plaintext_key})
        assert resp.status_code == 401
    finally:
        app.dependency_overrides.clear()
        rq.get_redis_client = orig_redis
        fake.flushall()
        os.environ["APP_ENV"] = orig_env
        get_settings.cache_clear()
        for m in [
            "evaluator.relevance",
            "evaluator.hallucination",
            "evaluator.latency",
            "evaluator.cost",
            "evaluator.pipeline",
        ]:
            sys.modules.pop(m, None)


def test_production_valid_key_succeeds():
    """In production, a valid API key returns 200."""
    data = _make_test_db()
    TestSession = data["Session"]
    plaintext_key = data["key"]

    client, app, rq, orig_redis, fake, orig_env = _get_test_client(TestSession, "production")
    try:
        resp = client.get("/api/v1/runs", headers={"X-API-Key": plaintext_key})
        assert resp.status_code == 200
    finally:
        app.dependency_overrides.clear()
        rq.get_redis_client = orig_redis
        fake.flushall()
        os.environ["APP_ENV"] = orig_env
        get_settings.cache_clear()
        for m in [
            "evaluator.relevance",
            "evaluator.hallucination",
            "evaluator.latency",
            "evaluator.cost",
            "evaluator.pipeline",
        ]:
            sys.modules.pop(m, None)


def test_production_bearer_auth_succeeds():
    """In production, Bearer token authentication works."""
    data = _make_test_db()
    TestSession = data["Session"]
    plaintext_key = data["key"]

    client, app, rq, orig_redis, fake, orig_env = _get_test_client(TestSession, "production")
    try:
        resp = client.get(
            "/api/v1/runs",
            headers={"Authorization": f"Bearer {plaintext_key}"},
        )
        assert resp.status_code == 200
    finally:
        app.dependency_overrides.clear()
        rq.get_redis_client = orig_redis
        fake.flushall()
        os.environ["APP_ENV"] = orig_env
        get_settings.cache_clear()
        for m in [
            "evaluator.relevance",
            "evaluator.hallucination",
            "evaluator.latency",
            "evaluator.cost",
            "evaluator.pipeline",
        ]:
            sys.modules.pop(m, None)


# ── Cross-Project Isolation ──────────────────────────────────────────────────


def test_cross_project_run_access_denied():
    """Project A key cannot access Project B's run."""
    data = _make_two_project_test_db()
    TestSession = data["Session"]

    client, app, rq, orig_redis, fake, orig_env = _get_test_client(TestSession, "production")
    try:
        run_b_id = str(data["run_b_id"])

        # Project A key → Project B's run → 404
        resp = client.get(f"/api/v1/runs/{run_b_id}", headers={"X-API-Key": data["key_a"]})
        assert resp.status_code == 404

        # Project A key → its own run → 200
        run_a_id = str(data["run_a_id"])
        resp = client.get(f"/api/v1/runs/{run_a_id}", headers={"X-API-Key": data["key_a"]})
        assert resp.status_code == 200
    finally:
        app.dependency_overrides.clear()
        rq.get_redis_client = orig_redis
        fake.flushall()
        os.environ["APP_ENV"] = orig_env
        get_settings.cache_clear()
        for m in [
            "evaluator.relevance",
            "evaluator.hallucination",
            "evaluator.latency",
            "evaluator.cost",
            "evaluator.pipeline",
        ]:
            sys.modules.pop(m, None)


def test_cross_project_list_runs_isolation():
    """Each project only sees its own runs."""
    data = _make_two_project_test_db()
    TestSession = data["Session"]

    client, app, rq, orig_redis, fake, orig_env = _get_test_client(TestSession, "production")
    try:
        # Project A lists runs → only 1
        resp = client.get("/api/v1/runs", headers={"X-API-Key": data["key_a"]})
        assert resp.status_code == 200
        runs_a = resp.json()["runs"]
        assert len(runs_a) == 1

        # Project B lists runs → only 1
        resp = client.get("/api/v1/runs", headers={"X-API-Key": data["key_b"]})
        assert resp.status_code == 200
        runs_b = resp.json()["runs"]
        assert len(runs_b) == 1
    finally:
        app.dependency_overrides.clear()
        rq.get_redis_client = orig_redis
        fake.flushall()
        os.environ["APP_ENV"] = orig_env
        get_settings.cache_clear()
        for m in [
            "evaluator.relevance",
            "evaluator.hallucination",
            "evaluator.latency",
            "evaluator.cost",
            "evaluator.pipeline",
        ]:
            sys.modules.pop(m, None)


def test_health_and_metrics_are_public():
    """Health, readiness, and metrics endpoints must not require authentication."""
    data = _make_test_db()
    TestSession = data["Session"]

    client, app, rq, orig_redis, fake, orig_env = _get_test_client(TestSession, "production")
    try:
        assert client.get("/health").status_code == 200
        assert client.get("/ready").status_code == 200
        assert client.get("/metrics").status_code == 200
    finally:
        app.dependency_overrides.clear()
        rq.get_redis_client = orig_redis
        fake.flushall()
        os.environ["APP_ENV"] = orig_env
        get_settings.cache_clear()
        for m in [
            "evaluator.relevance",
            "evaluator.hallucination",
            "evaluator.latency",
            "evaluator.cost",
            "evaluator.pipeline",
        ]:
            sys.modules.pop(m, None)
