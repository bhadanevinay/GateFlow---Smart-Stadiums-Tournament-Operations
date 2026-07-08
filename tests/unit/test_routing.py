"""Unit tests for the Dijkstra routing engine."""

from __future__ import annotations

import pytest

from app.exceptions import RouteNotFoundError, UnknownZoneError
from app.models.enums import AccessibilityNeed
from app.services.flow_engine.routing import calculate_route

# Minimal graph for testing
TEST_GRAPH = {
    "nodes": ["A", "B", "C", "D", "E"],
    "edges": [
        {
            "source": "A",
            "target": "B",
            "distance": 100.0,
            "step_free": True,
            "landmark_description": "Sign A to B",
        },
        {
            "source": "B",
            "target": "C",
            "distance": 50.0,
            "step_free": False,
            "landmark_description": "Stairs B to C",
        },
        {
            "source": "A",
            "target": "D",
            "distance": 200.0,
            "step_free": True,
            "landmark_description": "Ramp A to D",
        },
        {
            "source": "D",
            "target": "C",
            "distance": 60.0,
            "step_free": True,
            "landmark_description": "Ramp D to C",
        },
        {
            "source": "E",
            "target": "E",
            "distance": 0.0,
            "step_free": True,
        },  # self loop or isolated
    ],
}


def test_standard_shortest_path() -> None:
    """Verifies that the shortest path is found without accessibility constraints."""
    # Without mobility need, routing should prefer B -> C path (100 + 50 = 150)
    # over D -> C path (200 + 60 = 260)
    route = calculate_route("A", "C", TEST_GRAPH, accessibility_needs=[])
    assert route.steps == ["A", "B", "C"]
    assert route.distance_meters == 150.0
    assert route.step_free is False
    assert "Sign A to B" in route.landmarks
    assert "Stairs B to C" in route.landmarks


def test_accessible_path_routing() -> None:
    """Verifies that non-accessible paths are filtered out for mobility needs."""
    # With mobility need, B -> C is filtered out because it's not step-free.
    # It must fallback to A -> D -> C (200 + 60 = 260)
    route = calculate_route(
        "A", "C", TEST_GRAPH, accessibility_needs=[AccessibilityNeed.MOBILITY]
    )
    assert route.steps == ["A", "D", "C"]
    assert route.distance_meters == 260.0
    assert route.step_free is True
    assert "Ramp A to D" in route.landmarks
    assert "Ramp D to C" in route.landmarks


def test_routing_raises_unknown_zone() -> None:
    """Checks that UnknownZoneError is raised for invalid nodes."""
    with pytest.raises(UnknownZoneError):
        calculate_route("INVALID", "C", TEST_GRAPH, [])
    with pytest.raises(UnknownZoneError):
        calculate_route("A", "INVALID", TEST_GRAPH, [])


def test_routing_raises_path_not_found() -> None:
    """Checks that RouteNotFoundError is raised for disconnected nodes."""
    # E is disconnected from others (no edges to A)
    with pytest.raises(RouteNotFoundError):
        calculate_route("A", "E", TEST_GRAPH, [])


def test_routing_start_equals_destination() -> None:
    """Verifies route details when start and destination are the same."""
    route = calculate_route("A", "A", TEST_GRAPH, [])
    assert route.steps == ["A"]
    assert route.distance_meters == 0.0
    assert route.estimated_minutes == 0.0
    assert not route.landmarks
    assert route.step_free is True
