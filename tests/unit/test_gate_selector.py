"""Unit tests for the gate selector service."""

from __future__ import annotations

import pytest

from app.exceptions import RouteNotFoundError
from app.models.domain import GateInfo
from app.models.enums import AccessibilityNeed, CongestionLevel, Language, UrgencyTier
from app.models.schemas import FanContextSchema
from app.services.flow_engine.gate_selector import select_best_gate

# Mock data for selector tests
MOCK_GATES = [
    GateInfo(
        "gate_a",
        "Gate A",
        step_free=True,
        sensory_friendly=True,
        audio_cues=True,
        base_capacity_per_min=100,
    ),
    GateInfo(
        "gate_b",
        "Gate B",
        step_free=False,
        sensory_friendly=False,
        audio_cues=False,
        base_capacity_per_min=50,
    ),
]

MOCK_GRAPH = {
    "nodes": ["start_node", "gate_a", "gate_b", "section_101"],
    "edges": [
        {
            "source": "start_node",
            "target": "gate_a",
            "distance": 500.0,
            "step_free": True,
        },
        {
            "source": "gate_a",
            "target": "section_101",
            "distance": 500.0,
            "step_free": True,
        },
        {
            "source": "start_node",
            "target": "gate_b",
            "distance": 50.0,
            "step_free": False,
        },
        {
            "source": "gate_b",
            "target": "section_101",
            "distance": 50.0,
            "step_free": False,
        },
    ],
}


def test_gate_selector_normal_mobility() -> None:
    """Verifies that mobility needs exclude non-step-free gates."""
    context = FanContextSchema(
        language=Language.EN,
        arrival_mode="metro",
        current_location="start_node",
        ticket_section="101",
        accessibility_needs=[AccessibilityNeed.MOBILITY],
        minutes_to_kickoff=45,
    )
    congestion = {"gate_a": CongestionLevel.LOW, "gate_b": CongestionLevel.LOW}
    gate, route, urgency, reasoning = select_best_gate(
        context, MOCK_GATES, congestion, MOCK_GRAPH
    )

    # Gate B is not step-free, so it must pick Gate A even though B is closer
    assert gate.id == "gate_a"
    assert route.step_free is True
    assert urgency == UrgencyTier.NORMAL
    assert "Section 101" in reasoning


def test_gate_selector_normal_no_needs_prefers_closer() -> None:
    """Checks that without mobility needs, the closer gate is preferred when congestion is equal."""
    context = FanContextSchema(
        language=Language.EN,
        arrival_mode="metro",
        current_location="start_node",
        ticket_section="101",
        accessibility_needs=[],
        minutes_to_kickoff=45,
    )
    congestion = {"gate_a": CongestionLevel.LOW, "gate_b": CongestionLevel.LOW}
    gate, route, urgency, reasoning = select_best_gate(
        context, MOCK_GATES, congestion, MOCK_GRAPH
    )

    # Gate B is closer (60+40 = 100m) than Gate A (100+50 = 150m)
    assert gate.id == "gate_b"
    assert route.step_free is False
    assert urgency == UrgencyTier.NORMAL


def test_gate_selector_congestion_reroute() -> None:
    """Checks that high congestion on a closer gate reroutes fans to a lower congestion alternative."""
    context = FanContextSchema(
        language=Language.EN,
        arrival_mode="metro",
        current_location="start_node",
        ticket_section="101",
        accessibility_needs=[],
        minutes_to_kickoff=45,
    )
    # Gate B is highly congested, A is low
    congestion = {"gate_a": CongestionLevel.LOW, "gate_b": CongestionLevel.HIGH}
    gate, route, urgency, _ = select_best_gate(
        context, MOCK_GATES, congestion, MOCK_GRAPH
    )

    # Should reroute to Gate A because of the congestion penalty on Gate B
    assert gate.id == "gate_a"


