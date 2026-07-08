"""Pydantic schemas for API request and response validation."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import (
    AccessibilityNeed,
    ArrivalMode,
    CongestionLevel,
    Language,
    UrgencyTier,
)


class FanContextSchema(BaseModel):
    """Input context for fan assistance request."""

    model_config = ConfigDict(extra="forbid")

    language: Language = Field(
        default=Language.EN,
        description="The fan's preferred language for the phrasing layer.",
    )
    arrival_mode: ArrivalMode = Field(
        ...,
        description="Transit mode used by the fan to arrive at the stadium.",
    )
    current_location: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="ID of the zone where the fan is currently located.",
    )
    ticket_section: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Ticket section number/ID (e.g. '128').",
    )
    accessibility_needs: list[AccessibilityNeed] = Field(
        default_factory=list,
        description="Declared accessibility requirements.",
    )
    minutes_to_kickoff: int = Field(
        ...,
        ge=-180,
        le=600,
        description="Minutes remaining until kickoff. Negative for post-kickoff.",
    )
    question: str | None = Field(
        default=None,
        max_length=1000,
        description="Optional free-text question asked by the fan.",
    )


class DecisionResultSchema(BaseModel):
    """Pydantic schema representing the flow engine decision result."""

    model_config = ConfigDict(extra="forbid")

    recommended_gate: str = Field(..., description="ID of the recommended gate.")
    urgency_tier: UrgencyTier = Field(..., description="Calculated urgency tier.")
    congestion: dict[str, CongestionLevel] = Field(
        ...,
        description="Current gate congestion status.",
    )
    route_steps: list[str] = Field(..., description="Steps along the concourse route.")
    accessibility_mode: list[str] = Field(
        ...,
        description="Active accessibility configuration tags.",
    )
    used_llm: bool = Field(..., description="Whether the LLM phrasing layer was used.")


class AssistResponseSchema(BaseModel):
    """Response containing natural language answer and structured decision."""

    model_config = ConfigDict(extra="forbid")

    answer: str = Field(..., description="The phrased natural language response.")
    decision: DecisionResultSchema = Field(
        ...,
        description="The structured decision metadata.",
    )


class TransportOptionSchema(BaseModel):
    """Travel details for a transit arrival option."""

    model_config = ConfigDict(extra="forbid")

    mode: ArrivalMode = Field(..., description="Arrival transport mode.")
    name: str = Field(..., description="Description of the transit node.")
    eta_minutes: float = Field(..., ge=0, description="Transit duration in minutes.")
    wait_minutes: float = Field(..., ge=0, description="Terminal wait time in minutes.")
    congestion: CongestionLevel = Field(..., description="Congestion at terminal.")
    arrival_node: str = Field(..., description="Graph arrival node ID.")
    total_travel_time_minutes: float = Field(
        ...,
        ge=0,
        description="Sum of ETA and terminal wait time.",
    )


class TransportAdviceResponseSchema(BaseModel):
    """Ranked transportation suggestions response."""

    model_config = ConfigDict(extra="forbid")

    options: list[TransportOptionSchema] = Field(
        ...,
        description="Ranked transit modes based on estimated time.",
    )


class ZoneInfoSchema(BaseModel):
    """Metadata detailing a venue zone."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="Name of the zone.")
    description: str = Field(..., description="Description of the zone area.")


class SectionInfoSchema(BaseModel):
    """Schema for individual stadium section details."""

    model_config = ConfigDict(extra="forbid")

    zone: str = Field(..., description="Zone the section belongs to.")
    accessible: bool = Field(..., description="Whether the section has step-free access.")


class VenueInfoResponseSchema(BaseModel):
    """Response returning general venue information."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="Venue name.")
    total_capacity: int = Field(..., ge=0, description="Total stadium capacity.")
    zones: dict[str, ZoneInfoSchema] = Field(..., description="Map of stadium zones.")
    sections: dict[str, SectionInfoSchema] = Field(..., description="Map of stadium sections.")


class GateDetailSchema(BaseModel):
    """Properties and status of a gate."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Gate ID.")
    name: str = Field(..., description="Human-readable gate name.")
    step_free: bool = Field(..., description="Is the gate route step-free.")
    sensory_friendly: bool = Field(..., description="Is the gate sensory friendly.")
    audio_cues: bool = Field(..., description="Does the gate use audio cues.")
    congestion: CongestionLevel = Field(..., description="Simulated live congestion.")


class HealthResponseSchema(BaseModel):
    """Liveness health status response."""

    model_config = ConfigDict(extra="forbid")

    status: str = Field("ok", description="Liveness state indicator.")


class HealthzResponseSchema(BaseModel):
    """Readiness status response."""

    model_config = ConfigDict(extra="forbid")

    status: str = Field("ok", description="Readiness state indicator.")
    llm: str = Field(..., description="LLM layer status: 'live' or 'offline'.")
