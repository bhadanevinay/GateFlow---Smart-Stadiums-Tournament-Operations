"""Unit tests for the offline template phrasing service."""

from __future__ import annotations

from app.models.domain import GateInfo
from app.models.enums import CongestionLevel, Language, UrgencyTier
from app.services.phrasing.template_phraser import phrase_decision

MOCK_GATES = [
    GateInfo("gate_c", "Gate C (South Metro Gate)", True, True, True, 200),
]
MOCK_CONGESTION = {"gate_c": CongestionLevel.LOW}


def test_english_normal_phrasing() -> None:
    """Verifies English phrasing for normal urgency."""
    ans = phrase_decision(
        language=Language.EN,
        urgency_tier=UrgencyTier.NORMAL,
        recommended_gate_id="gate_c",
        gates=MOCK_GATES,
        congestion_by_gate=MOCK_CONGESTION,
        ticket_section="128",
        distance_meters=150.0,
        estimated_minutes=2.5,
        landmarks=["South Entrance Ramp", "Elevator lobby"],
    )
    assert "Head to Gate C" in ans
    assert "Section 128" in ans
    assert "150m" in ans
    assert "South Entrance Ramp" in ans


def test_spanish_hurry_phrasing() -> None:
    """Verifies Spanish phrasing for hurry urgency."""
    ans = phrase_decision(
        language=Language.ES,
        urgency_tier=UrgencyTier.HURRY,
        recommended_gate_id="gate_c",
        gates=MOCK_GATES,
        congestion_by_gate=MOCK_CONGESTION,
        ticket_section="128",
        distance_meters=150.0,
        estimated_minutes=2.5,
        landmarks=[],
    )
    assert "¡Urgente" in ans
    assert "Sección 128" in ans


def test_hindi_critical_phrasing() -> None:
    """Verifies Hindi phrasing for critical urgency."""
    ans = phrase_decision(
        language=Language.HI,
        urgency_tier=UrgencyTier.CRITICAL,
        recommended_gate_id="gate_c",
        gates=MOCK_GATES,
        congestion_by_gate=MOCK_CONGESTION,
        ticket_section="128",
        distance_meters=150.0,
        estimated_minutes=2.5,
        landmarks=["Ramp A"],
    )
    assert "गंभीर" in ans
    assert "गेट" in ans or "किकऑफ" in ans


def test_fallback_landmarks() -> None:
    """Checks that a language-specific landmarks fallback is used if none provided."""
    ans = phrase_decision(
        language=Language.FR,
        urgency_tier=UrgencyTier.NORMAL,
        recommended_gate_id="gate_c",
        gates=MOCK_GATES,
        congestion_by_gate=MOCK_CONGESTION,
        ticket_section="128",
        distance_meters=150.0,
        estimated_minutes=2.5,
        landmarks=[],
    )
    assert "suivre la signalisation du couloir" in ans


def test_template_phraser_unknown_gate() -> None:
    """Verifies template phrasing when recommended gate ID is not found in gates list."""
    ans = phrase_decision(
        language=Language.EN,
        urgency_tier=UrgencyTier.NORMAL,
        recommended_gate_id="gate_unknown",
        gates=MOCK_GATES,
        congestion_by_gate=MOCK_CONGESTION,
        ticket_section="128",
        distance_meters=150.0,
        estimated_minutes=2.5,
        landmarks=[],
    )
    assert "gate_unknown" in ans
