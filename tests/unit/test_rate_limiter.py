"""Unit tests for rate_limiter module."""

import pytest
import time
import threading

from img_fetch.utils.rate_limiter import RateLimiter


class TestRateLimiter:
    """Tests for RateLimiter class."""

    def test_basic_rate_limiting(self):
        """Test basic rate limiting works."""
        limiter = RateLimiter({"example.com": 60})  # 1 per second
        start = time.time()
        limiter.wait("https://example.com/page1")
        limiter.wait("https://example.com/page2")
        elapsed = time.time() - start
        # Should have waited at least 1 second between requests
        assert elapsed >= 1.0

    def test_no_limit_for_unknown_domain(self):
        """Test no limit is applied for unknown domains."""
        limiter = RateLimiter()
        start = time.time()
        limiter.wait("https://unknown-domain.com/page")
        elapsed = time.time() - start
        # Should not have waited at all
        assert elapsed < 0.1

    def test_custom_limits(self):
        """Test custom rate limits."""
        limiter = RateLimiter({"fast.com": 600})  # 10 per second
        start = time.time()
        for i in range(5):
            limiter.wait(f"https://fast.com/page{i}")
        elapsed = time.time() - start
        # 5 requests at 10/second = 0.4 seconds minimum
        assert elapsed >= 0.4

    def test_thread_safety(self):
        """Test rate limiter is thread-safe."""
        limiter = RateLimiter({"example.com": 6000})  # 100 per second
        results = []

        def make_request(url: str):
            limiter.wait(url)
            results.append(time.time())

        threads = []
        for i in range(10):
            t = threading.Thread(target=make_request, args=(f"https://example.com/page{i}",))
            threads.append(t)

        start = time.time()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        elapsed = time.time() - start

        # All 10 requests should complete in roughly 0.1 seconds (10 per second limit)
        # but no less than the minimum interval
        assert len(results) == 10
        # Results should be sorted (all threads completed)
        assert results == sorted(results)

    def test_get_wait_time(self):
        """Test get_wait_time returns correct values."""
        limiter = RateLimiter({"example.com": 60})  # 1 per second

        # No previous request
        wait = limiter.get_wait_time("https://example.com/page1")
        assert wait == 0.0

        # After a request
        limiter.wait("https://example.com/page1")
        wait = limiter.get_wait_time("https://example.com/page2")
        assert wait > 0.9  # Should wait almost a full second

    def test_reset_single_domain(self):
        """Test resetting a single domain."""
        limiter = RateLimiter({"example.com": 60})

        limiter.wait("https://example.com/page1")
        limiter.reset("https://example.com/page1")

        # Should not have to wait after reset
        start = time.time()
        limiter.wait("https://example.com/page2")
        elapsed = time.time() - start
        assert elapsed < 0.1

    def test_reset_all(self):
        """Test resetting all domains."""
        limiter = RateLimiter({"example.com": 60, "other.com": 60})

        limiter.wait("https://example.com/page1")
        limiter.wait("https://other.com/page1")

        limiter.reset()

        # Should not have to wait after reset
        start = time.time()
        limiter.wait("https://example.com/page2")
        limiter.wait("https://other.com/page2")
        elapsed = time.time() - start
        assert elapsed < 0.1

    def test_set_limit(self):
        """Test setting new rate limit."""
        limiter = RateLimiter()
        assert limiter.get_wait_time("https://new.com/page") == 0.0  # No limit

        limiter.set_limit("new.com", 60)  # 1 per second
        limiter.wait("https://new.com/page1")
        wait = limiter.get_wait_time("https://new.com/page2")
        assert wait > 0.9

    def test_domain_extraction(self):
        """Test various URL formats are handled."""
        limiter = RateLimiter({"example.com": 60})

        urls = [
            "https://example.com/page",
            "http://example.com/page",
            "https://www.example.com/page",
            "https://EXAMPLE.COM/page",
        ]

        for url in urls:
            start = time.time()
            limiter.wait(url)
            elapsed = time.time() - start
            # All should be rate limited the same way
            assert elapsed >= 0.9
