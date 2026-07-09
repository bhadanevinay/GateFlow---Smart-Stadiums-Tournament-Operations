"""Deterministic time-seeded congestion simulation service.

Calculates gate and zone congestion based on time-to-kickoff and a deterministic
pseudo-random seed derived from the gate ID and the current hour.
"""

from __future__ import annotations

import datetime
import hashlib
from typing import Final

from app.models.enums import CongestionLevel

# Congestion calculation constants
MINUTES_CRITICAL_WINDOW: Final[int] = 15
MINUTES_HIGH_WINDOW: Final[int] = 30
MINUTES_MEDIUM_WINDOW: Final[int] = 60
MINUTES_EGRESS_THRESHOLD: Final[int] = -105
MINUTES_ONGOING_THRESHOLD: Final[int] = -10


def get_gate_congestion(
    gate_id: str,
    minutes_to_kickoff: int,
    current_hour: int | None = None,
) -> CongestionLevel:
    """Calculates simulated congestion for a gate.

    The congestion is based primarily on minutes remaining until kickoff (representing
    crowd arrival waves) and is overlayed with a stable pseudo-random value seeded
    by the gate ID and current hour of the day.

    Time Complexity: O(1)
    Space Complexity: O(1)

    Args:
        gate_id: ID of the gate to calculate congestion for.
        minutes_to_kickoff: Minutes until kickoff.
        current_hour: Optional hour override (0-23) for testing and stability.

    Returns:
        The simulated CongestionLevel.

    """
    # 1. Determine base level based on time-to-kickoff
    # Egress congestion (post-match egress begins when kickoff is way in the past, e.g., minutes_to_kickoff < -105)
    # Match duration is typically 105 mins (90 mins + halftime + added time)
    if minutes_to_kickoff < MINUTES_EGRESS_THRESHOLD:
        # High exit congestion
        base_tier = 2  # High
    elif minutes_to_kickoff < MINUTES_ONGOING_THRESHOLD:
        # Match is ongoing, very low traffic
        base_tier = 0  # Low
    elif minutes_to_kickoff <= MINUTES_CRITICAL_WINDOW:
        # Peak rush right before kickoff
        base_tier = 3  # Critical
    elif minutes_to_kickoff <= MINUTES_HIGH_WINDOW:
        base_tier = 2  # High
    elif minutes_to_kickoff <= MINUTES_MEDIUM_WINDOW:
        base_tier = 1  # Medium
    else:
        base_tier = 0  # Low

    # 2. Get stable hour seed
    if current_hour is None:  # pragma: no cover
        current_hour = datetime.datetime.now(datetime.UTC).hour

    # 3. Compute deterministic variation using hashing
    # Generate deterministic pseudo-random seed from gate_id + hour to ensure
    # consistent congestion values within the same hour across requests
    seed_str = f"{gate_id}:{current_hour}"
    hasher = hashlib.md5(seed_str.encode("utf-8"), usedforsecurity=False)
    seed_val = int(hasher.hexdigest()[:8], 16)

    # Shift base tier by -1, 0, or +1 based on hash value
    shift = (seed_val % 3) - 1
    final_tier = max(0, min(3, base_tier + shift))

    levels = [
        CongestionLevel.LOW,
        CongestionLevel.MEDIUM,
        CongestionLevel.HIGH,
        CongestionLevel.CRITICAL,
    ]
    return levels[final_tier]
