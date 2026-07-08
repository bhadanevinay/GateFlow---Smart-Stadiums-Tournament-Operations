"""Conftest module containing shared pytest fixtures."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.services.llm_client import MockLLM

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture(scope="session")
def client() -> Iterator[TestClient]:
    """Provides a TestClient initialized with the FastAPI application.

    Yields:
        TestClient instance.

    """
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def mock_settings_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock key settings env vars to ensure predictable testing behaviors."""
    monkeypatch.setattr(settings, "gemini_api_key", "mocked_key")
    monkeypatch.setattr(settings, "gemini_model", "gemini-2.5-flash")
    monkeypatch.setattr(settings, "redis_url", None)  # Fallback to local rate limit
    monkeypatch.setattr(settings, "rate_limit_requests_per_minute", 20)


@pytest.fixture(autouse=True)
def inject_mock_llm() -> None:
    """Injects MockLLM client into application state for all tests."""
    app.state.llm_client = MockLLM()
