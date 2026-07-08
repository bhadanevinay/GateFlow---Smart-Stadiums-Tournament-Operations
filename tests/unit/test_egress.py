"""Unit tests for the egress post-match routing service."""

from __future__ import annotations

import pytest

from app.exceptions import RouteNotFoundError, UnknownZoneError
from app.models.domain import GateInfo
from app.models.enums import AccessibilityNeed, CongestionLevel, Language
from app.models.schemas import FanContextSchema
from app.services.flow_engine.egress import calculate_egress_route

MOCK_GATES = [
    GateInfo(
        "gate_c",
        "Gate C",
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
    "nodes": ["section_128", "gate_c", "gate_b", "metro_station"],
    "edges": [
        {
            "source": "section_128",
            "target": "gate_c",
            "distance": 50.0,
            "step_free": True,
        },
        {
            "source": "gate_c",
            "target": "metro_station",
            "distance": 100.0,
            "step_free": True,
        },
        {
            "source": "section_128",
            "target": "gate_b",
            "distance": 40.0,
            "step_free": False,
        },
        {
            "source": "gate_b",
            "target": "metro_station",
            "distance": 60.0,
            "step_free": False,
        },
    ],
}

MOCK_TRANSPORT = {"metro": {"name": "Metro Terminal", "arrival_node": "metro_station"}}


def test_egress_normal_routing() -> None:
    """Checks basic post-match egress path planning."""
    context = FanContextSchema(
        language=Language.EN,
        arrival_mode="metro",
        current_location="section_128",  # during egress current_location is section but schemas require valid current_location
        ticket_section="128",
        accessibility_needs=[],
        minutes_to_kickoff=-110,
    )
    congestion = {"gate_c": CongestionLevel.LOW, "gate_b": CongestionLevel.LOW}
    gate, route, reasoning = calculate_egress_route(
        context, MOCK_GATES, congestion, MOCK_GRAPH, MOCK_TRANSPORT
    )

    # Gate B is closer for egress (40+60 = 100m total vs 50+100=150m for gate C)
    assert gate.id == "gate_b"
    assert route.steps == ["section_128", "gate_b", "metro_station"]
    assert route.distance_meters == 100.0
    assert route.step_free is False
    assert "Gate B" in reasoning


def test_egress_mobility_needs() -> None:
    """Verifies step-free constraint on exit routes."""
    context = FanContextSchema(
        language=Language.EN,
        arrival_mode="metro",
        current_location="section_128",
        ticket_section="128",
        accessibility_needs=[AccessibilityNeed.MOBILITY],
        minutes_to_kickoff=-110,
    )
    congestion = {"gate_c": CongestionLevel.LOW, "gate_b": CongestionLevel.LOW}
    gate, route, _ = calculate_egress_route(
        context, MOCK_GATES, congestion, MOCK_GRAPH, MOCK_TRANSPORT
    )

    # Gate C is step-free
    assert gate.id == "gate_c"
    assert route.steps == ["section_128", "gate_c", "metro_station"]
    assert route.distance_meters == 150.0
    assert route.step_free is True


def test_egress_congestion_penalty() -> None:
    """Checks that highly congested exits are penalized and bypassed."""
    context = FanContextSchema(
        language=Language.EN,
        arrival_mode="metro",
        current_location="section_128",
        ticket_section="128",
        accessibility_needs=[],
        minutes_to_kickoff=-110,
    )
    # B has lower distance but high congestion
    congestion = {"gate_c": CongestionLevel.LOW, "gate_b": CongestionLevel.HIGH}
    gate, route, _ = calculate_egress_route(
        context, MOCK_GATES, congestion, MOCK_GRAPH, MOCK_TRANSPORT
    )

    # B is penalized, should pick C
    assert gate.id == "gate_c"


def test_egress_missing_transport_mode() -> None:
    """Checks that UnknownZoneError is raised if transport mode config is missing."""
    context = FanContextSchema(
        language=Language.EN,
        arrival_mode="parking",  # Missing in MOCK_TRANSPORT
        current_location="section_128",
        ticket_section="128",
        accessibility_needs=[],
        minutes_to_kickoff=-110,
    )
    with pytest.raises(UnknownZoneError):
        calculate_egress_route(context, MOCK_GATES, {}, MOCK_GRAPH, MOCK_TRANSPORT)


def test_egress_no_accessible_gates() -> None:
    """Verifies RouteNotFoundError is raised if no step-free gates exist for mobility needs."""
    context = FanContextSchema(
        language=Language.EN,
        arrival_mode="metro",
        current_location="section_128",
        ticket_section="128",
        accessibility_needs=[AccessibilityNeed.MOBILITY],
        minutes_to_kickoff=-110,
    )
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
        calculate_egress_route(context, non_accessible_gates, {}, MOCK_GRAPH, MOCK_TRANSPORT)


def test_egress_critical_congestion() -> None:
    """Checks that critical congestion is correctly penalized."""
    context = FanContextSchema(
        language=Language.EN,
        arrival_mode="metro",
        current_location="section_128",
        ticket_section="128",
        accessibility_needs=[],
        minutes_to_kickoff=-110,
    )
    # B has CRITICAL congestion, C has LOW
    congestion = {"gate_c": CongestionLevel.LOW, "gate_b": CongestionLevel.CRITICAL}
    gate, route, _ = calculate_egress_route(
        context, MOCK_GATES, congestion, MOCK_GRAPH, MOCK_TRANSPORT
    )
    assert gate.id == "gate_c"


def test_egress_disconnected_gate() -> None:
    """Checks that a gate is ignored if there is no path through it."""
    context = FanContextSchema(
        language=Language.EN,
        arrival_mode="metro",
        current_location="section_128",
        ticket_section="128",
        accessibility_needs=[],
        minutes_to_kickoff=-110,
    )
    # A graph where gate_b is disconnected from metro_station
    disconnected_graph = {
        "nodes": ["section_128", "gate_c", "gate_b", "metro_station"],
        "edges": [
            {
                "source": "section_128",
                "target": "gate_c",
                "distance": 50.0,
                "step_free": True,
            },
            {
                "source": "gate_c",
                "target": "metro_station",
                "distance": 100.0,
                "step_free": True,
            },
            {
                "source": "section_128",
                "target": "gate_b",
                "distance": 40.0,
                "step_free": False,
            },
        ],
    }
    gate, route, _ = calculate_egress_route(
        context, MOCK_GATES, {}, disconnected_graph, MOCK_TRANSPORT
    )
    # Must choose gate_c because gate_b is disconnected from destination
    assert gate.id == "gate_c"


def test_egress_no_path() -> None:
    """Checks that RouteNotFoundError is raised if no paths exist to transport node."""
    context = FanContextSchema(
        language=Language.EN,
        arrival_mode="metro",
        current_location="section_128",
        ticket_section="128",
        accessibility_needs=[],
        minutes_to_kickoff=-110,
    )
    # A graph where metro_station is isolated
    isolated_graph = {
        "nodes": ["section_128", "gate_c", "gate_b", "metro_station"],
        "edges": [
            {
                "source": "section_128",
                "target": "gate_c",
                "distance": 50.0,
                "step_free": True,
            },
        ],
    }
    with pytest.raises(RouteNotFoundError):
        calculate_egress_route(context, MOCK_GATES, {}, isolated_graph, MOCK_TRANSPORT)
