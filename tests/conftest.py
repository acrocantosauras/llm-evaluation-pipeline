import os
import sys
import types
from unittest.mock import MagicMock

import pytest

# Set environment BEFORE any app imports
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["APP_ENV"] = "development"
os.environ["LOG_LEVEL"] = "warning"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"


VALID_REQUEST = {
    "conversation": {
        "model_response": "Ibuprofen may cause stomach pain and nausea.",
        "input_tokens": 40,
        "output_tokens": 15,
    },
    "context": [
        {"id": "1", "text": "Ibuprofen can cause stomach upset, nausea, dizziness."},
    ],
}


def _mock_heavy_modules():
    """Mock the heavy ML modules to avoid model downloads during tests."""
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
            from evaluator.cost import estimate_cost
            from evaluator.hallucination import hallucination_report
            from evaluator.latency import measure_latency
            from evaluator.relevance import relevance_score

            response = conversation.get("model_response", "")
            return {
                "relevance": relevance_score(response, context),
                "hallucination": hallucination_report(response, context),
                "latency_ms": conversation.get("latency_ms") or measure_latency(lambda: None),
                "estimated_cost": estimate_cost(conversation),
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


@pytest.fixture()
def client():
    """Create a TestClient with a SQLite in-memory database, mocked evaluator, and fakeredis."""
    _mock_heavy_modules()

    import fakeredis
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    import app.db.models  # noqa: F401
    from app.db.base import Base
    from app.db.session import get_db
    from app.main import app

    # Use SQLite for tests
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

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    # Seed a default project for the dev-mode auth fallback
    from app.db.models import Project

    seed_db = TestSession()
    if not seed_db.query(Project).first():
        default_project = Project(name="default", description="Default test project")
        seed_db.add(default_project)
        seed_db.commit()
    seed_db.close()

    # Patch Redis with fakeredis
    fake = fakeredis.FakeRedis(decode_responses=True)
    import app.services.redis_queue as rq

    original_get_redis = rq.get_redis_client
    rq.get_redis_client = lambda: fake

    from fastapi.testclient import TestClient as TC

    with TC(app) as c:
        yield c

    app.dependency_overrides.clear()
    rq.get_redis_client = original_get_redis
    fake.flushall()

    # Restore evaluator modules
    for mod_name in [
        "evaluator.relevance",
        "evaluator.hallucination",
        "evaluator.latency",
        "evaluator.cost",
        "evaluator.pipeline",
    ]:
        sys.modules.pop(mod_name, None)


@pytest.fixture()
def db_session():
    """Provide a direct database session for service-level tests."""
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    import app.db.models  # noqa: F401
    from app.db.base import Base

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

    session = TestSession()
    yield session
    session.close()
