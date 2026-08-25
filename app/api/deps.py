"""FastAPI dependencies for authentication, authorization, and request handling."""

import logging
import time
import uuid
from collections import defaultdict
from contextvars import ContextVar

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.session import get_db

# Request correlation context
request_id_var: ContextVar[str] = ContextVar("request_id", default="")

logger = logging.getLogger(__name__)

# ── Rate Limiting ──────────────────────────────────────────────────────────────

_rate_limits: dict[str, list[float]] = defaultdict(list)
_rate_limit_config: dict[str, tuple[int, float]] = {}  # name -> (max_requests, window_seconds)


def configure_rate_limit(name: str, max_requests: int, window_seconds: float = 60.0) -> None:
    _rate_limit_config[name] = (max_requests, window_seconds)


def _check_rate_limit(key: str, max_requests: int, window_seconds: float) -> bool:
    """Returns True if request is allowed."""
    now = time.time()
    cutoff = now - window_seconds
    _rate_limits[key] = [t for t in _rate_limits[key] if t > cutoff]
    if len(_rate_limits[key]) >= max_requests:
        return False
    _rate_limits[key].append(now)
    return True


# ── Request ID ─────────────────────────────────────────────────────────────────


async def request_id_middleware(request: Request) -> None:
    """Assign a correlation ID to each request."""
    rid = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request_id_var.set(rid)
    request.state.request_id = rid


# ── Authentication ─────────────────────────────────────────────────────────────


def _get_project_from_key(key_hash: str, db: Session):
    """Look up project from API key hash."""
    from app.db.models import ApiKey, Project

    api_key = db.query(ApiKey).filter(ApiKey.key_hash == key_hash, ApiKey.enabled.is_(True)).first()
    if not api_key:
        return None
    project = db.query(Project).filter(Project.id == api_key.project_id).first()
    return project, api_key


async def get_current_project(request: Request, db: Session = Depends(get_db)):
    """Dependency that extracts project from API key.

    In production (APP_ENV=production), authentication is always required.
    In development (APP_ENV=development), unauthenticated requests fall back to the first project.
    In CI (APP_ENV=ci), authentication is always required.
    """
    from app.core.config import get_settings
    from app.core.security import hash_api_key

    settings = get_settings()
    is_production = settings.APP_ENV in ("production", "ci")

    auth = request.headers.get("Authorization", "")
    api_key_header = request.headers.get("X-API-Key", "")

    # Try X-API-Key header first
    if api_key_header:
        key_hash = hash_api_key(api_key_header)
        result = _get_project_from_key(key_hash, db)
        if result:
            project, api_key_obj = result
            request.state.project_id = str(project.id)
            request.state.api_key_id = str(api_key_obj.id)
            return project

    # Try Bearer token
    if auth.startswith("Bearer "):
        token = auth[7:]
        key_hash = hash_api_key(token)
        result = _get_project_from_key(key_hash, db)
        if result:
            project, api_key_obj = result
            request.state.project_id = str(project.id)
            request.state.api_key_id = str(api_key_obj.id)
            return project

    # Production/CI: never allow unauthenticated access
    if is_production:
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid API key. Provide via X-API-Key header or Authorization: Bearer <key>",
        )

    # Development/testing: allow unauthenticated access with a default project
    if not api_key_header and not auth:
        from app.db.models import Project

        project = db.query(Project).first()
        if project:
            request.state.project_id = str(project.id)
            return project

    raise HTTPException(
        status_code=401,
        detail="Missing or invalid API key. Provide via X-API-Key header or Authorization: Bearer <key>",
    )


async def optional_auth(request: Request, db: Session = Depends(get_db)):
    """Dependency that optionally extracts project from API key.

    In production/CI, always requires valid auth.
    In development/testing, falls back to first project if no key provided.
    """
    try:
        return await get_current_project(request, db)
    except HTTPException:
        from app.core.config import get_settings

        settings = get_settings()
        if settings.APP_ENV in ("production", "ci"):
            raise  # Re-raise in production/CI

        from app.db.models import Project

        project = db.query(Project).first()
        if project:
            request.state.project_id = str(project.id)
        return None


# ── Rate Limiting Dependency ───────────────────────────────────────────────────


async def rate_limit_api(request: Request) -> None:
    """Rate limit API endpoints."""
    from app.core.config import get_settings

    settings = get_settings()

    max_requests = getattr(settings, "RATE_LIMIT_REQUESTS", 100)
    window = getattr(settings, "RATE_LIMIT_WINDOW", 60.0)

    key = request.state.project_id if hasattr(request.state, "project_id") else request.client.host
    if not _check_rate_limit(f"api:{key}", max_requests, window):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again later.")
