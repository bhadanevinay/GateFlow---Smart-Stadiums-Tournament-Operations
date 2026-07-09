"""Security services including input sanitization and rate limiting.

Implements a per-IP token bucket rate limiter with an optional Redis backend
supporting atomic Lua script token consumption and a graceful in-memory fallback.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Final

import redis

from app.exceptions import RateLimitExceededError
from app.models.schemas import MAX_QUESTION_LENGTH

if TYPE_CHECKING:
    from app.config import Settings

logger = logging.getLogger("gateflow")

# Rate limiter constants
BUCKET_CAPACITY: Final[float] = 20.0
REFILL_RATE_PER_SEC: Final[float] = 20.0 / 60.0  # 20 requests per minute
PRUNE_THRESHOLD_SEC: Final[float] = 120.0  # Idle threshold to remove bucket

# Sanitization constants
ASCII_PRINTABLE_MIN: Final[int] = 32
ASCII_DELETE: Final[int] = 127

# Lua script for atomic Redis token bucket
LUA_RATE_LIMITER: Final[str] = """
-- Atomic token bucket implementation:
-- 1. Fetch current tokens and last_update timestamp from Redis hash
-- 2. Calculate elapsed time and refill tokens (capped at max_tokens)
-- 3. Attempt to consume 'cost' tokens
-- 4. Return {1, 0} on success, {0, wait_time} on rate-limited
local key = KEYS[1]
local max_tokens = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local cost = tonumber(ARGV[4])
local ttl = tonumber(ARGV[5])

local data = redis.call('HMGET', key, 'tokens', 'last_update')
local tokens = tonumber(data[1])
local last_update = tonumber(data[2])

if not tokens then
    tokens = max_tokens
    last_update = now
else
    local elapsed = now - last_update
    tokens = math.min(max_tokens, tokens + (elapsed * refill_rate))
end

if tokens >= cost then
    tokens = tokens - cost
    redis.call('HMSET', key, 'tokens', tokens, 'last_update', now)
    redis.call('EXPIRE', key, ttl)
    return {1, 0}
else
    local wait_time = (cost - tokens) / refill_rate
    return {0, wait_time}
end
"""


class RateLimiter:
    """Per-IP Token Bucket Rate Limiter with Redis backend and in-memory fallback."""

    def __init__(self, settings: Settings) -> None:
        """Initializes the RateLimiter instance.

        Args:
            settings: The application settings.

        """
        self.redis_url = settings.redis_url
        self.capacity = float(settings.rate_limit_requests_per_minute)
        self.refill_rate = self.capacity / 60.0  # tokens per second

        self._in_memory_buckets: dict[str, tuple[float, float]] = {}
        self._last_prune_time = time.time()

        self._redis_client: redis.Redis | None = None
        self._redis_script = None

        if self.redis_url:  # pragma: no cover
            try:
                self._redis_client = redis.Redis.from_url(
                    self.redis_url, socket_timeout=1.0, socket_connect_timeout=1.0
                )
                self._redis_script = self._redis_client.register_script(
                    LUA_RATE_LIMITER
                )
            except redis.RedisError as e:
                logger.warning(
                    "Failed to initialize Redis rate limiter. Falling back to in-memory: %s",
                    e,
                )

    def _prune_in_memory_buckets(self, now: float) -> None:
        """Prunes idle in-memory token buckets to prevent memory leaks.

        Time Complexity: O(N) where N is number of active client IPs.
        Space Complexity: O(1).
        """
        idle_ips = [
            ip
            for ip, (_, last_time) in self._in_memory_buckets.items()
            if now - last_time > PRUNE_THRESHOLD_SEC
        ]
        for ip in idle_ips:
            self._in_memory_buckets.pop(ip, None)
        self._last_prune_time = now

    def _check_in_memory(self, ip: str, now: float) -> float:
        """Checks rate limit using local memory.

        Returns 0.0 if allowed, or float representing wait time in seconds if blocked.
        """
        # Periodic pruning
        if now - self._last_prune_time > PRUNE_THRESHOLD_SEC:
            self._prune_in_memory_buckets(now)

        tokens, last_time = self._in_memory_buckets.get(ip, (self.capacity, now))

        # Refill tokens
        elapsed = now - last_time
        tokens = min(self.capacity, tokens + (elapsed * self.refill_rate))

        if tokens >= 1.0:
            self._in_memory_buckets[ip] = (tokens - 1.0, now)
            return 0.0

        self._in_memory_buckets[ip] = (tokens, now)
        return (1.0 - tokens) / self.refill_rate

    def _check_redis(self, ip: str, now: float) -> float | None:  # pragma: no cover
        """Checks rate limit using Redis client.

        Returns wait_time (0.0 if allowed), or None if Redis request fails.
        """
        if self._redis_client is None or self._redis_script is None:
            return None

        key = f"rate_limit:{ip}"
        try:
            # Run atomic script
            # Returns allowed_flag and wait_time values
            res = self._redis_script(
                keys=[key],
                args=[
                    self.capacity,
                    self.refill_rate,
                    now,
                    1.0,  # cost
                    120,  # TTL in seconds
                ],
            )
            allowed, wait_time = res
            if allowed == 1:
                return 0.0
            return float(wait_time)
        except redis.RedisError as e:
            logger.warning("Redis rate limiter error, falling back to in-memory: %s", e)
            return None

    def check_rate_limit(self, ip: str) -> None:
        """Checks rate limit for a client IP.

        Args:
            ip: Client IP address.

        Raises:
            RateLimitExceededError: If the rate limit is exceeded.

        """
        now = time.time()
        wait_time = None

        # 1. Try Redis rate limiting if client active
        if self._redis_client is not None:  # pragma: no cover
            wait_time = self._check_redis(ip, now)

        # 2. Fallback to in-memory check
        if wait_time is None:  # pragma: no cover
            wait_time = self._check_in_memory(ip, now)

        if wait_time > 0.0:
            raise RateLimitExceededError(
                f"Rate limit exceeded. Try again in {wait_time:.1f} seconds."
            )


def sanitize_question(question: str | None) -> str | None:
    """Removes control characters and truncates free-text questions.

    Time Complexity: O(N) where N is length of string.
    Space Complexity: O(N) for sanitized string.

    Args:
        question: Original user input string.

    Returns:
        Sanitized and truncated string, or None if input was None.

    """
    if question is None:
        return None

    # Strip control characters (ASCII ord < 32 and DEL 127)
    sanitized = "".join(
        ch
        for ch in question
        if ord(ch) >= ASCII_PRINTABLE_MIN and ord(ch) != ASCII_DELETE
    )

    # Length-cap to 1000 characters
    if len(sanitized) > MAX_QUESTION_LENGTH:
        sanitized = sanitized[:MAX_QUESTION_LENGTH]

    return sanitized
