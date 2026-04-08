"""Tests for page metadata extraction."""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from img_fetch.core.product import Product
from img_fetch.fetchers.youzan_fetcher import YouzanFetcher


class TestPageMetadataExtraction:
    """Tests for page metadata extraction from HTML."""

    def test_extract_title(self):
        """Test extraction of page title."""
        html = '''
        <html>
        <head>
            <title>STONE ISLAND Ribbed Soft Cotton - Black/M</title>
        </head>
        <body></body>
        </html>
        '''

        fetcher = YouzanFetcher()
        metadata = fetcher._extract_page_metadata("https://example.com", html)

        assert metadata["title"] == "STONE ISLAND Ribbed Soft Cotton - Black/M"

    def test_extract_description(self):
        """Test extraction of meta description."""
        html = '''
        <html>
        <head>
            <meta name="description" content="Premium cotton product from STONE ISLAND. Perfect for casual wear."/>
        </head>
        <body></body>
        </html>
        '''

        fetcher = YouzanFetcher()
        metadata = fetcher._extract_page_metadata("https://example.com", html)

        assert metadata["description"] == "Premium cotton product from STONE ISLAND. Perfect for casual wear."

    def test_extract_keywords(self):
        """Test extraction of meta keywords."""
        html = '''
        <html>
        <head>
            <meta name="keywords" content="stone island, cotton, premium, jacket"/>
        </head>
        <body></body>
        </html>
        '''

        fetcher = YouzanFetcher()
        metadata = fetcher._extract_page_metadata("https://example.com", html)

        assert metadata["keywords"] == ["stone island", "cotton", "premium", "jacket"]

    def test_extract_alt_text(self):
        """Test extraction of alt text from images."""
        html = '''
        <html>
        <head></head>
        <body>
            <img src="image1.jpg" alt="Product front view"/>
            <img src="image2.jpg" alt="Product back view"/>
            <img src="image3.jpg" alt=""/>
        </body>
        </html>
        '''

        fetcher = YouzanFetcher()
        metadata = fetcher._extract_page_metadata("https://example.com", html)

        assert "Product front view" in metadata["alt_text"]
        assert "Product back view" in metadata["alt_text"]
        assert len(metadata["alt_text"]) == 2  # Empty alt should not be included

    def test_extract_all_metadata(self):
        """Test extraction of all metadata fields together."""
        html = '''
        <html>
        <head>
            <title>Test Product</title>
            <meta name="description" content="Test description"/>
            <meta name="keywords" content="test, product"/>
        </head>
        <body>
            <img src="test.jpg" alt="Test alt"/>
        </body>
        </html>
        '''

        fetcher = YouzanFetcher()
        metadata = fetcher._extract_page_metadata("https://example.com", html)

        assert metadata["title"] == "Test Product"
        assert metadata["description"] == "Test description"
        assert metadata["keywords"] == ["test", "product"]
        assert metadata["alt_text"] == ["Test alt"]

    def test_missing_metadata_returns_defaults(self):
        """Test that missing metadata returns empty/default values."""
        html = '<html><head></head><body></body></html>'

        fetcher = YouzanFetcher()
        metadata = fetcher._extract_page_metadata("https://example.com", html)

        assert metadata["title"] == ""
        assert metadata["description"] == ""
        assert metadata["keywords"] == []
        assert metadata["alt_text"] == []


class TestImageUrlResolution:
    """Tests for URL resolution (relative to absolute)."""

    def test_resolve_protocol_relative_url(self):
        """Test resolving protocol-relative URL."""
        fetcher = YouzanFetcher()

        result = fetcher._resolve_url("https://example.com", "//img.youzan.com/image.jpg")
        assert result == "https://img.youzan.com/image.jpg"

    def test_resolve_absolute_url_unchanged(self):
        """Test that absolute URLs are unchanged."""
        fetcher = YouzanFetcher()

        result = fetcher._resolve_url("https://example.com", "https://img.youzan.com/image.jpg")
        assert result == "https://img.youzan.com/image.jpg"

    def test_resolve_relative_url(self):
        """Test resolving relative URL."""
        fetcher = YouzanFetcher()

        result = fetcher._resolve_url("https://shop152506312.m.youzan.com", "/img/product/image.jpg")
        assert result == "https://shop152506312.m.youzan.com/img/product/image.jpg"

    def test_resolve_empty_url(self):
        """Test that empty URL returns empty."""
        fetcher = YouzanFetcher()

        result = fetcher._resolve_url("https://example.com", "")
        assert result == ""

    def test_resolve_root_relative_url(self):
        """Test resolving root-relative URL."""
        fetcher = YouzanFetcher()

        result = fetcher._resolve_url("https://shop152506312.m.youzan.com/v2/goods/123", "../image.jpg")
        assert result == "https://shop152506312.m.youzan.com/v2/image.jpg"


class TestValidProductImage:
    """Tests for product image validation."""

    def test_reject_icon_urls(self):
        """Test that icon URLs are rejected."""
        fetcher = YouzanFetcher()

        assert fetcher._is_valid_product_image("/icons/icon.jpg") is False
        assert fetcher._is_valid_product_image("https://cdn.youzan.com/logo.png") is False
        assert fetcher._is_valid_product_image("/images/sprite.png") is False

    def test_accept_product_urls(self):
        """Test that product URLs are accepted."""
        fetcher = YouzanFetcher()

        assert fetcher._is_valid_product_image("/product/12345.jpg") is True
        assert fetcher._is_valid_product_image("/goods/image.jpg") is True
        assert fetcher._is_valid_product_image("/item/456.jpg") is True

    def test_accept_upload_urls(self):
        """Test that upload URLs are accepted."""
        fetcher = YouzanFetcher()

        assert fetcher._is_valid_product_image("/upload/2024/01/image.jpg") is True
        assert fetcher._is_valid_product_image("https://img.yzcdn.com/image.jpg") is True

    def test_accept_urls_with_product_patterns(self):
        """Test that URLs with product/upload patterns are accepted."""
        fetcher = YouzanFetcher()

        # These have product-like patterns, so they should be accepted
        assert fetcher._is_valid_product_image("/some/random/path/image.jpg") is True