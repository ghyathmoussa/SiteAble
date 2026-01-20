"""Test rate limiter."""

import asyncio
import time

import pytest

from crawler.rate_limiter import AdaptiveRateLimiter, RateLimiter


@pytest.mark.asyncio
async def test_rate_limiter_basic():
    """Test basic rate limiting."""
    limiter = RateLimiter(requests_per_second=10)

    # Should allow immediate first request
    start = time.monotonic()
    await limiter.acquire()
    first_elapsed = time.monotonic() - start
    assert first_elapsed < 0.05  # Should be nearly instant


@pytest.mark.asyncio
async def test_rate_limiter_spacing():
    """Test that requests are properly spaced."""
    limiter = RateLimiter(requests_per_second=5)

    start = time.monotonic()

    # Make 3 requests
    for _ in range(3):
        await limiter.acquire()

    elapsed = time.monotonic() - start

    # With 5 RPS, minimum interval is 0.2s
    # 3 requests should take at least 0.4s (first is instant)
    assert elapsed >= 0.35  # Some tolerance


@pytest.mark.asyncio
async def test_rate_limiter_unlimited():
    """Test unlimited rate (0 RPS)."""
    limiter = RateLimiter(requests_per_second=0)

    start = time.monotonic()

    # Make several requests
    for _ in range(10):
        await limiter.acquire()

    elapsed = time.monotonic() - start

    # Should be nearly instant
    assert elapsed < 0.1


def test_rate_limiter_reset():
    """Test rate limiter reset."""
    limiter = RateLimiter(requests_per_second=1)
    limiter._last_request_time = time.monotonic()
    limiter.reset()
    assert limiter._last_request_time == 0


class TestAdaptiveRateLimiter:
    """Tests for AdaptiveRateLimiter."""

    def test_initial_rate(self):
        """Test initial rate is set correctly."""
        limiter = AdaptiveRateLimiter(initial_rps=5)
        assert limiter.requests_per_second == 5

    def test_decrease_on_error(self):
        """Test rate decreases on error."""
        limiter = AdaptiveRateLimiter(initial_rps=5, min_rps=1)
        initial_rps = limiter.requests_per_second

        limiter.record_error()

        assert limiter.requests_per_second < initial_rps

    def test_decrease_on_slow_response(self):
        """Test rate decreases on slow response."""
        limiter = AdaptiveRateLimiter(initial_rps=5, min_rps=1)
        initial_rps = limiter.requests_per_second

        limiter.record_success(response_time=10.0)  # Slow response

        assert limiter.requests_per_second < initial_rps

    def test_increase_on_success(self):
        """Test rate increases after multiple successes."""
        limiter = AdaptiveRateLimiter(initial_rps=5, max_rps=10)

        # Record enough successes to trigger increase
        for _ in range(15):
            limiter.record_success(response_time=0.1)

        # Rate should have increased
        assert limiter.requests_per_second > 5

    def test_min_rate_respected(self):
        """Test minimum rate is respected."""
        limiter = AdaptiveRateLimiter(initial_rps=2, min_rps=1)

        # Record many errors
        for _ in range(20):
            limiter.record_error()

        assert limiter.requests_per_second >= 1

    def test_max_rate_respected(self):
        """Test maximum rate is respected."""
        limiter = AdaptiveRateLimiter(initial_rps=5, max_rps=10)

        # Record many successes
        for _ in range(100):
            limiter.record_success(response_time=0.1)

        assert limiter.requests_per_second <= 10

    def test_stats(self):
        """Test getting stats."""
        limiter = AdaptiveRateLimiter(initial_rps=5)

        limiter.record_success(0.1)
        limiter.record_success(6.0)  # slow
        limiter.record_error()

        stats = limiter.get_stats()

        assert stats["success_count"] == 2
        assert stats["error_count"] == 1
        assert stats["slow_response_count"] == 1
