"""Health and readiness check API routes."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.models.schemas import HealthResponseSchema, HealthzResponseSchema

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponseSchema,
    summary="Liveness check",
    description="Returns simple service status confirmation.",
)
def get_health() -> dict[str, str]:
    """Returns liveness check status.

    Returns:
        Dictionary containing status.

    """
    return {"status": "ok"}


@router.get(
    "/healthz",
    response_model=HealthzResponseSchema,
    summary="Readiness check",
    description="Confirms service readiness and states LLM phrasing configuration status.",
)
def get_readiness(request: Request) -> dict[str, str]:
    """Returns readiness check status with LLM configuration mode.

    Args:
        request: FastAPI request to check app state for configured client.

    Returns:
        Dictionary containing status and llm key.

    """
    llm_client = getattr(request.app.state, "llm_client", None)
    llm_status = "live" if llm_client is not None else "offline"
    return {"status": "ok", "llm": llm_status}
