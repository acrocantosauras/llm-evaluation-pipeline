"""Tests for Phase 4 authentication, authorization, and security."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Security utility tests
# ---------------------------------------------------------------------------


def test_generate_api_key():
    """API key generation produces unique keys."""
    from app.core.security import generate_api_key

    key1 = generate_api_key()
    key2 = generate_api_key()
    assert key1 != key2
    assert key1.startswith("llm_eval_")


def test_hash_api_key():
    """Key hashing is deterministic."""
    from app.core.security import hash_api_key

    key = "llm_eval_test_key"
    h1 = hash_api_key(key)
    h2 = hash_api_key(key)
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex digest


def test_verify_api_key():
    """Key verification works correctly."""
    from app.core.security import generate_api_key, hash_api_key, verify_api_key

    key = generate_api_key()
    key_hash = hash_api_key(key)
    assert verify_api_key(key, key_hash) is True
    assert verify_api_key("wrong_key", key_hash) is False


def test_key_is_not_stored_plaintext():
    """The hash is different from the plaintext key."""
    from app.core.security import generate_api_key, hash_api_key

    key = generate_api_key()
    key_hash = hash_api_key(key)
    assert key != key_hash


# ---------------------------------------------------------------------------
# Rate limiting tests
# ---------------------------------------------------------------------------


def test_rate_limit_allows_within_window():
    """Requests within the limit are allowed."""
    from app.api.deps import _check_rate_limit

    key = str(uuid.uuid4())
    assert _check_rate_limit(key, 3, 60.0) is True
    assert _check_rate_limit(key, 3, 60.0) is True
    assert _check_rate_limit(key, 3, 60.0) is True


def test_rate_limit_blocks_over_limit():
    """Requests over the limit are blocked."""
    from app.api.deps import _check_rate_limit

    key = str(uuid.uuid4())
    assert _check_rate_limit(key, 2, 60.0) is True
    assert _check_rate_limit(key, 2, 60.0) is True
    assert _check_rate_limit(key, 2, 60.0) is False


# ---------------------------------------------------------------------------
# Auth route tests (with mocked DB)
# ---------------------------------------------------------------------------


def test_project_model_creation():
    """Project model can be instantiated."""
    from app.db.models import Project

    project = Project(
        id=uuid.uuid4(),
        created_at=datetime.now(timezone.utc),
        name="Test Project",
        description="A test project",
    )
    assert project.name == "Test Project"
    assert project.id is not None


def test_api_key_model_creation():
    """ApiKey model can be instantiated."""
    from app.db.models import ApiKey

    api_key = ApiKey(
        id=uuid.uuid4(),
        created_at=datetime.now(timezone.utc),
        project_id=uuid.uuid4(),
        name="test-key",
        key_hash="abc123",
        enabled=True,
    )
    assert api_key.name == "test-key"
    assert api_key.enabled is True
    assert api_key.last_used_at is None
