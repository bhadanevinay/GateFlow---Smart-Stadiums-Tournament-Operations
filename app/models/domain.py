"""Domain model classes for GateFlow."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.enums import ArrivalMode, CongestionLevel, UrgencyTier


@dataclass(frozen=True, slots=True)
class GateInfo:
    """Represents a stadium entrance gate.

    Attributes:
      id: Unique identifier for the gate (e.g., 'gate_a').
      name: Human-readable gate name.
      step_free: Whether the gate route is step-free.
      sensory_friendly: Whether the gate is optimized for sensory sensitivity.
      audio_cues: Whether the gate features audio cues.
      base_capacity_per_min: Base processing capacity in fans per minute.

    """

    id: str
    name: str
    step_free: bool
    sensory_friendly: bool
    audio_cues: bool
    base_capacity_per_min: int


@dataclass(frozen=True, slots=True)
class RoutePlan:
    """Represents a path through the venue concourse.

    Attributes:
      steps: Sequential list of node IDs along the path.
      distance_meters: Total travel distance in meters.
      estimated_minutes: Total estimated walking time.
      landmarks: Descriptive list of navigation landmarks along the way.
      step_free: True if the entire route is step-free/wheelchair accessible.

    """

    steps: list[str]
    distance_meters: float
    estimated_minutes: float
    landmarks: list[str]
    step_free: bool


@dataclass(frozen=True, slots=True)
class TransportOption:
    """Represents a transit recommendation option.

    Attributes:
      mode: Arrival transport mode.
      name: Description of the specific terminal/line.
      eta_minutes: Simulated transit/driving time to the stadium area.
      wait_minutes: Queue/wait time at the transport node.
      congestion: Current congestion level at the terminal.
      arrival_node: Graph node matching the arrival point.
      total_travel_time_minutes: Sum of ETA and wait time.

    """

    mode: ArrivalMode
    name: str
    eta_minutes: float
    wait_minutes: float
    congestion: CongestionLevel
    arrival_node: str
    total_travel_time_minutes: float


@dataclass(frozen=True, slots=True)
class DecisionResult:
    """The frozen single source of truth containing a flow engine decision.

    Attributes:
      recommended_gate: The ID of the chosen entry gate.
      urgency_tier: Urgency level calculated based on time-to-kickoff.
      congestion: Map of gate IDs to their current congestion levels.
      route_steps: Sequential path from arrival point to ticket section.
      accessibility_mode: List of active accessibility configuration flags.
      used_llm: Whether this decision's description was phrased via the LLM.
      reasoning: Natural-language explanation of the decision parameters.

    """

    recommended_gate: str
    urgency_tier: UrgencyTier
    congestion: dict[str, CongestionLevel]
    route_steps: list[str]
    accessibility_mode: list[str]
    used_llm: bool
    reasoning: str
