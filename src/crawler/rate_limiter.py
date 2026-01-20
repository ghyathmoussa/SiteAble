"""Rate limiter for crawler requests."""

import asyncio
import time
from typing import Optional


class RateLimiter:
    """Token bucket rate limiter for async requests.

    Limits requests to a maximum rate (requests per second).
    Thread-safe for use with asyncio.
    """

    def __init__(self, requests_per_second: float = 2.0):
        """Initialize rate limiter.

        Args:
            requests_per_second: Maximum requests per second (0 = unlimited)
        """
        self.requests_per_second = requests_per_second
        self.min_interval = 1.0 / requests_per_second if requests_per_second > 0 else 0
        self._last_request_time: float = 0
        self._lock: Optional[asyncio.Lock] = None  # Lazy initialization

    async def acquire(self) -> None:
        """Wait until a request can be made within rate limits.

        This method should be called before making each request.
        It will block if necessary to maintain the rate limit.
        """
        if self.requests_per_second <= 0:
            return  # No rate limiting

        # Lazy initialization of lock
        if self._lock is None:
            self._lock = asyncio.Lock()

        async with self._lock:
            current_time = time.monotonic()
            time_since_last = current_time - self._last_request_time

            if time_since_last < self.min_interval:
                sleep_time = self.min_interval - time_since_last
                await asyncio.sleep(sleep_time)

            self._last_request_time = time.monotonic()

    def reset(self) -> None:
        """Reset the rate limiter state."""
        self._last_request_time = 0


class AdaptiveRateLimiter(RateLimiter):
    """Rate limiter that adapts based on response times and errors.

    Automatically slows down when the server is responding slowly
    or returning errors, and speeds up when things are healthy.
    """

    def __init__(
        self,
        initial_rps: float = 2.0,
        min_rps: float = 0.1,
        max_rps: float = 10.0,
    ):
        """Initialize adaptive rate limiter.

        Args:
            initial_rps: Initial requests per second
            min_rps: Minimum requests per second (slowest rate)
            max_rps: Maximum requests per second (fastest rate)
        """
        super().__init__(initial_rps)
        self.initial_rps = initial_rps
        self.min_rps = min_rps
        self.max_rps = max_rps
        self._error_count = 0
        self._success_count = 0
        self._slow_response_count = 0
        self._slow_threshold = 5.0  # seconds

    def record_success(self, response_time: float) -> None:
        """Record a successful request.

        Args:
            response_time: Time taken for the request in seconds
        """
        self._success_count += 1

        # Check for slow response
        if response_time > self._slow_threshold:
            self._slow_response_count += 1
            self._decrease_rate()
        elif self._success_count % 10 == 0:  # Every 10 successes
            self._increase_rate()

    def record_error(self) -> None:
        """Record a failed request."""
        self._error_count += 1
        self._decrease_rate()

    def _decrease_rate(self) -> None:
        """Decrease the request rate."""
        new_rps = self.requests_per_second * 0.8
        self.requests_per_second = max(new_rps, self.min_rps)
        self.min_interval = 1.0 / self.requests_per_second if self.requests_per_second > 0 else 0

    def _increase_rate(self) -> None:
        """Increase the request rate."""
        new_rps = self.requests_per_second * 1.1
        self.requests_per_second = min(new_rps, self.max_rps)
        self.min_interval = 1.0 / self.requests_per_second if self.requests_per_second > 0 else 0

    def get_stats(self) -> dict:
        """Get rate limiter statistics."""
        return {
            "current_rps": self.requests_per_second,
            "success_count": self._success_count,
            "error_count": self._error_count,
            "slow_response_count": self._slow_response_count,
        }
