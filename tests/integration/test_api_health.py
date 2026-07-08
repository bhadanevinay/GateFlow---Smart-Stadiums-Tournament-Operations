"""Integration tests for the health status check endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


def test_liveness_check(client: TestClient) -> None:
    """Verifies the /health GET endpoint behavior.

    Args:
        client: Shared API test client.

    """
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_check(client: TestClient) -> None:
    """Verifies the /healthz GET endpoint behavior.

    Args:
        client: Shared API test client.

    """
    response = client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["llm"] in ["live", "offline"]
