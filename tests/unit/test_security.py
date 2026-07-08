"""Unit tests for input sanitization and rate limiting services."""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from app.config import settings
from app.exceptions import RateLimitExceededError
from app.services.security import RateLimiter, sanitize_question


def test_sanitize_question_removes_controls() -> None:
    """Verifies that control characters are removed from input questions."""
    dirty = "Hello\nWorld\r\t\x00!"
    clean = sanitize_question(dirty)
    # \n, \r, \t, and \x00 are under ord < 32, so they should be stripped
    assert clean == "HelloWorld!"


def test_sanitize_question_truncates() -> None:
    """Verifies that long questions are truncated to 1000 characters."""
    long_question = "a" * 1500
    clean = sanitize_question(long_question)
    assert len(clean) == 1000
    assert clean == "a" * 1000


def test_sanitize_question_handles_none() -> None:
    """Checks that None input returns None."""
    assert sanitize_question(None) is None


def test_rate_limiter_in_memory_allowed_and_blocked() -> None:
    """Checks that the in-memory rate limiter enforces requests boundaries."""
    limiter = RateLimiter(settings)

    # Allow BUCKET_CAPACITY (20) requests
    for _ in range(20):
        limiter.check_rate_limit("192.168.1.1")

    # 21st request should be blocked
    with pytest.raises(RateLimitExceededError):
        limiter.check_rate_limit("192.168.1.1")

    # A different IP should be allowed
    limiter.check_rate_limit("192.168.1.2")


def test_rate_limiter_prune() -> None:
    """Verifies that old client entries are pruned to save memory."""
    limiter = RateLimiter(settings)
    limiter.check_rate_limit("192.168.1.1")

    # Simulate past time
    limiter._in_memory_buckets["192.168.1.1"] = (10.0, time.time() - 200)

    # Prune should clear it
    limiter._prune_in_memory_buckets(time.time())
    assert "192.168.1.1" not in limiter._in_memory_buckets


def test_rate_limiter_redis_fallback() -> None:
    """Tests that rate limiter falls back to in-memory if Redis connection fails."""
    with patch("redis.Redis.from_url") as mock_from_url:
        # Simulate connection error
        mock_from_url.side_effect = Exception("Connection refused")
        limiter = RateLimiter(settings)

        # Should fall back to in-memory and allow requests
        limiter.check_rate_limit("10.0.0.1")
        assert "10.0.0.1" in limiter._in_memory_buckets


def test_rate_limiter_prune_via_check() -> None:
    """Verifies that periodic pruning is automatically triggered by check_rate_limit."""
    limiter = RateLimiter(settings)
    limiter.check_rate_limit("192.168.1.1")
    # Simulate past prune time (more than 300 seconds ago)
    limiter._last_prune_time = time.time() - 400
    # Add an entry that is eligible for pruning (elapsed > 120 seconds)
    limiter._in_memory_buckets["192.168.1.2"] = (20.0, time.time() - 400)
    # Check rate limit to trigger periodic pruning
    limiter.check_rate_limit("192.168.1.1")
    # The entry for 192.168.1.2 should be pruned
    assert "192.168.1.2" not in limiter._in_memory_buckets
