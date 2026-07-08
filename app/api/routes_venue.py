"""Venue information API routes."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Query

from app.models.schemas import GateDetailSchema, VenueInfoResponseSchema
from app.services.flow_engine.congestion import get_gate_congestion
from app.services.venue_data import load_gates, load_stadium_info

if TYPE_CHECKING:
    from typing import Any

router = APIRouter()


@router.get(
    "/venue",
    response_model=VenueInfoResponseSchema,
    summary="Get venue information",
    description="Loads and returns stadium metadata, capacity, and active zones.",
)
def get_venue_info() -> dict[str, Any]:
    """Returns general stadium layout details.

    Returns:
        Stadium metadata mapping.

    """
    return load_stadium_info()


@router.get(
    "/venue/gates",
    response_model=list[GateDetailSchema],
    summary="Get venue gates",
    description="Lists all stadium gates, their accessibility features, and simulated congestion.",
)
def get_venue_gates(
    minutes_to_kickoff: Annotated[
        int,
        Query(
            ge=-180,
            le=600,
            description="Time until kickoff to calculate simulated gate congestion.",
        ),
    ] = 45,
) -> list[dict[str, Any]]:
    """Calculates congestion and returns gates list with accessibility options.

    Args:
        minutes_to_kickoff: Minutes to match kickoff.

    Returns:
        List of gate details dictionaries.

    """
    gates = load_gates()
    results = []
    for gate in gates:
        congestion = get_gate_congestion(
            gate_id=gate.id,
            minutes_to_kickoff=minutes_to_kickoff,
        )
        results.append(
            {
                "id": gate.id,
                "name": gate.name,
                "step_free": gate.step_free,
                "sensory_friendly": gate.sensory_friendly,
                "audio_cues": gate.audio_cues,
                "congestion": congestion,
            }
        )
    return results
