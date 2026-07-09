"""LLM Client interface, mock, and Google Gemini SDK client implementation."""

from __future__ import annotations

__all__ = ["GeminiClient", "LLMClient", "MockLLM", "get_llm_client"]

from typing import TYPE_CHECKING, Protocol

from google import genai
from google.genai import types

from app.exceptions import LLMUnavailableError

if TYPE_CHECKING:
    from app.config import Settings


class LLMClient(Protocol):
    """Protocol defining structural requirements for swappable LLM clients."""

    async def generate_text(self, prompt: str, max_tokens: int) -> str:
        """Generates text based on the provided prompt and token limits.

        Args:
            prompt: Detailed grounding instructions and input.
            max_tokens: Maximum tokens to generate.

        Returns:
            The generated response string.

        Raises:
            LLMUnavailableError: If the downstream LLM service is unreachable or fails.

        """
        ...


class MockLLM:
    """Mock LLM client implementation for offline tests and validation."""

    def __init__(self, response_text: str = "Mocked LLM phrasing response.") -> None:
        """Initializes the MockLLM with a default response.

        Args:
            response_text: The fixed response string to return.

        """
        self.response_text = response_text

    async def generate_text(self, prompt: str, max_tokens: int) -> str:
        """Returns the configured mock text.

        Args:
            prompt: Ignored in mock.
            max_tokens: Ignored in mock.

        """
        # If the prompt contains a specific keyword for testing error fallback, raise exception
        if "RAISE_MOCK_ERROR" in prompt:
            raise LLMUnavailableError("Mock LLM error triggered for testing fallback.")
        return self.response_text


class GeminiClient:  # pragma: no cover
    """Live Google Gemini client implementing the LLMClient protocol."""

    def __init__(self, api_key: str, model_name: str) -> None:
        """Initializes the Gemini client.

        Args:
            api_key: Downstream Google Gemini credentials.
            model_name: Model identifier (e.g. 'gemini-2.5-flash').

        """
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name

    async def generate_text(self, prompt: str, max_tokens: int) -> str:
        """Generates text via Google Gemini async API.

        Args:
            prompt: Grounding instructions.
            max_tokens: Ceiling token counts.

        Returns:
            The generated text response.

        Raises:
            LLMUnavailableError: Wraps any network/SDK failures.

        """
        try:
            generation_config = types.GenerateContentConfig(
                max_output_tokens=max_tokens,
                temperature=0.2,  # Low temperature for fact grounding
            )
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=generation_config,
            )
            resp_text = response.text
        except Exception as e:
            raise LLMUnavailableError(f"Gemini client request failed: {e}") from e

        if not resp_text:
            raise LLMUnavailableError("Gemini API returned an empty text response.")
        return str(resp_text).strip()


def get_llm_client(settings: Settings) -> LLMClient | None:
    """Factory function returning the configured LLMClient.

    Args:
        settings: Application Settings instance.

    Returns:
        LLMClient implementation, or None if no Gemini API key is configured.

    """
    if not settings.gemini_api_key:
        return None
    return GeminiClient(  # pragma: no cover
        api_key=settings.gemini_api_key,
        model_name=settings.gemini_model,
    )
