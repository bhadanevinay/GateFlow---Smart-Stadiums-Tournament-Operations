"""Egress routing service.

Calculates safe, accessible exit routes for fans leaving the stadium after the match,
guiding them from their seat section to their selected onward transport station.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Final

from app.exceptions import RouteNotFoundError, UnknownZoneError
from app.models.domain import GateInfo, RoutePlan
from app.models.enums import AccessibilityNeed, CongestionLevel
from app.services.flow_engine.routing import calculate_route, merge_route_plans

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from app.models.schemas import FanContextSchema

CONGESTION_EGRESS_PENALTY: Final[float] = 500.0


def _score_egress_gate(
    gate: GateInfo,
    start_node: str,
    dest_node: str,
    graph: Mapping[str, list[str] | list[dict[str, str | float | bool]]],
    context: FanContextSchema,
    congestion_by_gate: Mapping[str, CongestionLevel],
) -> tuple[float, RoutePlan, RoutePlan] | None:
    """Helper to route and score a single exit gate candidate."""
    try:
        route_section_to_gate = calculate_route(
            start_node=start_node,
            end_node=gate.id,
            graph=graph,
            accessibility_needs=context.accessibility_needs,
        )
        route_gate_to_dest = calculate_route(
            start_node=gate.id,
            end_node=dest_node,
            graph=graph,
            accessibility_needs=context.accessibility_needs,
        )
    except (RouteNotFoundError, KeyError):
        return None

    total_time = (
        route_section_to_gate.estimated_minutes + route_gate_to_dest.estimated_minutes
    )
    congestion_lvl = congestion_by_gate.get(gate.id, CongestionLevel.LOW)

    score = total_time
    # Apply exponential penalty for congested exit gates to avoid crowd bottlenecks
    if congestion_lvl == CongestionLevel.CRITICAL:
        score += CONGESTION_EGRESS_PENALTY * 2
    elif congestion_lvl == CongestionLevel.HIGH:
        score += CONGESTION_EGRESS_PENALTY

    return score, route_section_to_gate, route_gate_to_dest


def calculate_egress_route(
    context: FanContextSchema,
    gates: Sequence[GateInfo],
    congestion_by_gate: Mapping[str, CongestionLevel],
    graph: Mapping[str, list[str] | list[dict[str, str | float | bool]]],
    transport_nodes: Mapping[str, Mapping[str, Any]],
) -> tuple[GateInfo, RoutePlan, str]:
    """Calculates the best exit route from stadium section to transport terminal.

    Inverts the arrival flow: route goes from section to gate (exit), and then
    from gate to transport node. Biases exit gate selection to minimize total walking
    distance and avoid bottleneck gates.

    Time Complexity: O(G * (V log V + E)) where G is the number of gates.
    Space Complexity: O(V) for routing data.

    Args:
        context: The fan context request schema.
        gates: Available venue gates.
        congestion_by_gate: Current gate congestion levels.
        graph: Stadium concourse routing graph.
        transport_nodes: Onward transport node configurations.

    Returns:
        A tuple of (selected exit GateInfo, merged exit RoutePlan, reasoning string).

    Raises:
        UnknownZoneError: If the onward transport node configuration is missing.
        RouteNotFoundError: If no accessible egress route can be determined.

    """
    mode_str = context.arrival_mode.value
    if mode_str not in transport_nodes:
        raise UnknownZoneError(
            f"Onward transport mode '{mode_str}' node details missing."
        )

    dest_node = str(transport_nodes[mode_str]["arrival_node"])
    start_node = f"section_{context.ticket_section}"

    # Filter exit gates based on accessibility constraints
    is_mobility = AccessibilityNeed.MOBILITY in context.accessibility_needs
    candidates = [g for g in gates if not is_mobility or g.step_free]

    if not candidates:
        raise RouteNotFoundError("No accessible gates available for post-match egress.")

    scored_candidates: list[tuple[float, GateInfo, RoutePlan, RoutePlan]] = []

    for gate in candidates:
        res = _score_egress_gate(
            gate=gate,
            start_node=start_node,
            dest_node=dest_node,
            graph=graph,
            context=context,
            congestion_by_gate=congestion_by_gate,
        )
        if res is not None:
            score, r1, r2 = res
            scored_candidates.append((score, gate, r1, r2))

    if not scored_candidates:
        raise RouteNotFoundError(
            f"No egress route found from Section {context.ticket_section} "
            f"to transport station {dest_node}."
        )

    # Pick the exit gate with the lowest score
    scored_candidates.sort(key=lambda x: x[0])
    _, best_gate, r1, r2 = scored_candidates[0]

    merged_route = merge_route_plans(r1, r2)

    reasoning = (
        f"Selected exit {best_gate.name} as the safest, least congested egress route "
        f"connecting Section {context.ticket_section} to the {context.arrival_mode.value}."
    )

    return best_gate, merged_route, reasoning
