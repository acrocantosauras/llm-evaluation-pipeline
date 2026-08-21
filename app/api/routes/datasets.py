from fastapi import APIRouter

router = APIRouter(prefix="/api/v1", tags=["datasets"])


@router.get("/datasets", status_code=501)
def list_datasets() -> dict:
    """Dataset management — not yet implemented."""
    return {"detail": "Dataset management is planned for a future phase."}
