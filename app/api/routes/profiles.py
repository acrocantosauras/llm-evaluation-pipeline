from fastapi import APIRouter, Depends

from app.api.deps import get_current_project, rate_limit_api
from app.db.models import Project
from evaluator.profiles import list_profiles

router = APIRouter(prefix="/api/v1", tags=["profiles"], dependencies=[Depends(rate_limit_api)])


@router.get("/profiles")
def get_profiles(project: Project = Depends(get_current_project)) -> dict:
    """List available evaluation profiles. Requires authentication."""
    return {"profiles": list_profiles()}
