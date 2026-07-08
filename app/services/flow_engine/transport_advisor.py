"""Transportation advising service.

Scores and ranks transport modes (metro, parking, rideshare, shuttle) by combining
base durations with congestion factors, terminal queues, and accessibility overrides.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Final

from app.models.domain import TransportOption
from app.models.enums import AccessibilityNeed, ArrivalMode, CongestionLevel
from app.services.flow_engine.congestion import get_gate_congestion

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

# Congestion travel multipliers
CONGESTION_TIME_MULTIPLIERS: Final[Mapping[CongestionLevel, float]] = {
    CongestionLevel.LOW: 1.0,
    CongestionLevel.MEDIUM: 1.2,
    CongestionLevel.HIGH: 1.5,
    CongestionLevel.CRITICAL: 2.0,
}

# Accessibility delay adjustments
MOBILITY_TERMINAL_WAIT_ADDITION: Final[float] = 5.0  # extra mins for elevators/boarding


def recommend_transport(
    accessibility_needs: Sequence[AccessibilityNeed],
    minutes_to_kickoff: int,
    transport_nodes: Mapping[str, Mapping[str, Any]],
    current_hour: int | None = None,
) -> list[TransportOption]:
    """Scores and ranks transport modes by travel time, congestion, and accessibility.

    Returns a list of TransportOption sorted by total travel time ascending.

    Time Complexity: O(M) where M is the number of transport options (constant).
    Space Complexity: O(M) to store the returned options.

    Args:
        accessibility_needs: User-declared accessibility requirements.
        minutes_to_kickoff: Minutes remaining until kickoff.
        transport_nodes: Transport config loaded from transport_nodes.json.
        current_hour: Optional hour override for stable testing.

    Returns:
        List of ranked TransportOption objects.

    """
    options: list[TransportOption] = []
    is_mobility = AccessibilityNeed.MOBILITY in accessibility_needs

    for mode_str, config in transport_nodes.items():
        try:
            mode = ArrivalMode(mode_str)
        except ValueError:
            continue

        name = str(config["name"])
        base_eta = float(config["base_eta_minutes"])
        base_wait = float(config["base_wait_minutes"])
        arrival_node = str(config["arrival_node"])

        # Determine terminal congestion deterministically using the arrival node ID
        congestion = get_gate_congestion(
            gate_id=arrival_node,
            minutes_to_kickoff=minutes_to_kickoff,
            current_hour=current_hour,
        )

        multiplier = CONGESTION_TIME_MULTIPLIERS[congestion]

        # Calculate dynamic travel components
        eta = base_eta * multiplier
        wait = base_wait * multiplier

        # Add accessibility delay for mobility assistance requirements
        if is_mobility:
            wait += MOBILITY_TERMINAL_WAIT_ADDITION

        total_time = eta + wait

        options.append(
            TransportOption(
                mode=mode,
                name=name,
                eta_minutes=eta,
                wait_minutes=wait,
                congestion=congestion,
                arrival_node=arrival_node,
                total_travel_time_minutes=total_time,
            )
        )

    # Sort options by total travel time ascending (fastest first)
    options.sort(key=lambda x: x.total_travel_time_minutes)
    return options
