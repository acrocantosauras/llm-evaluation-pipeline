from fastapi import APIRouter

from evaluator.profiles import list_profiles

router = APIRouter(prefix="/api/v1", tags=["profiles"])


@router.get("/profiles")
def get_profiles() -> dict:
    """List available evaluation profiles."""
    return {"profiles": list_profiles()}
