"""Domain-specific exceptions for the GateFlow application."""

from __future__ import annotations


class GateFlowError(Exception):
    """Base exception class for all GateFlow domain errors."""


class UnknownZoneError(GateFlowError):
    """Raised when a specified zone ID does not exist in the venue configuration."""


class UnknownGateError(GateFlowError):
    """Raised when a specified gate ID does not exist in the venue configuration."""


class InvalidContextError(GateFlowError):
    """Raised when the provided user context is invalid or violates constraints."""


class RouteNotFoundError(GateFlowError):
    """Raised when no path can be resolved between requested nodes."""


class RateLimitExceededError(GateFlowError):
    """Raised when the user exceeds their allocated rate limit."""


class LLMUnavailableError(GateFlowError):
    """Raised when the LLM phrasing layer fails or is unreachable."""
