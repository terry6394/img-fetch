"""Unit tests for brand_extractor module."""

import pytest

from img_fetch.core.brand_extractor import (
    extract_brand,
    normalize_brand,
    extract_brand_from_url,
    BRAND_PREFIX_MAP,
)


class TestExtractBrand:
    """Tests for extract_brand function."""

    def test_stone_island(self):
        """Test STONE ISLAND brand extraction."""
        assert extract_brand("STONE ISLAND Ribbed Soft Cotton") == "STONE_ISLAND"
        assert extract_brand("Stone Island Jacket") == "STONE_ISLAND"
        assert extract_brand("STONE island Cap") == "STONE_ISLAND"

    def test_canada_goose(self):
        """Test CANADA GOOSE brand extraction."""
        assert extract_brand("CANADA GOOSE Expedition Parka") == "CANADA_GOOSE"
        assert extract_brand("Canada Goose Chilliwack") == "CANADA_GOOSE"
        assert extract_brand("canada goose bomber") == "CANADA_GOOSE"

    def test_haglofs(self):
        """Test HAGLOFS brand extraction."""
        assert extract_brand("HAGLOFS Alpha Jacket") == "HAGLOFS"
        assert extract_brand("Haglofs Rugged Pants") == "HAGLOFS"

    def test_helly_hansen(self):
        """Test HELLY HANSEN brand extraction."""
        assert extract_brand("HELLY HANSEN Workwear") == "HELLY_HANSEN"
        assert extract_brand("Helly Hansen Snaefell") == "HELLY_HANSEN"

    def test_lim(self):
        """Test L.I.M brand extraction."""
        assert extract_brand("L.I.M Tech Lite") == "L.I.M"
        assert extract_brand("L.I.M Fleece") == "L.I.M"

    def test_unknown_brand(self):
        """Test unknown brand returns normalized first word."""
        assert extract_brand("NIKE Air Max") == "NIKE"
        assert extract_brand("adidas Ultraboost") == "ADIDAS"
        assert extract_brand("Unknown Brand Product") == "UNKNOWN"

    def test_empty_input(self):
        """Test empty input returns empty string."""
        assert extract_brand("") == ""
        assert extract_brand("   ") == ""
        assert extract_brand(None) == ""  # type: ignore

    def test_single_word_product(self):
        """Test single word product name."""
        assert extract_brand("HAGLOFS") == "HAGLOFS"
        assert extract_brand("JACKET") == "JACKET"

    def test_brand_prefix_map_completeness(self):
        """Test all brands in prefix map are detected."""
        for prefix, full_name in BRAND_PREFIX_MAP.items():
            product_name = f"{prefix} Some Product"
            result = extract_brand(product_name)
            assert result == full_name, f"Failed for {prefix}"


class TestNormalizeBrand:
    """Tests for normalize_brand function."""

    def test_basic_normalization(self):
        """Test basic brand normalization."""
        assert normalize_brand("CANADA_GOOSE") == "CANADA_GOOSE"
        assert normalize_brand("Stone Island") == "STONE_ISLAND"

    def test_case_conversion(self):
        """Test uppercase conversion."""
        assert normalize_brand("helly hansen") == "HELLY_HANSEN"
        assert normalize_brand("HaGlOfS") == "HAGLOFS"

    def test_whitespace_handling(self):
        """Test whitespace handling."""
        assert normalize_brand("  STONE ISLAND  ") == "STONE_ISLAND"
        assert normalize_brand("HAGLOFS    JACKET") == "HAGLOFS_JACKET"

    def test_special_characters(self):
        """Test special character handling."""
        assert normalize_brand("BRAND-NAME") == "BRAND-NAME"
        assert normalize_brand("BRAND.NAME") == "BRAND.NAME"

    def test_empty_input(self):
        """Test empty input returns empty string."""
        assert normalize_brand("") == ""
        assert normalize_brand("   ") == ""


class TestExtractBrandFromUrl:
    """Tests for extract_brand_from_url function."""

    def test_canada_goose_url(self):
        """Test brand extraction from Canada Goose URL."""
        url = "https://www.canadagoose.com/expedition-parka"
        assert extract_brand_from_url(url) == "CANADA_GOOSE"

    def test_haglofs_url(self):
        """Test brand extraction from HAGLOFS URL."""
        url = "https://www.haglofs.com/alpha-jacket"
        assert extract_brand_from_url(url) == "HAGLOFS"

    def test_stone_island_url(self):
        """Test brand extraction from Stone Island URL."""
        url = "https://www.stoneisland.com/ribbed-cotton"
        assert extract_brand_from_url(url) == "STONE_ISLAND"

    def test_youzan_url(self):
        """Test that youzan URL returns None."""
        url = "https://shop152506312.m.youzan.com/v2/goods/3eonf4t3mspjk2v"
        assert extract_brand_from_url(url) is None

    def test_unknown_domain(self):
        """Test unknown domain returns None."""
        url = "https://www.unknownsite.com/product"
        assert extract_brand_from_url(url) is None

    def test_empty_url(self):
        """Test empty URL returns None."""
        assert extract_brand_from_url("") is None
        assert extract_brand_from_url(None) is None  # type: ignore
