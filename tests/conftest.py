import os
import sys
import types
from unittest.mock import MagicMock

import pytest

# Set DATABASE_URL to SQLite BEFORE any app imports
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["APP_ENV"] = "testing"
os.environ["LOG_LEVEL"] = "warning"


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
    """Create a TestClient with a SQLite in-memory database and mocked evaluator.

    The heavy ML modules are mocked for the lifetime of this fixture to avoid
    model downloads. Evaluator-specific tests handle their own mocking.
    """
    _mock_heavy_modules()

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    import app.db.models  # noqa: F401
    from app.db.base import Base
    from app.db.session import get_db
    from app.main import app

    # StaticPool ensures all connections share the same in-memory database
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()

    # Restore original evaluator modules so evaluator-specific tests aren't affected
    for mod_name in [
        "evaluator.relevance",
        "evaluator.hallucination",
        "evaluator.latency",
        "evaluator.cost",
        "evaluator.pipeline",
    ]:
        sys.modules.pop(mod_name, None)
