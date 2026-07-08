"""Copilot assistant API route."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any, Final

from fastapi import APIRouter, Request

from app.exceptions import UnknownZoneError
from app.models.enums import AccessibilityNeed, CongestionLevel, UrgencyTier
from app.models.schemas import (
    AssistResponseSchema,
    DecisionResultSchema,
    FanContextSchema,
)
from app.services.flow_engine.congestion import get_gate_congestion
from app.services.flow_engine.egress import calculate_egress_route
from app.services.flow_engine.gate_selector import select_best_gate
from app.services.phrasing.llm_phraser import phrase_with_llm
from app.services.phrasing.template_phraser import phrase_decision
from app.services.security import sanitize_question
from app.services.venue_data import (
    load_concourse_graph,
    load_gates,
    load_stadium_info,
    load_transport_nodes,
)

MINUTES_EGRESS_THRESHOLD: Final[int] = -105

if TYPE_CHECKING:
    from app.models.domain import GateInfo, RoutePlan

router = APIRouter()


def _get_accessibility_modes(needs: list[AccessibilityNeed]) -> list[str]:
    """Helper to resolve accessibility tags list."""
    modes: list[str] = []
    if AccessibilityNeed.MOBILITY in needs:
        modes.append("step_free")
    if AccessibilityNeed.VISUAL in needs:
        modes.append("audio_friendly")
    if AccessibilityNeed.HEARING in needs:
        modes.append("captioned")
    return modes


def _determine_route_and_gate(
    context: FanContextSchema,
    gates: Sequence[GateInfo],
    congestion_by_gate: Mapping[str, CongestionLevel],
    graph: Mapping[str, list[str] | list[dict[str, str | float | bool]]],
    transport_nodes: Mapping[str, Mapping[str, Any]],
    *,
    is_egress: bool,
) -> tuple[GateInfo, RoutePlan, UrgencyTier, str]:
    """Helper to determine the optimal route and gate based on egress status."""
    if is_egress:
        chosen_gate, route_plan, reasoning = calculate_egress_route(
            context=context,
            gates=gates,
            congestion_by_gate=congestion_by_gate,
            graph=graph,
            transport_nodes=transport_nodes,
        )
        urgency_tier = UrgencyTier.NORMAL
    else:
        chosen_gate, route_plan, urgency_tier, reasoning = select_best_gate(
            context=context,
            gates=gates,
            congestion_by_gate=congestion_by_gate,
            graph=graph,
        )
    return chosen_gate, route_plan, urgency_tier, reasoning


@router.post(
    "/assist",
    response_model=AssistResponseSchema,
    summary="Get interactive copilot guidance",
    description=(
        "Returns safe navigation routing from a user's location to their seat section "
        "(or section to transit terminal during post-match egress), phrased in the "
        "fan's preferred language with real-time congestion awareness."
    ),
)
async def post_assist(
    context: FanContextSchema,
    request: Request,
) -> dict[str, Any]:
    """Calculates route and returns natural language phrasing.

    Time Complexity: O(G * (V log V + E)) due to path calculations across gates.
    Space Complexity: O(V) for path representations.

    Args:
        context: The incoming fan context details.
        request: FastAPI request to access app state singletons.

    Returns:
        JSON response with natural language answer and decision metadata.

    """
    # 1. Validate section zone existence
    stadium_info = load_stadium_info()
    if context.ticket_section not in stadium_info["sections"]:
        raise UnknownZoneError(
            f"Ticket section '{context.ticket_section}' is not recognized for this venue."
        )

    # 2. Sanitization
    context.question = sanitize_question(context.question)

    # 3. Load required configurations
    gates = load_gates()
    graph = load_concourse_graph()
    transport_nodes = load_transport_nodes()

    # 4. Generate congestion mapping for all gates
    congestion_by_gate = {
        gate.id: get_gate_congestion(
            gate_id=gate.id,
            minutes_to_kickoff=context.minutes_to_kickoff,
        )
        for gate in gates
    }

    # 5. Core decision logic - distinguish between entry and post-match egress
    # Post-match egress begins when minutes_to_kickoff is less than -105 (match duration complete)
    is_egress = context.minutes_to_kickoff < MINUTES_EGRESS_THRESHOLD

    chosen_gate, route_plan, urgency_tier, reasoning = _determine_route_and_gate(
        context=context,
        gates=gates,
        congestion_by_gate=congestion_by_gate,
        graph=graph,
        transport_nodes=transport_nodes,
        is_egress=is_egress,
    )

    # 6. Resolve accessibility tags
    accessibility_mode = _get_accessibility_modes(context.accessibility_needs)

    # 7. Formulate offline template text (always calculated as the reliable baseline)
    fallback_text = phrase_decision(
        language=context.language,
        urgency_tier=urgency_tier,
        recommended_gate_id=chosen_gate.id,
        gates=gates,
        congestion_by_gate=congestion_by_gate,
        ticket_section=context.ticket_section,
        distance_meters=route_plan.distance_meters,
        estimated_minutes=route_plan.estimated_minutes,
        landmarks=route_plan.landmarks,
    )

    # 8. Phrase response using LLM if key is set and user asked a free-text question
    used_llm = False
    answer = fallback_text

    llm_client = getattr(request.app.state, "llm_client", None)
    # Only call LLM if a client exists and a question was typed (respects §0 and §2.3)
    if llm_client is not None and context.question and context.question.strip():
        # Create intermediate serializable result for grounding prompt
        serializable_result = {
            "recommended_gate": chosen_gate.id,
            "gate_name": chosen_gate.name,
            "urgency_tier": urgency_tier.value,
            "congestion": {k: v.value for k, v in congestion_by_gate.items()},
            "route_steps": route_plan.steps,
            "distance_meters": route_plan.distance_meters,
            "estimated_minutes": route_plan.estimated_minutes,
            "landmarks": route_plan.landmarks,
            "accessibility_mode": accessibility_mode,
            "reasoning": reasoning,
            "is_egress": is_egress,
        }
        decision_json_str = json.dumps(serializable_result, ensure_ascii=False)

        answer, used_llm = await phrase_with_llm(
            context=context,
            decision_json_str=decision_json_str,
            llm_client=llm_client,
            fallback_text=fallback_text,
        )

    # 9. Pack final structured decision result
    decision_result = DecisionResultSchema(
        recommended_gate=chosen_gate.id,
        urgency_tier=urgency_tier,
        congestion=congestion_by_gate,
        route_steps=route_plan.steps,
        accessibility_mode=accessibility_mode,
        used_llm=used_llm,
    )

    return {
        "answer": answer,
        "decision": decision_result,
    }
