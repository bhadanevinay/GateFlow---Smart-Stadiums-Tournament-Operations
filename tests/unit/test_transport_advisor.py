"""Unit tests for the transport advisor service."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.models.enums import AccessibilityNeed, ArrivalMode, CongestionLevel
from app.services.flow_engine.transport_advisor import recommend_transport

# Mock config
MOCK_NODES = {
    "metro": {
        "name": "Metro Terminal",
        "base_eta_minutes": 10.0,
        "base_wait_minutes": 5.0,
        "arrival_node": "metro_station",
    },
    "shuttle": {
        "name": "Shuttle Terminal",
        "base_eta_minutes": 20.0,
        "base_wait_minutes": 2.0,
        "arrival_node": "shuttle_bus_stop",
    },
}


@patch("app.services.flow_engine.transport_advisor.get_gate_congestion", return_value=CongestionLevel.LOW)
def test_transport_ranking_by_time(mock_get_congestion: MagicMock) -> None:  # noqa: ARG001
    """Verifies that transport options are correctly calculated and ranked."""
    # Under low congestion:
    # metro: eta=10*1=10, wait=5*1=5, total=15
    # shuttle: eta=20*1=20, wait=2*1=2, total=22
    options = recommend_transport(
        accessibility_needs=[],
        minutes_to_kickoff=45,
        transport_nodes=MOCK_NODES,
        current_hour=12,
    )
    assert len(options) == 2
    assert options[0].mode == ArrivalMode.METRO
    assert options[0].total_travel_time_minutes == 15.0
    assert options[1].mode == ArrivalMode.SHUTTLE
    assert options[1].total_travel_time_minutes == 22.0


@patch("app.services.flow_engine.transport_advisor.get_gate_congestion", return_value=CongestionLevel.LOW)
def test_transport_mobility_adds_wait(mock_get_congestion: MagicMock) -> None:  # noqa: ARG001
    """Verifies that mobility needs append terminal delay constants."""
    # Under low congestion:
    # metro wait becomes 5 * 1 + 5 = 10. Total becomes 20.
    options = recommend_transport(
        accessibility_needs=[AccessibilityNeed.MOBILITY],
        minutes_to_kickoff=45,
        transport_nodes=MOCK_NODES,
        current_hour=12,
    )
    metro_opt = next(o for o in options if o.mode == ArrivalMode.METRO)
    assert metro_opt.wait_minutes == 10.0
    assert metro_opt.total_travel_time_minutes == 20.0


@patch("app.services.flow_engine.transport_advisor.get_gate_congestion", return_value=CongestionLevel.LOW)
def test_invalid_mode_ignored(mock_get_congestion: MagicMock) -> None:  # noqa: ARG001
    """Checks that invalid keys in JSON are ignored gracefully."""
    bad_nodes = {
        "invalid_mode_name": {
            "name": "Bad Terminal",
            "base_eta_minutes": 10,
            "base_wait_minutes": 5,
            "arrival_node": "node",
        }
    }
    options = recommend_transport([], 45, bad_nodes, 12)
    assert not options
