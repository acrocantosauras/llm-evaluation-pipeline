"""Authentication routes - project and API key management."""

import logging
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.security import generate_api_key, hash_api_key, key_prefix
from app.db.models import ApiKey, Project
from app.db.session import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["auth"])


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=1000)


class ProjectResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    created_at: datetime


class ApiKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    expires_in_days: int | None = Field(
        default=None,
        ge=1,
        le=3650,
        description="Optional key lifetime in days. Omit for a non-expiring key.",
    )


class ApiKeyResponse(BaseModel):
    id: uuid.UUID
    name: str
    key: str | None = None  # Only returned on creation
    key_prefix: str
    enabled: bool
    created_at: datetime
    expires_at: datetime | None = None


@router.post("/projects", response_model=ProjectResponse, status_code=201)
def create_project(request: ProjectCreate, db: Session = Depends(get_db)) -> ProjectResponse:
    """Create a new project."""
    project = Project(
        id=uuid.uuid4(),
        created_at=datetime.now(timezone.utc),
        name=request.name,
        description=request.description,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return ProjectResponse(
        id=project.id, name=project.name, description=project.description, created_at=project.created_at
    )


@router.get("/projects", response_model=list[ProjectResponse])
def list_projects(db: Session = Depends(get_db)) -> list[ProjectResponse]:
    """List all projects."""
    projects = db.query(Project).order_by(Project.created_at.desc()).all()
    return [ProjectResponse(id=p.id, name=p.name, description=p.description, created_at=p.created_at) for p in projects]


@router.get("/projects/{project_id}", response_model=ProjectResponse)
def get_project(project_id: uuid.UUID, db: Session = Depends(get_db)) -> ProjectResponse:
    """Get a specific project."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectResponse(
        id=project.id, name=project.name, description=project.description, created_at=project.created_at
    )


def _create_key_record(
    db: Session, project_id: uuid.UUID, name: str, expires_in_days: int | None
) -> tuple[ApiKey, str]:
    """Create an ApiKey row; return (api_key, plaintext). Plaintext is never persisted or logged."""
    plaintext_key = generate_api_key()
    expires_at = None
    if expires_in_days is not None:
        expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)

    api_key = ApiKey(
        id=uuid.uuid4(),
        created_at=datetime.now(timezone.utc),
        project_id=project_id,
        name=name,
        key_hash=hash_api_key(plaintext_key),
        key_prefix=key_prefix(plaintext_key),
        enabled=True,
        expires_at=expires_at,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    return api_key, plaintext_key


@router.post("/projects/{project_id}/api-keys", response_model=ApiKeyResponse, status_code=201)
def create_api_key(project_id: uuid.UUID, request: ApiKeyCreate, db: Session = Depends(get_db)) -> ApiKeyResponse:
    """Create a new API key. The full key is returned ONLY on creation."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    api_key, plaintext_key = _create_key_record(db, project_id, request.name, request.expires_in_days)

    return ApiKeyResponse(
        id=api_key.id,
        name=api_key.name,
        key=plaintext_key,
        key_prefix=api_key.key_prefix,
        enabled=api_key.enabled,
        created_at=api_key.created_at,
        expires_at=api_key.expires_at,
    )


@router.get("/projects/{project_id}/api-keys", response_model=list[ApiKeyResponse])
def list_api_keys(project_id: uuid.UUID, db: Session = Depends(get_db)) -> list[ApiKeyResponse]:
    """List API keys for a project (keys shown as prefixes only)."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    keys = db.query(ApiKey).filter(ApiKey.project_id == project_id).order_by(ApiKey.created_at.desc()).all()
    return [
        ApiKeyResponse(
            id=k.id,
            name=k.name,
            key=None,
            key_prefix=k.key_prefix or k.key_hash[:10] + "...",
            enabled=k.enabled,
            created_at=k.created_at,
            expires_at=k.expires_at,
        )
        for k in keys
    ]


@router.post("/projects/{project_id}/api-keys/{key_id}/rotate", response_model=ApiKeyResponse, status_code=201)
def rotate_api_key(project_id: uuid.UUID, key_id: uuid.UUID, db: Session = Depends(get_db)) -> ApiKeyResponse:
    """Rotate an API key: creates a replacement and disables the old key.

    The new plaintext key is returned ONLY on this call. The old key stops
    working immediately (revocation), enabling zero-downtime rotation by
    creating the replacement first if desired via POST + DELETE instead.
    """
    api_key = db.query(ApiKey).filter(ApiKey.id == key_id, ApiKey.project_id == project_id).first()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    # Inherit expiry policy of the rotated key (None stays non-expiring).
    expires_in_days = None
    if api_key.expires_at is not None:
        remaining = (api_key.expires_at - datetime.now(timezone.utc)).days + 1
        expires_in_days = max(1, remaining)

    new_key, plaintext_key = _create_key_record(db, project_id, api_key.name, expires_in_days)

    # Disable the old key after successful replacement
    api_key.enabled = False
    db.commit()

    return ApiKeyResponse(
        id=new_key.id,
        name=new_key.name,
        key=plaintext_key,
        key_prefix=new_key.key_prefix,
        enabled=new_key.enabled,
        created_at=new_key.created_at,
        expires_at=new_key.expires_at,
    )


@router.delete("/projects/{project_id}/api-keys/{key_id}", status_code=204)
def revoke_api_key(project_id: uuid.UUID, key_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    """Revoke (disable) an API key."""
    api_key = db.query(ApiKey).filter(ApiKey.id == key_id, ApiKey.project_id == project_id).first()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    api_key.enabled = False
    db.commit()
