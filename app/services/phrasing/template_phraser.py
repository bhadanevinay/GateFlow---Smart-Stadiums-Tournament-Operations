"""Offline template phraser service.

Formats a deterministic decision result into a natural-language description using
localized templates, with zero I/O.
"""

from __future__ import annotations

__all__ = ["phrase_decision"]

from typing import TYPE_CHECKING, Final

from app.models.enums import CongestionLevel, Language, UrgencyTier
from app.services.phrasing.templates import get_template

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from app.models.domain import GateInfo

# Localized fallbacks for empty landmarks list
LANDMARKS_FALLBACK: Final[Mapping[Language, str]] = {
    Language.EN: "follow concourse signs",
    Language.ES: "siga las señales del pasillo",
    Language.FR: "suivre la signalisation du couloir",
    Language.HI: "मुख्य मार्ग के संकेतों का पालन करें",
}


def phrase_decision(
    language: Language,
    urgency_tier: UrgencyTier,
    recommended_gate_id: str,
    gates: Sequence[GateInfo],
    congestion_by_gate: Mapping[str, CongestionLevel],
    ticket_section: str,
    distance_meters: float,
    estimated_minutes: float,
    landmarks: Sequence[str],
) -> str:
    """Phrases the decision results using localized templates.

    Time Complexity: O(G + L) where G is the number of gates and L is the number of landmarks.
    Space Complexity: O(L) for the formatted landmarks string.

    Args:
        language: Preferred Language enum.
        urgency_tier: Computed UrgencyTier enum.
        recommended_gate_id: Chosen gate ID.
        gates: Available venue gates.
        congestion_by_gate: Current gate congestion map.
        ticket_section: Target seating section.
        distance_meters: Total route walking distance.
        estimated_minutes: Estimated walking duration in minutes.
        landmarks: Navigation landmarks along the route.

    Returns:
        The phrased, localized natural language description string.

    """
    # 1. Resolve the gate's name
    gate_name = recommended_gate_id
    for gate in gates:
        if gate.id == recommended_gate_id:
            gate_name = gate.name
            break

    # 2. Resolve congestion text
    congestion_lvl = congestion_by_gate.get(recommended_gate_id, CongestionLevel.LOW)
    congestion_text = congestion_lvl.value

    # 3. Format landmarks list
    if landmarks:
        landmarks_str = ", ".join(landmarks)
    else:
        landmarks_str = LANDMARKS_FALLBACK.get(
            language, LANDMARKS_FALLBACK[Language.EN]
        )

    # 4. Fetch the localized template
    template = get_template(language, urgency_tier)

    # 5. Format and return the template
    return template.format(
        gate_name=gate_name,
        congestion_level=congestion_text,
        section=ticket_section,
        distance=distance_meters,
        time=estimated_minutes,
        landmarks_str=landmarks_str,
    )
