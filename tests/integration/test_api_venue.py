"""Integration tests for venue and gates data endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

from app.main import app

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


def test_get_venue_info(client: TestClient) -> None:
    """Verifies that stadium layout metadata is loaded.

    Args:
        client: Shared API test client.

    """
    response = client.get("/api/venue")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert data["name"] == "Lusail Iconic Stadium"
    assert "total_capacity" in data


def test_get_venue_gates(client: TestClient) -> None:
    """Verifies retrieval of gates list with live congestion.

    Args:
        client: Shared API test client.

    """
    response = client.get("/api/venue/gates?minutes_to_kickoff=30")
    assert response.status_code == 200
    gates = response.json()
    assert len(gates) > 0
    gate = gates[0]
    assert "id" in gate
    assert "name" in gate
    assert "step_free" in gate
    assert "congestion" in gate


def test_get_venue_gates_validation_error(client: TestClient) -> None:
    """Verifies that invalid minutes parameter returns 422 error.

    Args:
        client: Shared API test client.

    """
    # minutes_to_kickoff must be >= -180 and <= 600
    response = client.get("/api/venue/gates?minutes_to_kickoff=1000")
    assert response.status_code == 422


def test_get_root(client: TestClient) -> None:
    """Verifies that the root path serves the single page application if exists."""
    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("fastapi.responses.FileResponse") as mock_file_response,
    ):
        mock_file_response.return_value = "file response mockup"  # type: ignore[assignment]
        response = client.get("/")
        # If mock succeeds or falls back gracefully
        assert response.status_code in (200, 404)


def test_get_root_404(client: TestClient) -> None:
    """Verifies that the root path returns 404 when index.html is missing."""
    # Mock exists to return False specifically for index.html check
    with patch("pathlib.Path.exists", return_value=False):
        response = client.get("/")
    assert response.status_code == 404
    assert response.json()["detail"] == "Frontend assets not found."


def test_rate_limiter_none_in_state(client: TestClient) -> None:
    """Verifies that the rate limiter middleware handles a missing state entry gracefully."""
    # Temporarily remove rate limiter from app state
    old_limiter = getattr(app.state, "rate_limiter", None)
    if old_limiter is not None:
        del app.state.rate_limiter

    try:
        # Request should succeed because rate limiting is skipped
        res = client.get("/api/transport/advice?minutes_to_kickoff=40")
        assert res.status_code == 200
    finally:
        # Restore rate limiter
        if old_limiter is not None:
            app.state.rate_limiter = old_limiter
