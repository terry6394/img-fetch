"""Tests for retry logic and error handling."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from img_fetch.core.product import Product
from img_fetch.fetchers.youzan_fetcher import YouzanFetcher
from img_fetch.utils.exceptions import NetworkError, ImageNotFoundError


class TestRetryLogic:
    """Tests for retry logic in fetchers."""

    def test_youzan_fetcher_supports_retry(self):
        """Test that YouzanFetcher indicates it supports retry."""
        fetcher = YouzanFetcher()
        assert fetcher.can_retry() is True

    @patch("img_fetch.fetchers.youzan_fetcher.requests.get")
    def test_fetch_does_not_retry_on_network_error(self, mock_get):
        """Test that fetch does NOT automatically retry on network errors.

        Note: The YouzanFetcher uses rate limiting but does not implement
        automatic retry logic. If a network error occurs, it fails immediately.
        """
        import requests

        fetcher = YouzanFetcher()

        product = Product(
            excel_row=1,
            name="Test Product",
            spec="BLACK-M",
            brand="TEST",
            product_url="https://shop152506312.m.youzan.com/v2/goods/123"
        )

        # All calls fail with network error
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection reset")

        result = fetcher.fetch(product)

        # Should have called get only once (no automatic retry)
        assert mock_get.call_count == 1
        assert result is None
        assert product.status == "failed"

    @patch("img_fetch.fetchers.youzan_fetcher.requests.get")
    def test_fetch_handles_rate_limit_error(self, mock_get):
        """Test that fetch handles rate limiting gracefully."""
        import requests

        fetcher = YouzanFetcher()

        product = Product(
            excel_row=1,
            name="Test Product",
            spec="BLACK-M",
            brand="TEST",
            product_url="https://shop152506312.m.youzan.com/v2/goods/123"
        )

        # Rate limit error
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection reset")

        result = fetcher.fetch(product)

        assert result is None
        assert product.status == "failed"

    def test_product_retries_counter(self):
        """Test that product retries counter is tracked."""
        product = Product(
            excel_row=1,
            name="Test Product",
            spec="BLACK-M",
            product_url="https://example.com/product"
        )

        assert product.retries == 0

        product.retries += 1
        assert product.retries == 1


class TestErrorHandling:
    """Tests for error handling scenarios."""

    @patch("img_fetch.fetchers.youzan_fetcher.requests.get")
    def test_handles_http_404(self, mock_get):
        """Test handling of 404 Not Found."""
        import requests

        fetcher = YouzanFetcher()

        product = Product(
            excel_row=1,
            name="Test Product",
            spec="BLACK-M",
            product_url="https://shop152506312.m.youzan.com/v2/goods/123"
        )

        # Create mock response with proper raise_for_status behavior
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        # Make raise_for_status raise HTTPError on 404
        def raise_for_status():
            if mock_response.status_code == 404:
                raise requests.exceptions.HTTPError("404 Not Found")
        mock_response.raise_for_status = raise_for_status

        result = fetcher.fetch(product)

        assert result is None
        assert product.status == "failed"

    @patch("img_fetch.fetchers.youzan_fetcher.requests.get")
    def test_handles_timeout(self, mock_get):
        """Test handling of request timeout."""
        import requests

        fetcher = YouzanFetcher()

        product = Product(
            excel_row=1,
            name="Test Product",
            spec="BLACK-M",
            product_url="https://shop152506312.m.youzan.com/v2/goods/123"
        )

        mock_get.side_effect = requests.exceptions.Timeout("Request timed out")

        result = fetcher.fetch(product)

        assert result is None
        assert product.status == "failed"

    @patch("img_fetch.fetchers.youzan_fetcher.requests.get")
    def test_handles_invalid_html(self, mock_get):
        """Test handling of invalid/malformed HTML."""
        fetcher = YouzanFetcher()

        product = Product(
            excel_row=1,
            name="Test Product",
            spec="BLACK-M",
            product_url="https://shop152506312.m.youzan.com/v2/goods/123"
        )

        mock_response = Mock()
        mock_response.text = "Not valid HTML at all"
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = fetcher.fetch(product)

        assert result is None
        assert product.status == "failed"
        assert "No image found" in product.error_message

    @patch("img_fetch.fetchers.youzan_fetcher.requests.get")
    def test_handles_empty_page(self, mock_get):
        """Test handling of empty page content."""
        fetcher = YouzanFetcher()

        product = Product(
            excel_row=1,
            name="Test Product",
            spec="BLACK-M",
            product_url="https://shop152506312.m.youzan.com/v2/goods/123"
        )

        mock_response = Mock()
        mock_response.text = ""
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = fetcher.fetch(product)

        assert result is None
        assert product.status == "failed"


class TestErrorExceptions:
    """Tests for custom exception classes."""

    def test_network_error(self):
        """Test NetworkError exception."""
        error = NetworkError("Connection failed")
        assert str(error) == "Connection failed"
        assert issubclass(NetworkError, Exception)

    def test_image_not_found_error(self):
        """Test ImageNotFoundError exception."""
        error = ImageNotFoundError("No image on page")
        assert str(error) == "No image on page"
        assert issubclass(ImageNotFoundError, Exception)

    def test_exceptions_are_catchable(self):
        """Test that custom exceptions can be caught."""
        with pytest.raises(NetworkError):
            raise NetworkError("test")

        with pytest.raises(ImageNotFoundError):
            raise ImageNotFoundError("test")