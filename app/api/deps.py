"""FastAPI dependencies for authentication, authorization, and request handling.

Design notes
------------
- Rate limiting is backed by Redis (shared across all API workers, atomic,
  bounded memory via TTLs). See ``_check_rate_limit``.
- All dependencies that perform blocking I/O (DB queries, Redis calls) are
  plain ``def`` functions so Starlette runs them in its bounded threadpool
  instead of blocking the event loop.
- Authentication fails closed in production/ci. The unauthenticated
  "development fallback" must be *explicitly* enabled via
  ``ALLOW_DEV_AUTH_FALLBACK=true`` and is never honored outside development.
"""

import logging
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.session import get_db

# Request correlation context
request_id_var: ContextVar[str] = ContextVar("request_id", default="")

logger = logging.getLogger(__name__)

# Throttle window for last_used_at writes (seconds) to avoid a DB write per request.
LAST_USED_UPDATE_INTERVAL = 60.0

# ── Rate Limiting ──────────────────────────────────────────────────────────────


def _check_rate_limit(key: str, max_requests: int, window_seconds: float) -> bool:
    """Atomic fixed-window rate limit backed by Redis.

    Shared across all API worker processes and survives individual worker
    restarts (state lives in Redis). Memory is bounded by the key TTL.

    Implementation (each operation is atomic; no Lua required):
    - First request in a window wins a ``SET key 1 EX <window> NX``, which
      atomically creates the counter with an expiry.
    - Subsequent requests ``INCR`` the counter.
    - A TTL guard re-arms the expiry if it was lost (e.g. after exotic
      persistence failures), preventing immortal keys.

    Returns True if the request is allowed.

    Raises redis.ConnectionError / TimeoutError to let the caller decide the
    fail-open vs fail-closed policy (see ``rate_limit_api``).
    """
    from app.services import redis_queue

    r = redis_queue.get_redis_client()
    redis_key = f"ratelimit:{key}"
    window = max(1, int(window_seconds))

    newly_set = r.set(redis_key, 1, ex=window, nx=True)
    if newly_set:
        return max_requests >= 1

    count = r.incr(redis_key)

    # Guard against a counter without a TTL (would otherwise never reset).
    ttl = r.ttl(redis_key)
    if ttl is not None and ttl < 0:
        r.expire(redis_key, window)

    return count <= max_requests


# ── Request ID ─────────────────────────────────────────────────────────────────


async def request_id_middleware(request: Request) -> None:
    """Assign a correlation ID to each request."""
    rid = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request_id_var.set(rid)
    request.state.request_id = rid


# ── Authentication ─────────────────────────────────────────────────────────────


def _get_project_from_key(key_hash: str, db: Session):
    """Look up project from API key hash.

    Rejects disabled or expired keys. Updates ``last_used_at`` at most once
    per LAST_USED_UPDATE_INTERVAL per key to bound write amplification.
    """
    from app.db.models import ApiKey, Project

    now = datetime.now(timezone.utc)
    api_key = (
        db.query(ApiKey)
        .filter(
            ApiKey.key_hash == key_hash,
            ApiKey.enabled.is_(True),
            # Fail closed on expired keys
            (ApiKey.expires_at.is_(None)) | (ApiKey.expires_at > now),
        )
        .first()
    )
    if not api_key:
        return None

    # Throttled last-used bookkeeping
    last_used = api_key.last_used_at
    if last_used is not None and last_used.tzinfo is None:
        # SQLite returns naive datetimes; interpret as UTC
        last_used = last_used.replace(tzinfo=timezone.utc)
    stale = last_used is None or (now - last_used).total_seconds() >= LAST_USED_UPDATE_INTERVAL
    if stale:
        try:
            api_key.last_used_at = now
            db.commit()
        except Exception:
            logger.warning("Failed to update last_used_at for api key", exc_info=True)
            db.rollback()

    project = db.query(Project).filter(Project.id == api_key.project_id).first()
    return project, api_key


def _authenticate(request: Request, db: Session):
    """Resolve the project from X-API-Key or Bearer credentials, or raise 401."""
    from app.core.security import hash_api_key

    auth = request.headers.get("Authorization", "")
    api_key_header = request.headers.get("X-API-Key", "")

    candidates = []
    if api_key_header:
        candidates.append(api_key_header)
    if auth.startswith("Bearer "):
        candidates.append(auth[7:])

    for candidate in candidates:
        key_hash = hash_api_key(candidate)
        result = _get_project_from_key(key_hash, db)
        if result:
            project, api_key_obj = result
            request.state.project_id = str(project.id)
            request.state.api_key_id = str(api_key_obj.id)
            return project

    raise HTTPException(
        status_code=401,
        detail="Missing or invalid API key. Provide via X-API-Key header or Authorization: Bearer <key>",
    )