def test_gate_selector_urgency_prefers_speed() -> None:
    """Verifies that under high urgency, faster route is chosen even with higher congestion."""
    context = FanContextSchema(
        language=Language.EN,
        arrival_mode="metro",
        current_location="start_node",
        ticket_section="101",
        accessibility_needs=[],
        minutes_to_kickoff=10,  # UrgencyTier.HURRY
    )
    # Gate B has medium congestion, Gate A has low.
    # Gate B is closer (100m total). Under urgency, congestion multiplier weight is low (1.5)
    # So gate B should still win on total time
    congestion = {"gate_a": CongestionLevel.LOW, "gate_b": CongestionLevel.MEDIUM}
    gate, route, urgency, _ = select_best_gate(
        context, MOCK_GATES, congestion, MOCK_GRAPH
    )

    assert gate.id == "gate_b"
    assert urgency == UrgencyTier.HURRY


def test_gate_selector_no_accessible_gates() -> None:
    """Verifies RouteNotFoundError is raised if no gates match criteria or are unreachable."""
    context = FanContextSchema(
        language=Language.EN,
        arrival_mode="metro",
        current_location="start_node",
        ticket_section="101",
        accessibility_needs=[AccessibilityNeed.MOBILITY],
        minutes_to_kickoff=45,
    )
    # If MOCK_GATES has no step-free gates
    non_accessible_gates = [
        GateInfo(
            "gate_b",
            "Gate B",
            step_free=False,
            sensory_friendly=False,
            audio_cues=False,
            base_capacity_per_min=50,
        )
    ]
    with pytest.raises(RouteNotFoundError):
        select_best_gate(context, non_accessible_gates, {}, MOCK_GRAPH)


def test_gate_selector_critical_urgency() -> None:
    """Verifies that critical urgency is correctly resolved and evaluated."""
    context = FanContextSchema(
        language=Language.EN,
        arrival_mode="metro",
        current_location="start_node",
        ticket_section="101",
        accessibility_needs=[],
        minutes_to_kickoff=5,  # UrgencyTier.CRITICAL
    )
    gate, route, urgency, _ = select_best_gate(
        context, MOCK_GATES, {}, MOCK_GRAPH
    )
    assert urgency == UrgencyTier.CRITICAL


def test_gate_selector_disconnected_gate() -> None:
    """Verifies that a gate is ignored if there is no route to or from it."""
    context = FanContextSchema(
        language=Language.EN,
        arrival_mode="metro",
        current_location="start_node",
        ticket_section="101",
        accessibility_needs=[],
        minutes_to_kickoff=45,
    )
    # A graph where gate_a is completely disconnected
    disconnected_graph = {
        "nodes": ["start_node", "gate_a", "gate_b", "section_101"],
        "edges": [
            {
                "source": "start_node",
                "target": "gate_b",
                "distance": 50.0,
                "step_free": True,
            },
            {
                "source": "gate_b",
                "target": "section_101",
                "distance": 50.0,
                "step_free": True,
            },
        ],
    }
    gate, route, urgency, _ = select_best_gate(
        context, MOCK_GATES, {}, disconnected_graph
    )
    # It must pick gate_b because gate_a is disconnected
    assert gate.id == "gate_b"


def test_gate_selector_no_path() -> None:
    """Checks that RouteNotFoundError is raised if no gates have paths to target section."""
    context = FanContextSchema(
        language=Language.EN,
        arrival_mode="metro",
        current_location="start_node",
        ticket_section="101",
        accessibility_needs=[],
        minutes_to_kickoff=45,
    )
    # A graph where section_101 is isolated
    isolated_graph = {
        "nodes": ["start_node", "gate_a", "gate_b", "section_101"],
        "edges": [
            {
                "source": "start_node",
                "target": "gate_a",
                "distance": 50.0,
                "step_free": True,
            },
        ],
    }
    with pytest.raises(RouteNotFoundError):
        select_best_gate(context, MOCK_GATES, {}, isolated_graph)
