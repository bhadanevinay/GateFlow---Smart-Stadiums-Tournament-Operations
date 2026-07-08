"""Unit tests for the congestion calculation service."""

from __future__ import annotations

from app.models.enums import CongestionLevel
from app.services.flow_engine.congestion import get_gate_congestion


def test_egress_congestion() -> None:
    """Verifies exit congestion when minutes_to_kickoff indicates post-match egress."""
    # minutes_to_kickoff < -105 should trigger egress waves (High exit base)
    res = get_gate_congestion("gate_c", -120, current_hour=12)
    assert isinstance(res, CongestionLevel)
    # With MD5 hash seed, let's verify it resolves to a valid CongestionLevel
    assert res in [
        CongestionLevel.MEDIUM,
        CongestionLevel.HIGH,
        CongestionLevel.CRITICAL,
    ]


def test_ongoing_match_congestion() -> None:
    """Verifies that congestion is low during the match (ongoing play)."""
    # -105 <= minutes_to_kickoff < -10
    res = get_gate_congestion("gate_a", -50, current_hour=12)
    # Base level is Low, shift can make it Low or Medium
    assert res in [CongestionLevel.LOW, CongestionLevel.MEDIUM]


def test_peak_rush_congestion() -> None:
    """Verifies peak congestion near kickoff."""
    # minutes_to_kickoff = 5 (critical window)
    res = get_gate_congestion("gate_c", 5, current_hour=12)
    # Base is Critical (3), shift is (seed % 3) - 1. So it could be High or Critical.
    assert res in [CongestionLevel.HIGH, CongestionLevel.CRITICAL]


def test_deterministic_behavior() -> None:
    """Asserts that calculations are stable and deterministic for the same parameters."""
    c1 = get_gate_congestion("gate_a", 45, current_hour=15)
    c2 = get_gate_congestion("gate_a", 45, current_hour=15)
    assert c1 == c2


def test_default_hour_resolution() -> None:
    """Checks that the function runs correctly without current_hour specified."""
    res = get_gate_congestion("gate_a", 45)
    assert isinstance(res, CongestionLevel)


def test_early_arrival_congestion() -> None:
    """Verifies low base congestion for early arrivals (minutes_to_kickoff > 90)."""
    res = get_gate_congestion("gate_a", 120, current_hour=12)
    assert res in (CongestionLevel.LOW, CongestionLevel.MEDIUM)