def get_current_project(request: Request, db: Session = Depends(get_db)):
    """Dependency that extracts project from API key.

    In production (APP_ENV=production) and ci, authentication always fails
    closed — there is no fallback under any configuration.
    In development, unauthenticated requests fall back to a default project
    ONLY when ALLOW_DEV_AUTH_FALLBACK is explicitly true.
    """
    from app.core.config import get_settings

    settings = get_settings()
    strict = settings.APP_ENV in ("production", "ci")

    # Try API-key/Bearer authentication first
    auth_header = request.headers.get("Authorization", "")
    api_key_header = request.headers.get("X-API-Key", "")
    if api_key_header or auth_header.startswith("Bearer "):
        return _authenticate(request, db)

    if strict:
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid API key. Provide via X-API-Key header or Authorization: Bearer <key>",
        )

    # Development-only convenience fallback: must be explicitly enabled.
    if settings.ALLOW_DEV_AUTH_FALLBACK:
        from app.db.models import Project

        project = db.query(Project).order_by(Project.created_at.asc()).first()
        if project:
            request.state.project_id = str(project.id)
            return project

    raise HTTPException(
        status_code=401,
        detail="Missing or invalid API key. Provide via X-API-Key header or Authorization: Bearer <key>",
    )


def optional_auth(request: Request, db: Session = Depends(get_db)):
    """Dependency that optionally extracts project from API key.

    In production/CI, always requires valid auth (fails closed).
    In development, returns None when no valid key is provided and the
    explicit dev fallback is disabled; falls back to a default project only
    when ALLOW_DEV_AUTH_FALLBACK is explicitly enabled.
    """
    try:
        return get_current_project(request, db)
    except HTTPException:
        from app.core.config import get_settings

        settings = get_settings()
        if settings.APP_ENV in ("production", "ci"):
            raise  # Always re-raise in production/CI

        if settings.ALLOW_DEV_AUTH_FALLBACK:
            from app.db.models import Project

            project = db.query(Project).order_by(Project.created_at.asc()).first()
            if project:
                request.state.project_id = str(project.id)
        return None


# ── Rate Limiting Dependency ───────────────────────────────────────────────────


def rate_limit_api(
    request: Request,
    project=Depends(get_current_project),  # noqa: ARG001 — orders limiter AFTER auth
) -> None:
    """Rate limit API endpoints (Redis-backed, shared across workers).

    Deliberately a sync ``def`` dependency: the Redis round-trips happen in
    Starlette's bounded threadpool, never on the event loop.

    Declares a dependency on ``get_current_project`` so the limiter runs
    after authentication and can key the bucket per project (FastAPI caches
    dependency results, so auth still executes exactly once per request).
    Unauthenticated callers are rejected by auth before reaching the limiter;
    the IP fallback below only covers hypothetical unkeyed routes.

    Fail behavior is explicit configuration (RATE_LIMIT_FAIL_CLOSED):
    - False (default): fail OPEN — allow the request but log a warning and
      emit a metric. Documented availability-over-strictness tradeoff.
    - True: fail CLOSED — return 503 when the limiter cannot be reached.
    """
    import redis as redis_lib

    from app.core.config import get_settings
    from app.observability import metrics

    settings = get_settings()

    max_requests = getattr(settings, "RATE_LIMIT_REQUESTS", 100)
    window = getattr(settings, "RATE_LIMIT_WINDOW", 60.0)

    # get_current_project has run (dependency above); it sets this.
    key = getattr(request.state, "project_id", None)
    if not key:
        client_host = request.client.host if request.client else "anonymous"
        key = f"ip:{client_host}"

    try:
        allowed = _check_rate_limit(f"api:{key}", max_requests, window)
    except (
        redis_lib.ConnectionError,
        redis_lib.TimeoutError,
        ConnectionError,
        TimeoutError,
    ) as exc:
        metrics.inc_rate_limit_failures()
        if settings.RATE_LIMIT_FAIL_CLOSED:
            logger.error("Rate limiter unreachable and fail-closed enabled: %s", exc)
            raise HTTPException(status_code=503, detail="Rate limiter unavailable") from exc
        logger.warning("Rate limiter unreachable, failing open: %s", exc)
        return

    if not allowed:
        metrics.inc_rate_limited()
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again later.")
