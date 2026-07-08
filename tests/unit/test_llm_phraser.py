"""Unit tests for the LLM phrasing layer service."""

from __future__ import annotations

import pytest

from app.models.enums import Language
from app.models.schemas import FanContextSchema
from app.services.llm_client import MockLLM
from app.services.phrasing.llm_phraser import phrase_with_llm


@pytest.mark.asyncio
async def test_llm_phraser_success() -> None:
    """Verifies that the LLM phraser successfully uses the client output."""
    context = FanContextSchema(
        language=Language.EN,
        arrival_mode="metro",
        current_location="metro_station",
        ticket_section="128",
        accessibility_needs=[],
        minutes_to_kickoff=45,
        question="Which gate to use?",
    )
    llm_client = MockLLM("This is dynamic LLM text.")
    fallback = "Template fallback text."

    ans, used = await phrase_with_llm(context, "{}", llm_client, fallback)
    assert used is True
    assert ans == "This is dynamic LLM text."


@pytest.mark.asyncio
async def test_llm_phraser_none_client() -> None:
    """Verifies that the template fallback is used immediately if no client configured."""
    context = FanContextSchema(
        language=Language.EN,
        arrival_mode="metro",
        current_location="metro_station",
        ticket_section="128",
        accessibility_needs=[],
        minutes_to_kickoff=45,
        question="Which gate to use?",
    )
    ans, used = await phrase_with_llm(context, "{}", None, "Fallback text")
    assert used is False
    assert ans == "Fallback text"


@pytest.mark.asyncio
async def test_llm_phraser_client_fails() -> None:
    """Verifies fallback to templates when client raises an exception."""
    context = FanContextSchema(
        language=Language.EN,
        arrival_mode="metro",
        current_location="metro_station",
        ticket_section="128",
        accessibility_needs=[],
        minutes_to_kickoff=45,
        # Triggers MockLLM error condition
        question="RAISE_MOCK_ERROR",
    )
    llm_client = MockLLM()
    ans, used = await phrase_with_llm(context, "{}", llm_client, "Fallback text")
    assert used is False
    assert ans == "Fallback text"


@pytest.mark.asyncio
async def test_llm_phraser_unexpected_error_handling() -> None:
    """Checks that any generic runtime exception is caught and falls back safely."""
    context = FanContextSchema(
        language=Language.EN,
        arrival_mode="metro",
        current_location="metro_station",
        ticket_section="128",
        accessibility_needs=[],
        minutes_to_kickoff=45,
        question="Test query",
    )

    class BrokenClient:
        async def generate_text(self, prompt: str, max_tokens: int) -> str:
            raise RuntimeError("Broken network socket connection!")

    ans, used = await phrase_with_llm(
        context,
        "{}",
        BrokenClient(),
        "Fallback text",  # type: ignore
    )
    assert used is False
    assert ans == "Fallback text"


@pytest.mark.asyncio
async def test_llm_phraser_sanitizes_question_length() -> None:
    """Verifies that very long questions are cropped."""
    long_question = "a" * 1200
    context = FanContextSchema.model_construct(
        language=Language.EN,
        arrival_mode="metro",
        current_location="metro_station",
        ticket_section="128",
        accessibility_needs=[],
        minutes_to_kickoff=45,
        question=long_question,
    )
    llm_client = MockLLM()
    # Should not raise exception
    ans, used = await phrase_with_llm(context, "{}", llm_client, "Fallback")
    assert ans == "Mocked LLM phrasing response."


@pytest.mark.asyncio
async def test_llm_phraser_empty_response() -> None:
    """Verifies that empty response from LLM falls back to template."""
    context = FanContextSchema(
        language=Language.EN,
        arrival_mode="metro",
        current_location="metro_station",
        ticket_section="128",
        accessibility_needs=[],
        minutes_to_kickoff=45,
        question="Help me",
    )
    llm_client = MockLLM("")
    ans, used = await phrase_with_llm(context, "{}", llm_client, "Fallback text")
    assert used is False
    assert ans == "Fallback text"
