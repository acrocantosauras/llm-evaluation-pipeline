"""Tests for API key hardening: expiry enforcement, rotation, prefixes, last_used_at."""

from datetime import datetime, timedelta, timezone

import pytest


@pytest.fixture()
def key_db():
    """In-memory DB with one project; returns (Session, project)."""
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    import app.db.models  # noqa: F401
    from app.db.base import Base
    from app.db.models import Project

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def set_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestSession()
    project = Project(name="proj", description="")
    db.add(project)
    db.commit()
    db.refresh(project)
    return db, project


def _make_key(db, project, expires_at=None, enabled=True):
    from app.core.security import generate_api_key, hash_api_key, key_prefix
    from app.db.models import ApiKey

    plaintext = generate_api_key()
    key = ApiKey(
        project_id=project.id,
        name="k",
        key_hash=hash_api_key(plaintext),
        key_prefix=key_prefix(plaintext),
        enabled=enabled,
        expires_at=expires_at,
    )
    db.add(key)
    db.commit()
    db.refresh(key)
    return key, plaintext


def test_valid_unexpired_key_authenticates(key_db):
    db, project = key_db
    from app.api.deps import _get_project_from_key
    from app.core.security import hash_api_key

    key, plaintext = _make_key(db, project, expires_at=datetime.now(timezone.utc) + timedelta(days=30))

    result = _get_project_from_key(hash_api_key(plaintext), db)
    assert result is not None
    found_project, found_key = result
    assert found_project.id == project.id
    assert found_key.id == key.id
    # last_used_at was written on first use
    assert found_key.last_used_at is not None


def test_expired_key_is_rejected(key_db):
    db, project = key_db
    from app.api.deps import _get_project_from_key
    from app.core.security import hash_api_key

    key, plaintext = _make_key(db, project, expires_at=datetime.now(timezone.utc) - timedelta(seconds=1))

    assert _get_project_from_key(hash_api_key(plaintext), db) is None


def test_disabled_key_is_rejected(key_db):
    db, project = key_db
    from app.api.deps import _get_project_from_key
    from app.core.security import hash_api_key

    _, plaintext = _make_key(db, project, enabled=False)
    assert _get_project_from_key(hash_api_key(plaintext), db) is None


def test_last_used_at_write_is_throttled(key_db):
    """Repeated auth within the throttle window does not rewrite last_used_at."""
    db, project = key_db
    from app.api.deps import LAST_USED_UPDATE_INTERVAL, _get_project_from_key
    from app.core.security import hash_api_key

    _, plaintext = _make_key(db, project)

    first_hash = hash_api_key(plaintext)
    _, key_after_first = _get_project_from_key(first_hash, db)
    first_used = key_after_first.last_used_at
    assert first_used is not None

    # Second lookup immediately after — last_used_at must be unchanged (no write).
    _, key_after_second = _get_project_from_key(first_hash, db)
    assert key_after_second.last_used_at == first_used

    # After the throttle window elapses it updates again.
    key_row = key_after_second
    key_row.last_used_at = first_used - timedelta(seconds=LAST_USED_UPDATE_INTERVAL + 5)
    db.commit()
    _, key_after_third = _get_project_from_key(first_hash, db)
    assert key_after_third.last_used_at > first_used - timedelta(seconds=LAST_USED_UPDATE_INTERVAL)


def test_rotation_disables_old_and_issues_new(client):
    """End-to-end rotation via the API: old key disabled, new key returned once."""
    # Create a project
    proj = client.post("/api/v1/projects", json={"name": "rot-project"}).json()

    # Create a key
    created = client.post(f"/api/v1/projects/{proj['id']}/api-keys", json={"name": "old-key"}).json()
    old_plaintext = created["key"]
    assert created["key_prefix"].endswith("...")
    assert len(created["key_prefix"]) <= 20  # safe display prefix, never the full key

    # Old key authenticates
    resp = client.get("/api/v1/runs", headers={"X-API-Key": old_plaintext})
    assert resp.status_code == 200

    # Rotate
    rotated = client.post(f"/api/v1/projects/{proj['id']}/api-keys/{created['id']}/rotate", json={}).json()
    new_plaintext = rotated["key"]
    assert new_plaintext != old_plaintext

    # Listing shows only prefixes — never raw keys or full hashes
    keys_list = client.get(f"/api/v1/projects/{proj['id']}/api-keys").json()
    for k in keys_list:
        assert k.get("key") is None
        assert k["key_prefix"] not in ("", None)
        listing = json_dumps_safe(keys_list)
        assert old_plaintext not in listing
        assert new_plaintext not in listing

    # New key works
    resp = client.get("/api/v1/runs", headers={"X-API-Key": new_plaintext})
    assert resp.status_code == 200

    # Old key is now disabled → 401 in production semantics (dev fallback may mask;
    # use an endpoint that requires explicit auth by sending an invalid+valid pair)
    from app.core.config import get_settings

    get_settings.cache_clear()
    import os

    prev = os.environ.get("APP_ENV")
    os.environ["APP_ENV"] = "production"
    get_settings.cache_clear()
    try:
        resp_old = client.get("/api/v1/runs", headers={"X-API-Key": old_plaintext})
        assert resp_old.status_code == 401
    finally:
        if prev is None:
            os.environ.pop("APP_ENV", None)
        else:
            os.environ["APP_ENV"] = prev
        get_settings.cache_clear()


def json_dumps_safe(obj) -> str:
    import json

    return json.dumps(obj)


def test_created_key_with_expiry_via_api(client):
    """API-created keys honor expires_in_days."""
    proj = client.post("/api/v1/projects", json={"name": "exp-project"}).json()
    created = client.post(
        f"/api/v1/projects/{proj['id']}/api-keys",
        json={"name": "short-lived", "expires_in_days": 7},
    ).json()
    assert created["expires_at"] is not None

    plaintext = created["key"]
    resp = client.get("/api/v1/runs", headers={"X-API-Key": plaintext})
    assert resp.status_code == 200
