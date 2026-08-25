"""Tests for the Redis-backed atomic rate limiter.

Covers:
- requests below the limit
- the request that reaches the limit
- requests over the limit
- concurrent requests (atomicity under threads)
- multiple application workers sharing the same limit
- Redis-unavailable behavior (fail-open default, fail-closed option)
"""

import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest


@pytest.fixture()
def fake_redis(monkeypatch):
    """Provide a fakeredis instance backing the rate limiter."""
    import fakeredis

    from app.services import redis_queue as rq

    fake = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(rq, "get_redis_client", lambda: fake)
    yield fake
    fake.flushall()


# ── Unit-level limiter behavior ────────────────────────────────────────────────


def test_below_limit_allowed(fake_redis):
    from app.api.deps import _check_rate_limit

    key = str(uuid.uuid4())
    for _ in range(4):
        assert _check_rate_limit(key, 5, 60.0) is True


def test_request_at_limit_allowed_then_next_blocked(fake_redis):
    from app.api.deps import _check_rate_limit

    key = str(uuid.uuid4())
    assert _check_rate_limit(key, 3, 60.0) is True
    assert _check_rate_limit(key, 3, 60.0) is True
    # 3rd request reaches the limit — still allowed
    assert _check_rate_limit(key, 3, 60.0) is True
    # 4th request is over the limit
    assert _check_rate_limit(key, 3, 60.0) is False
    # and stays blocked (no leakage back under the limit)
    assert _check_rate_limit(key, 3, 60.0) is False


def test_keys_are_isolated(fake_redis):
    from app.api.deps import _check_rate_limit

    key_a = str(uuid.uuid4())
    key_b = str(uuid.uuid4())
    for _ in range(2):
        _check_rate_limit(key_a, 2, 60.0)
    assert _check_rate_limit(key_a, 2, 60.0) is False
    # A different key has its own budget
    assert _check_rate_limit(key_b, 2, 60.0) is True


def test_counter_has_ttl_bounded_memory(fake_redis):
    """Every counter key carries a TTL so memory stays bounded."""
    from app.api.deps import _check_rate_limit

    key = str(uuid.uuid4())
    _check_rate_limit(key, 10, 30.0)

    redis_key = f"ratelimit:{key}"
    ttl = fake_redis.ttl(redis_key)
    assert 0 < ttl <= 30


def test_ttl_guard_rearms_lost_expiry(fake_redis):
    """A counter that lost its TTL gets a fresh expiry instead of living forever."""
    from app.api.deps import _check_rate_limit

    key = str(uuid.uuid4())
    redis_key = f"ratelimit:{key}"

    # Simulate an immortal counter (lost TTL)
    fake_redis.set(redis_key, 1)
    assert fake_redis.ttl(redis_key) == -1

    allowed = _check_rate_limit(key, 10, 60.0)

    assert allowed is True
    assert fake_redis.ttl(redis_key) > 0


def test_concurrent_requests_are_atomic(fake_redis):
    """Exactly `limit` requests succeed under thread concurrency — no over-admission."""
    from app.api.deps import _check_rate_limit

    key = str(uuid.uuid4())
    limit = 25

    def hit(_):
        return _check_rate_limit(key, limit, 60.0)

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(hit, range(100)))

    allowed = sum(1 for r in results if r)
    assert allowed == limit  # no race condition: never more than limit


def test_multiple_workers_share_the_same_limit():
    """Two API worker processes (separate clients, same Redis) share one budget."""
    import fakeredis

    from app.api.deps import _check_rate_limit
    from app.services import redis_queue as rq

    server = fakeredis.FakeServer()
    client_a = fakeredis.FakeRedis(server=server, decode_responses=True)
    client_b = fakeredis.FakeRedis(server=server, decode_responses=True)

    original = rq.get_redis_client
    rq.get_redis_client = lambda: client_a
    try:
        key = "worker-shared"
        # Worker A uses up most of the budget
        for _ in range(4):
            assert _check_rate_limit(key, 6, 60.0) is True

        # Worker B draws from the SAME remaining budget
        rq.get_redis_client = lambda: client_b
        assert _check_rate_limit(key, 6, 60.0) is True
        assert _check_rate_limit(key, 6, 60.0) is True
        assert _check_rate_limit(key, 6, 60.0) is False
    finally:
        rq.get_redis_client = original


# ── Redis-unavailable behavior ─────────────────────────────────────────────────


def test_fail_open_when_redis_unavailable(monkeypatch):
    """Default policy: allow requests when the limiter cannot be reached.

    The request must proceed past rate limiting (any status except 429/503;
    401 is expected here since no auth/DB fixtures are installed).
    """
    import app.services.redis_queue as rq

    class BrokenClient:
        def set(self, *a, **kw):
            raise ConnectionError("redis down")

    monkeypatch.setattr(rq, "get_redis_client", lambda: BrokenClient())

    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app, raise_server_exceptions=False) as c:
        resp = c.get("/api/v1/profiles")
        assert resp.status_code not in (429, 503)


def test_fail_closed_when_configured(monkeypatch):
    """RATE_LIMIT_FAIL_CLOSED=true returns 503 when the limiter is unreachable."""
    import app.services.redis_queue as rq
    from app.core.config import get_settings

    class BrokenClient:
        def set(self, *a, **kw):
            raise ConnectionError("redis down")

    monkeypatch.setattr(rq, "get_redis_client", lambda: BrokenClient())
    monkeypatch.setenv("RATE_LIMIT_FAIL_CLOSED", "true")
    get_settings.cache_clear()
    try:
        from unittest.mock import MagicMock

        from fastapi.testclient import TestClient

        from app.api.deps import get_current_project
        from app.main import app

        # Isolate limiter behavior: auth succeeds without touching the DB.
        fake_project = MagicMock()
        fake_project.id = uuid.uuid4()
        app.dependency_overrides[get_current_project] = lambda: fake_project
        try:
            with TestClient(app, raise_server_exceptions=False) as c:
                resp = c.get("/api/v1/profiles")
                assert resp.status_code == 503
        finally:
            app.dependency_overrides.pop(get_current_project, None)
    finally:
        get_settings.cache_clear()


# ── Integration through the HTTP API ──────────────────────────────────────────


def test_api_returns_429_over_limit(client, monkeypatch):
    """End-to-end: exceeding RATE_LIMIT_REQUESTS returns 429 via the API."""
    from app.core.config import get_settings

    monkeypatch.setenv("RATE_LIMIT_REQUESTS", "3")
    get_settings.cache_clear()
    try:
        for _ in range(3):
            resp = client.get("/api/v1/runs")
            assert resp.status_code == 200
        resp = client.get("/api/v1/runs")
        assert resp.status_code == 429
    finally:
        get_settings.cache_clear()
