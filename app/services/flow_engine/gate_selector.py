"""Gate selection service.

Recommends the best entry gate based on accessibility, congestion levels, walking distance,
and time-to-kickoff.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from app.exceptions import RouteNotFoundError
from app.models.domain import GateInfo, RoutePlan
from app.models.enums import AccessibilityNeed, CongestionLevel, UrgencyTier
from app.services.flow_engine.routing import calculate_route, merge_route_plans

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from app.models.schemas import FanContextSchema


# Scoring and timing constants
URGENT_WINDOW_MINUTES: Final[int] = 20
CRITICAL_WINDOW_MINUTES: Final[int] = 5

# Congestion levels maps to numerical weights
CONGESTION_VALUES: Final[Mapping[CongestionLevel, float]] = {
    CongestionLevel.LOW: 1.0,
    CongestionLevel.MEDIUM: 2.0,
    CongestionLevel.HIGH: 3.0,
    CongestionLevel.CRITICAL: 4.0,
}

# Rerouting penalty for high/critical congestion
CONGESTION_REROUTE_PENALTY: Final[float] = 1000.0


def _score_gate_candidate(
    gate: GateInfo,
    context: FanContextSchema,
    section_node: str,
    graph: Mapping[str, list[str] | list[dict[str, str | float | bool]]],
    urgency: UrgencyTier,
    congestion_by_gate: Mapping[str, CongestionLevel],
    *,
    has_low_congestion_alt: bool,
) -> tuple[float, RoutePlan, RoutePlan] | None:
    """Helper to route and score a single entry gate candidate."""
    try:
        route_arrival_to_gate = calculate_route(
            start_node=context.current_location,
            end_node=gate.id,
            graph=graph,
            accessibility_needs=context.accessibility_needs,
        )
        route_gate_to_section = calculate_route(
            start_node=gate.id,
            end_node=section_node,
            graph=graph,
            accessibility_needs=context.accessibility_needs,
        )
    except (RouteNotFoundError, KeyError):
        return None

    total_time = (
        route_arrival_to_gate.estimated_minutes
        + route_gate_to_section.estimated_minutes
    )
    congestion_lvl = congestion_by_gate.get(gate.id, CongestionLevel.LOW)
    congestion_num = CONGESTION_VALUES[congestion_lvl]

    if urgency in (UrgencyTier.HURRY, UrgencyTier.CRITICAL):
        # Under time pressure: weight congestion 1.5x to prioritize faster gates
        score = total_time + (congestion_num * 1.5)
    else:
        # Normal mode: standard congestion weighting
        score = total_time + (congestion_num * 8.0)

    if (
        congestion_lvl in (CongestionLevel.HIGH, CongestionLevel.CRITICAL)
        and has_low_congestion_alt
    ):
        score += CONGESTION_REROUTE_PENALTY

    return score, route_arrival_to_gate, route_gate_to_section


def _get_urgency_tier(minutes_to_kickoff: int) -> UrgencyTier:
    """Helper to compute urgency tier based on kickoff countdown."""
    if minutes_to_kickoff <= CRITICAL_WINDOW_MINUTES:
        return UrgencyTier.CRITICAL
    if minutes_to_kickoff <= URGENT_WINDOW_MINUTES:
        return UrgencyTier.HURRY
    return UrgencyTier.NORMAL


def select_best_gate(
    context: FanContextSchema,
    gates: Sequence[GateInfo],
    congestion_by_gate: Mapping[str, CongestionLevel],
    graph: Mapping[str, list[str] | list[dict[str, str | float | bool]]],
) -> tuple[GateInfo, RoutePlan, UrgencyTier, str]:
    """Selects the optimal gate for a fan given their context and current congestion.

    Filters gates by accessibility constraints (step-free for mobility needs).
    Computes routes for both segments: arrival node to gate, and gate to ticket section.
    Scores each candidate using distance and congestion, biasing towards speed when close
    to kickoff and avoiding congested gates (high/critical) when alternative gates
    have lower occupancy.

    Time Complexity: O(G * (V log V + E)) where G is the number of gates.
    Space Complexity: O(V) for Dijkstra path reconstruction.

    Args:
        context: The Pydantic fan context request schema.
        gates: The list of gates in the stadium.
        congestion_by_gate: Map of gate IDs to CongestionLevel.
        graph: The concourse routing graph.

    Returns:
        A tuple of (chosen GateInfo, merged RoutePlan, UrgencyTier, reasoning string).

    Raises:
        RouteNotFoundError: If no gates are accessible or no route can be calculated.

    """
    urgency = _get_urgency_tier(context.minutes_to_kickoff)
    section_node = f"section_{context.ticket_section}"

    # Filter candidates based on accessibility needs
    is_mobility = AccessibilityNeed.MOBILITY in context.accessibility_needs
    candidates = [g for g in gates if not is_mobility or g.step_free]

    if not candidates:
        raise RouteNotFoundError(
            "No step-free gates found matching accessibility requirements."
        )

    # Evaluate each candidate
    scored_candidates: list[tuple[float, GateInfo, RoutePlan, RoutePlan]] = []

    # Check if there is at least one gate with low/medium congestion
    has_low_congestion_alt = any(
        congestion_by_gate.get(g.id, CongestionLevel.LOW)
        in (CongestionLevel.LOW, CongestionLevel.MEDIUM)
        for g in candidates
    )

    for gate in candidates:
        res = _score_gate_candidate(
            gate=gate,
            context=context,
            section_node=section_node,
            graph=graph,
            urgency=urgency,
            congestion_by_gate=congestion_by_gate,
            has_low_congestion_alt=has_low_congestion_alt,
        )
        if res is not None:
            score, r1, r2 = res
            scored_candidates.append((score, gate, r1, r2))

    if not scored_candidates:
        raise RouteNotFoundError(
            f"No path found to section {context.ticket_section} from {context.current_location}."
        )

    # Sort by score ascending
    scored_candidates.sort(key=lambda x: x[0])
    _, best_gate, r1, r2 = scored_candidates[0]

    merged_route = merge_route_plans(r1, r2)

    # Formulate reasoning summary for decision record
    desc_str = (
        "fastest" if urgency != UrgencyTier.NORMAL else "least congested accessible"
    )
    reasoning = (
        f"Selected {best_gate.name} because it is the {desc_str} "
        f"route to Section {context.ticket_section} under {urgency.value} urgency."
    )

    return best_gate, merged_route, urgency, reasoning
