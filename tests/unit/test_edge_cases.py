"""Edge case tests for img_fetch modules."""

import pytest
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from urllib.parse import urlparse

from img_fetch.core.product import Product
from img_fetch.core.file_namer import sanitize_filename, is_safe_filename
from img_fetch.utils.rate_limiter import RateLimiter
from img_fetch.writers.report_writer import ReportWriter


class TestPathTraversalEdgeCases:
    """Test path traversal security edge cases."""

    def test_sanitize_removes_parent_directory_reference(self):
        """Test that ../ is properly removed from filenames."""
        # Critical security test: path traversal should be neutralized
        assert sanitize_filename("../file.jpg") == "file.jpg"

    def test_sanitize_removes_multiple_parent_references(self):
        """Test that multiple ../ are properly removed."""
        assert sanitize_filename("../../etc/passwd") == "etcpasswd"

    def test_sanitize_removes_leading_slash(self):
        """Test that leading / is removed."""
        assert sanitize_filename("/etc/passwd") == "etcpasswd"

    def test_sanitize_handles_relative_path_with_dots(self):
        """Test handling of paths with dots but not traversal."""
        assert sanitize_filename(".../file.jpg") == "file.jpg"

    def test_sanitize_handles_windows_style_paths(self):
        """Test Windows-style path separators."""
        result = sanitize_filename("..\\file.jpg")
        # Backslash is in FORBIDDEN_CHARS and gets replaced
        assert ".." not in result

    def test_is_safe_filename_rejects_parent_traversal(self):
        """Test is_safe_filename rejects ../ patterns."""
        assert is_safe_filename("../file.jpg") is False
        assert is_safe_filename("foo/../bar.jpg") is False

    def test_is_safe_filename_rejects_absolute_paths(self):
        """Test is_safe_filename rejects absolute paths."""
        assert is_safe_filename("/etc/passwd") is False
        assert is_safe_filename("C:\\Windows\\file.jpg") is False


class TestInvalidURLEdgeCases:
    """Test handling of invalid URLs."""

    def test_malformed_url_handling(self):
        """Test that malformed URLs are handled gracefully."""
        # Empty URL
        url = ""
        parsed = urlparse(url)
        assert parsed.scheme == ""
        assert parsed.netloc == ""

    def test_url_with_no_scheme(self):
        """Test URL without scheme is handled."""
        url = "www.example.com/page"
        parsed = urlparse(url)
        # urlparse doesn't add scheme automatically
        assert parsed.netloc == ""

    def test_url_with_special_characters(self):
        """Test URL with special characters in query string."""
        url = "https://example.com/search?q=test&name=foo bar"
        parsed = urlparse(url)
        assert parsed.netloc == "example.com"


class TestRateLimiterEdgeCases:
    """Test rate limiter edge cases."""

    def test_unknown_domain_no_delay(self):
        """Test that unknown domains don't cause delays."""
        limiter = RateLimiter()
        start = time.time()
        limiter.wait("https://completely-unknown-domain-12345.com/page")
        elapsed = time.time() - start
        # Should be essentially instantaneous
        assert elapsed < 0.1

    def test_case_insensitive_domain_matching(self):
        """Test that domain matching is case-insensitive."""
        limiter = RateLimiter({"EXAMPLE.COM": 60})  # 1 per second
        start = time.time()
        limiter.wait("https://example.com/page1")
        limiter.wait("https://EXAMPLE.COM/page2")
        elapsed = time.time() - start
        # Should have waited at least 1 second
        assert elapsed >= 1.0

    def test_subdomain_difference(self):
        """Test that subdomains are treated as different."""
        limiter = RateLimiter({"example.com": 60})
        start = time.time()
        limiter.wait("https://example.com/page1")
        limiter.wait("https://www.example.com/page2")
        elapsed = time.time() - start
        # Should NOT have waited, as www is different from bare domain
        # (This is current behavior, may need review)
        assert elapsed < 0.5

    def test_port_in_url_handled(self):
        """Test that port numbers in URLs are handled."""
        limiter = RateLimiter({"example.com": 60})
        # URLs with ports should still be rate limited
        start = time.time()
        limiter.wait("https://example.com:8080/page1")
        limiter.wait("https://example.com:8080/page2")
        elapsed = time.time() - start
        assert elapsed >= 1.0


class TestProductEdgeCases:
    """Test Product model edge cases."""

    def test_product_with_empty_name(self):
        """Test product with empty name."""
        product = Product(
            excel_row=1,
            name="",
            spec="BLACK-M",
            brand="TEST"
        )
        assert product.name == ""
        assert product.search_query == ""

    def test_product_with_only_spec(self):
        """Test product with name empty but spec present."""
        product = Product(
            excel_row=1,
            name="",
            spec="BLACK-M",
            brand="TEST"
        )
        assert product.spec == "BLACK-M"
        # search_query should only include name if it's non-empty
        # The __post_init__ builds from name and spec, but skips if name is empty
        assert product.search_query == ""

    def test_product_with_unicode_characters(self):
        """Test product with unicode characters in name."""
        product = Product(
            excel_row=1,
            name="测试产品 Test Product",
            spec="黑色-M",
            brand="TEST"
        )
        assert "测试" in product.name
        assert product.search_query == "测试产品 Test Product 黑色-M"

    def test_product_without_brand(self):
        """Test product without brand defaults to empty."""
        product = Product(
            excel_row=1,
            name="Alpha Jacket",
            spec="BLACK-M",
            brand=""
        )
        assert product.brand == ""


class TestReportWriterEdgeCases:
    """Test report writer edge cases."""

    def test_empty_product_list(self, tmp_path):
        """Test report with empty product list."""
        writer = ReportWriter(output_dir=tmp_path)
        writer.write_report([])
        assert writer.get_report_path().exists()

    def test_product_with_long_name_truncation(self, tmp_path):
        """Test that very long product names don't break report."""
        product = Product(
            excel_row=1,
            name="A" * 500,  # Very long name
            spec="BLACK-M",
            brand="TEST",
            status="success"
        )
        writer = ReportWriter(output_dir=tmp_path)
        writer.write_report([product])
        assert writer.get_report_path().exists()

    def test_product_with_special_characters_in_name(self, tmp_path):
        """Test product names with special characters."""
        product = Product(
            excel_row=1,
            name='Product "Special" <Characters> & More',
            spec="BLACK-M",
            brand="TEST",
            status="success"
        )
        writer = ReportWriter(output_dir=tmp_path)
        writer.write_report([product])  # Should not raise
        assert writer.get_report_path().exists()


class TestFileNamerEdgeCases:
    """Test file namer edge cases."""

    def test_very_long_filename_truncated(self):
        """Test that very long filenames are truncated."""
        long_name = "A" * 300
        result = sanitize_filename(long_name)
        assert len(result) <= 255  # Max filename length

    def test_filename_with_only_forbidden_chars(self):
        """Test filename made entirely of forbidden characters."""
        result = sanitize_filename('<>:"|?*')
        assert result != '<>:"|?*'  # Should be sanitized
        assert len(result) > 0

    def test_empty_filename_returns_unnamed(self):
        """Test that empty filename returns 'unnamed'."""
        assert sanitize_filename("") == "unnamed"
        assert sanitize_filename("   ") == "unnamed"

    def test_filename_with_newlines(self):
        """Test filename with newline characters."""
        result = sanitize_filename("file\nname.jpg")
        assert "\n" not in result

    def test_filename_with_tabs(self):
        """Test filename with tab characters."""
        result = sanitize_filename("file\tname.jpg")
        assert "\t" not in result
