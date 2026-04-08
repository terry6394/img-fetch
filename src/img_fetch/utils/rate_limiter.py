"""Rate limiting utilities."""

import time
import threading
from typing import Optional
from urllib.parse import urlparse

from img_fetch.config import RATE_LIMITS


class RateLimiter:
    """
    Rate limiter for controlling request frequency per domain.

    Thread-safe implementation using locks.
    """

    def __init__(self, custom_limits: Optional[dict[str, int]] = None):
        """
        Initialize rate limiter.

        Args:
            custom_limits: Optional custom rate limits (requests per minute)
                          to override defaults from config.
        """
        self._limits = {**RATE_LIMITS, **(custom_limits or {})}
        self._last_request: dict[str, float] = {}
        self._lock = threading.Lock()

    def wait(self, url: str) -> None:
        """
        Wait if necessary to respect rate limits for the domain.

        Args:
            url: URL to check rate limit for
        """
        domain = self._extract_domain(url)
        if not domain:
            return

        limit = self._limits.get(domain)
        if not limit:
            # No rate limit configured for this domain
            return

        min_delay = 60.0 / limit  # seconds between requests

        with self._lock:
            now = time.time()
            last = self._last_request.get(domain, 0)
            elapsed = now - last

            if elapsed < min_delay:
                sleep_time = min_delay - elapsed
                time.sleep(sleep_time)
                now = time.time()

            self._last_request[domain] = now

    def _extract_domain(self, url: str) -> Optional[str]:
        """
        Extract domain from URL.

        Args:
            url: Full URL

        Returns:
            Domain string or None if extraction fails
        """
        try:
            parsed = urlparse(url)
            return parsed.netloc.lower()
        except Exception:
            return None

    def get_wait_time(self, url: str) -> float:
        """
        Get the current wait time for a URL.

        Args:
            url: URL to check

        Returns:
            Seconds to wait before next request (0 if no limit)
        """
        domain = self._extract_domain(url)
        if not domain:
            return 0.0

        limit = self._limits.get(domain)
        if not limit:
            return 0.0

        min_delay = 60.0 / limit

        with self._lock:
            last = self._last_request.get(domain, 0)
            elapsed = time.time() - last
            return max(0.0, min_delay - elapsed)

    def reset(self, url: Optional[str] = None) -> None:
        """
        Reset rate limit tracking.

        Args:
            url: If provided, reset only this domain. Otherwise reset all.
        """
        with self._lock:
            if url:
                domain = self._extract_domain(url)
                if domain and domain in self._last_request:
                    del self._last_request[domain]
            else:
                self._last_request.clear()

    def set_limit(self, domain: str, requests_per_minute: int) -> None:
        """
        Set a custom rate limit for a domain.

        Args:
            domain: Domain to set limit for
            requests_per_minute: New limit
        """
        with self._lock:
            self._limits[domain] = requests_per_minute
