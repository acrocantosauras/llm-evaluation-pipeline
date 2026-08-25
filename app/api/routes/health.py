from fastapi import APIRouter, Depends, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict:
    """Application health check. Does not verify database connectivity."""
    return {"status": "healthy"}


@router.get("/ready")
def readiness_check(db: Session = Depends(get_db)) -> dict:
    """Readiness check — verifies database connectivity."""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ready", "database": "connected"}
    except Exception:
        return {"status": "not ready", "database": "disconnected"}


@router.get("/metrics")
def prometheus_metrics() -> Response:
    """Prometheus metrics endpoint."""
    from app.observability.metrics import get_metrics_response

    body, content_type = get_metrics_response()
    return Response(content=body, media_type=content_type)
