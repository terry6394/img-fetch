"""Tests for Youzan fetcher module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from img_fetch.core.product import Product, ImageMetadata
from img_fetch.fetchers.youzan_fetcher import YouzanFetcher


class TestYouzanFetcher:
    """Tests for YouzanFetcher class."""

    def test_supports_youzan_url(self):
        """Test that YouzanFetcher supports youzan.com URLs."""
        fetcher = YouzanFetcher()

        product = Product(
            excel_row=1,
            name="Test Product",
            spec="BLACK-M",
            product_url="https://shop152506312.m.youzan.com/v2/goods/3eonf4t3mspjk2v"
        )

        assert fetcher.supports(product) is True

    def test_does_not_support_non_youzan_url(self):
        """Test that YouzanFetcher does not support non-youzan URLs."""
        fetcher = YouzanFetcher()

        product = Product(
            excel_row=1,
            name="Test Product",
            spec="BLACK-M",
            product_url="https://amazon.com/product/123"
        )

        assert fetcher.supports(product) is False

    def test_does_not_support_missing_url(self):
        """Test that YouzanFetcher does not support products without URL."""
        fetcher = YouzanFetcher()

        product = Product(
            excel_row=1,
            name="Test Product",
            spec="BLACK-M",
            product_url=""
        )

        assert fetcher.supports(product) is False

    def test_can_retry(self):
        """Test that YouzanFetcher supports retries."""
        fetcher = YouzanFetcher()
        assert fetcher.can_retry() is True

    @patch("img_fetch.fetchers.youzan_fetcher.requests.get")
    def test_fetch_extracts_image_from_page(self, mock_get):
        """Test that fetch extracts image from Youzan page HTML."""
        fetcher = YouzanFetcher()

        product = Product(
            excel_row=1,
            name="STONE ISLAND Ribbed Soft Cotton",
            spec="BLACK-M",
            brand="STONE_ISLAND",
            product_url="https://shop152506312.m.youzan.com/v2/goods/3eonf4t3mspjk2v"
        )

        # Mock HTML response with og:image meta tag
        mock_html = '''
        <html>
        <head>
            <meta property="og:image" content="https://img.youzan.com/img/product/image.jpg"/>
            <meta name="description" content="Test product description"/>
            <title>Test Product - STONE ISLAND</title>
        </head>
        <body></body>
        </html>
        '''

        mock_response = Mock()
        mock_response.text = mock_html
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        with patch.object(fetcher, "_download_image", return_value="/path/to/image.jpg"):
            result = fetcher.fetch(product)

        assert result == "/path/to/image.jpg"
        assert product.status == "success"

    @patch("img_fetch.fetchers.youzan_fetcher.requests.get")
    def test_fetch_fails_when_no_image_found(self, mock_get):
        """Test that fetch returns None when no image is found."""
        fetcher = YouzanFetcher()

        product = Product(
            excel_row=1,
            name="Test Product",
            spec="BLACK-M",
            product_url="https://shop152506312.m.youzan.com/v2/goods/123"
        )

        mock_html = "<html><head></head><body>No image here</body></html>"
        mock_response = Mock()
        mock_response.text = mock_html
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = fetcher.fetch(product)

        assert result is None
        assert product.status == "failed"
        assert "No image found" in product.error_message

    def test_get_name(self):
        """Test fetcher name for logging."""
        fetcher = YouzanFetcher()
        assert fetcher.get_name() == "YouzanFetcher"


class TestYouzanImageExtraction:
    """Tests for Youzan-specific image extraction patterns."""

    def test_extract_og_image(self):
        """Test extraction of og:image meta tag."""
        html = '''
        <html>
        <head>
            <meta property="og:image" content="https://img.youzan.com/img/product/image.jpg"/>
        </head>
        </html>
        '''

        from img_fetch.fetchers.youzan_fetcher import YouzanFetcher
        fetcher = YouzanFetcher()

        with patch("img_fetch.fetchers.youzan_fetcher.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.text = html
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            image_url = fetcher._find_image_in_html("https://example.com", html)

        assert image_url == "https://img.youzan.com/img/product/image.jpg"

    def test_extract_multiple_og_images_returns_first(self):
        """Test that when multiple og:image tags exist, first is returned."""
        html = '''
        <html>
        <head>
            <meta property="og:image" content="https://img.youzan.com/img/product/image1.jpg"/>
            <meta property="og:image" content="https://img.youzan.com/img/product/image2.jpg"/>
        </head>
        </html>
        '''

        from img_fetch.fetchers.youzan_fetcher import YouzanFetcher
        fetcher = YouzanFetcher()

        image_url = fetcher._find_image_in_html("https://example.com", html)

        assert image_url == "https://img.youzan.com/img/product/image1.jpg"

    def test_extract_img_src_as_fallback(self):
        """Test extraction of img src as fallback when no og:image."""
        html = '''
        <html>
        <head></head>
        <body>
            <img src="https://img.youzan.com/img/product/direct.jpg"/>
        </body>
        </html>
        '''

        from img_fetch.fetchers.youzan_fetcher import YouzanFetcher
        fetcher = YouzanFetcher()

        image_url = fetcher._find_image_in_html("https://example.com", html)

        assert image_url == "https://img.youzan.com/img/product/direct.jpg"

    def test_handle_protocol_relative_urls(self):
        """Test handling of protocol-relative URLs (//example.com/image.jpg)."""
        html = '''
        <html>
        <head>
            <meta property="og:image" content="//img.youzan.com/img/product/image.jpg"/>
        </head>
        </html>
        '''

        from img_fetch.fetchers.youzan_fetcher import YouzanFetcher
        fetcher = YouzanFetcher()

        image_url = fetcher._find_image_in_html("https://example.com", html)

        assert image_url == "https://img.youzan.com/img/product/image.jpg"

    def test_make_relative_urls_absolute(self):
        """Test conversion of relative URLs to absolute."""
        html = '''
        <html>
        <head></head>
        <body>
            <img src="/img/product/image.jpg"/>
        </body>
        </html>
        '''

        from img_fetch.fetchers.youzan_fetcher import YouzanFetcher
        fetcher = YouzanFetcher()

        image_url = fetcher._find_image_in_html("https://shop152506312.m.youzan.com", html)

        assert image_url == "https://shop152506312.m.youzan.com/img/product/image.jpg"