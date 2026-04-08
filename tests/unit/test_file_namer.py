"""Unit tests for file_namer module."""

import pytest
from pathlib import Path

from img_fetch.core.file_namer import (
    normalize_filename,
    _normalize_part,
    get_image_path,
    is_safe_filename,
    sanitize_filename,
)


class TestNormalizeFilename:
    """Tests for normalize_filename function."""

    def test_basic_filename(self):
        """Test basic filename generation."""
        result = normalize_filename("Ribbed Soft Cotton", "BLACK-M", "STONE_ISLAND")
        assert result == "STONE_ISLAND_RIBBED_SOFT_COTTON_BLACK-M.jpg"

    def test_without_brand(self):
        """Test filename without brand uses just name and spec."""
        result = normalize_filename("Alpha Jacket", "RED-L")
        assert result == "ALPHA_JACKET_RED-L.jpg"

    def test_without_spec(self):
        """Test filename without spec."""
        result = normalize_filename("Soft Cotton", "", "HAGLOFS")
        assert result == "HAGLOFS_SOFT_COTTON.jpg"

    def test_spec_with_leading_hyphen(self):
        """Test spec with leading hyphen is handled."""
        result = normalize_filename("Jacket", "-BLACK-M", "HAGLOFS")
        assert result == "HAGLOFS_JACKET_BLACK-M.jpg"

    def test_uppercase_conversion(self):
        """Test all parts are converted to uppercase."""
        result = normalize_filename("Soft Cotton", "black-m", "stone_island")
        assert result == "STONE_ISLAND_SOFT_COTTON_BLACK-M.jpg"

    def test_special_characters_replaced(self):
        """Test special characters are replaced with underscores."""
        result = normalize_filename("Alpha/Jacket", "RED-L", "HAGLOFS")
        assert result == "HAGLOFS_ALPHA_JACKET_RED-L.jpg"

    def test_multiple_spaces(self):
        """Test multiple spaces are collapsed."""
        result = normalize_filename("Alpha    Jacket", "RED-L", "HAGLOFS")
        assert result == "HAGLOFS_ALPHA_JACKET_RED-L.jpg"

    def test_empty_inputs(self):
        """Test handling of empty inputs."""
        result = normalize_filename("", "", "")
        assert result == ".jpg"  # Just extension

    def test_filename_length_limit(self):
        """Test filename is truncated if too long."""
        long_name = "A" * 300
        result = normalize_filename(long_name, "SPEC", "BRAND")
        assert len(result) <= 200


class TestNormalizePart:
    """Tests for _normalize_part internal function."""

    def test_basic(self):
        """Test basic normalization."""
        assert _normalize_part("Hello World") == "HELLO_WORLD"
        assert _normalize_part("Test") == "TEST"

    def test_uppercase(self):
        """Test uppercase conversion."""
        assert _normalize_part("hello") == "HELLO"
        assert _normalize_part("HeLLo") == "HELLO"

    def test_special_characters(self):
        """Test special character handling."""
        assert _normalize_part("Jack/Jacket") == "JACK_JACKET"
        assert _normalize_part("Jack*Jacket") == "JACK_JACKET"

    def test_multiple_underscores(self):
        """Test multiple underscores are collapsed."""
        assert _normalize_part("Alpha__Jacket") == "ALPHA_JACKET"
        assert _normalize_part("A__B__C") == "A_B_C"

    def test_leading_trailing_underscores(self):
        """Test leading and trailing underscores are removed."""
        assert _normalize_part("_Alpha_") == "ALPHA"
        assert _normalize_part("  Alpha  ") == "ALPHA"

    def test_empty(self):
        """Test empty string returns empty."""
        assert _normalize_part("") == ""
        assert _normalize_part("   ") == ""


class TestGetImagePath:
    """Tests for get_image_path function."""

    def test_basic_path(self, tmp_path):
        """Test basic path generation."""
        path = get_image_path("STONE_ISLAND", "STONE_ISLAND_COTTON.jpg", tmp_path)
        assert path == tmp_path / "STONE_ISLAND" / "STONE_ISLAND_COTTON.jpg"

    def test_brand_directory_created(self, tmp_path):
        """Test brand directory is created."""
        path = get_image_path("HAGLOFS", "HAGLOFS_JACKET.jpg", tmp_path)
        assert path.parent.exists()
        assert path.parent.is_dir()

    def test_default_output_dir(self):
        """Test default output directory is used."""
        from img_fetch.config import IMAGES_DIR
        path = get_image_path("BRAND", "file.jpg")
        assert path.parent == IMAGES_DIR / "BRAND"


class TestIsSafeFilename:
    """Tests for is_safe_filename function."""

    def test_valid_filenames(self):
        """Test valid filenames."""
        assert is_safe_filename("image.jpg") is True
        assert is_safe_filename("STONE_ISLAND_COTTON.jpg") is True
        assert is_safe_filename("HAGLOFS-Alpha-Jacket.jpg") is True

    def test_forbidden_characters(self):
        """Test filenames with forbidden characters are rejected."""
        assert is_safe_filename("file:name.jpg") is False
        assert is_safe_filename("file/name.jpg") is False
        assert is_safe_filename("file<name.jpg") is False

    def test_path_traversal(self):
        """Test path traversal attempts are rejected."""
        assert is_safe_filename("../file.jpg") is False
        assert is_safe_filename("/etc/passwd") is False
        assert is_safe_filename("file../../etc/passwd") is False

    def test_windows_reserved_names(self):
        """Test Windows reserved names are rejected."""
        assert is_safe_filename("CON.jpg") is False
        assert is_safe_filename("PRN.txt") is False
        assert is_safe_filename("AUX") is False

    def test_leading_trailing_whitespace(self):
        """Test whitespace handling."""
        assert is_safe_filename(" file.jpg") is False
        assert is_safe_filename("file.jpg ") is False


class TestSanitizeFilename:
    """Tests for sanitize_filename function."""

    def test_basic_sanitization(self):
        """Test basic filename sanitization."""
        assert sanitize_filename("image.jpg") == "image.jpg"
        assert sanitize_filename("STONE_ISLAND_COTTON.jpg") == "STONE_ISLAND_COTTON.jpg"

    def test_forbidden_characters(self):
        """Test forbidden characters are replaced."""
        assert sanitize_filename("file:name.jpg") == "file_name.jpg"
        assert sanitize_filename("file<name.jpg") == "file_name.jpg"

    def test_path_traversal(self):
        """Test path traversal is removed."""
        assert sanitize_filename("../file.jpg") == "file.jpg"
        assert sanitize_filename("/etc/passwd") == "etc_passwd"

    def test_empty_input(self):
        """Test empty input returns unnamed."""
        assert sanitize_filename("") == "unnamed"
        assert sanitize_filename("   ") == "unnamed"
