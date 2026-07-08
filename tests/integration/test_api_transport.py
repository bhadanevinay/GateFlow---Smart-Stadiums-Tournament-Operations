"""Integration tests for transport advice endpoint."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


def test_get_transport_advice(client: TestClient) -> None:
    """Checks travel times ranking retrieval.

    Args:
        client: Shared API test client.

    """
    response = client.get(
        "/api/transport/advice?minutes_to_kickoff=45&accessibility_needs=mobility"
    )
    assert response.status_code == 200
    data = response.json()
    assert "options" in data
    assert len(data["options"]) > 0
    opt = data["options"][0]
    assert "mode" in opt
    assert "total_travel_time_minutes" in opt


def test_get_transport_advice_validation_error(client: TestClient) -> None:
    """Verifies that invalid enum values return 422 error.

    Args:
        client: Shared API test client.

    """
    response = client.get("/api/transport/advice?accessibility_needs=invalid_need")
    assert response.status_code == 422
