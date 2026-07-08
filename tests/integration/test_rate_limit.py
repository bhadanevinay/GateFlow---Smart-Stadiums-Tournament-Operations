"""Integration tests for rate limiter and security headers middlewares."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.main import app

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


def test_rate_limiter_blocks_requests(client: TestClient) -> None:
    """Verifies that the API rate limiter triggers 429 when client limits are exceeded.

    Args:
        client: Shared API test client.

    """
    # Temporarily set rate limit to 3 for testing
    limiter = app.state.rate_limiter
    limiter.capacity = 3.0
    limiter.refill_rate = 3.0 / 60.0
    # Clear client ip records
    limiter._in_memory_buckets.clear()

    # Make 3 requests to health endpoint (not rate-limited) and 3 to transport advice (rate-limited)
    for _ in range(3):
        res = client.get("/api/transport/advice?minutes_to_kickoff=40")
        assert res.status_code == 200

    # 4th request must fail with 429
    res = client.get("/api/transport/advice?minutes_to_kickoff=40")
    assert res.status_code == 429
    assert res.headers.get("Retry-After") is not None


def test_security_headers_present(client: TestClient) -> None:
    """Asserts that all standard security headers are present on API responses.

    Args:
        client: Shared API test client.

    """
    response = client.get("/health")
    assert response.status_code == 200
    headers = response.headers

    assert headers.get("X-Request-ID") is not None
    assert "default-src 'self'" in headers.get("Content-Security-Policy", "")
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("Referrer-Policy") == "no-referrer"
    assert headers.get("X-Frame-Options") == "DENY"
