from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    """Liveness check. No dependencies touched — if this fails, the process is dead."""
    return {"status": "ok"}
