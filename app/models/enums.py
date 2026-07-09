"""Domain enums defining the vocabulary of GateFlow."""

from __future__ import annotations

__all__ = [
    "AccessibilityNeed",
    "ArrivalMode",
    "CongestionLevel",
    "Language",
    "UrgencyTier",
]

from enum import StrEnum


class Language(StrEnum):
    """Supported response languages."""

    EN = "en"
    ES = "es"
    FR = "fr"
    HI = "hi"


class AccessibilityNeed(StrEnum):
    """User-declared accessibility requirements."""

    MOBILITY = "mobility"
    VISUAL = "visual"
    HEARING = "hearing"


class ArrivalMode(StrEnum):
    """Available stadium transport and arrival modes."""

    METRO = "metro"
    PARKING = "parking"
    RIDESHARE = "rideshare"
    SHUTTLE = "shuttle"


class UrgencyTier(StrEnum):
    """Urgency level based on time-to-kickoff."""

    NORMAL = "normal"
    HURRY = "hurry"
    CRITICAL = "critical"


class CongestionLevel(StrEnum):
    """Live or simulated crowd density status at gates/zones."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
