"""Transportation routing advice API routes."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Query

from app.models.enums import AccessibilityNeed
from app.models.schemas import TransportAdviceResponseSchema
from app.services.flow_engine.transport_advisor import recommend_transport
from app.services.venue_data import load_transport_nodes

router = APIRouter()


@router.get(
    "/transport/advice",
    response_model=TransportAdviceResponseSchema,
    summary="Get transportation advice",
    description=(
        "Scores and ranks transportation modes (metro, parking, rideshare, shuttle) "
        "by total estimated travel times, terminal wait times, and accessibility."
    ),
)
def get_transport_advice(
    minutes_to_kickoff: Annotated[
        int,
        Query(
            ge=-180,
            le=600,
            description="Time until kickoff to calculate simulated arrival congestion.",
        ),
    ] = 45,
    accessibility_needs: Annotated[
        list[AccessibilityNeed] | None,
        Query(
            description="Declared accessibility requirements.",
        ),
    ] = None,
) -> dict[str, Any]:
    """Calculates transport rankings based on live conditions and accessibility needs.

    Args:
        minutes_to_kickoff: Minutes to match kickoff.
        accessibility_needs: Declared accessibility requirements.

    Returns:
        Ranked transport options wrapped in response schema.

    """
    needs = accessibility_needs or []
    nodes = load_transport_nodes()
    options = recommend_transport(
        accessibility_needs=needs,
        minutes_to_kickoff=minutes_to_kickoff,
        transport_nodes=nodes,
    )
    return {"options": options}
