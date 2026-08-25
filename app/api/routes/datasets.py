from fastapi import APIRouter, Depends

from app.api.deps import get_current_project, rate_limit_api
from app.db.models import Project

router = APIRouter(prefix="/api/v1", tags=["datasets"], dependencies=[Depends(rate_limit_api)])


@router.get("/datasets", status_code=501)
def list_datasets(project: Project = Depends(get_current_project)) -> dict:
    """Dataset management — not yet implemented. Requires authentication."""
    return {"detail": "Dataset management is planned for a future phase."}
