"""Unit tests for JsonReader."""

import json
import pytest
from pathlib import Path

from img_fetch.core.product import Product
from img_fetch.readers.json_reader import JsonReader


@pytest.fixture
def json_reader():
    """Create a JsonReader instance."""
    return JsonReader()


@pytest.fixture
def sample_json_file(tmp_path):
    """Create a sample JSON file for testing."""
    data = [
        {
            "商品名称": "HAGLOFS Alpha Jacket",
            "商品规格": "Black/L",
            "商品编码": "HG001",
            "规格编码": "HG001-BL-L",
            "商品链接": "https://haglofs.com/alpha",
        },
        {
            "商品名称": "STONE ISLAND Ribbed Cotton",
            "商品规格": "Navy",
            "商品编码": "SI002",
            "规格编码": "SI002-NV",
            "商品链接": "https://stoneisland.com/ribbed",
        },
        {
            "商品名称": "CANADA GOOSE Expedition Parka",
            "商品规格": "Black",
            "商品编码": "CG003",
            "规格编码": "CG003-BK",
            "商品链接": "",
        },
        {
            "商品名称": "HELLY HANSEN Workwear",
            "商品规格": "",
            "商品编码": "HH005",
            "规格编码": "HH005-WK",
            "商品链接": "https://hellyhansen.com/workwear",
        },
        {
            "商品名称": "",  # Missing name - should be skipped
            "商品规格": "Some spec",
            "商品编码": "XX001",
        },
    ]

    file_path = tmp_path / "products.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

    return str(file_path)


@pytest.fixture
def json_with_wrapped_structure(tmp_path):
    """Create a JSON file with wrapped structure."""
    data = {
        "products": [
            {
                "name": "HAGLOFS Jacket",
                "spec": "Red",
                "product_code": "HJ001",
            },
            {
                "name": "STONE ISLAND Pants",
                "spec": "Blue",
                "product_code": "SP002",
            },
        ]
    }

    file_path = tmp_path / "wrapped.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

    return str(file_path)


@pytest.fixture
def json_with_english_keys(tmp_path):
    """Create a JSON file with English keys."""
    data = [
        {
            "name": "HAGLOFS Jacket",
            "spec": "Green",
            "product_code": "HJ003",
            "spec_code": "HJ003-G",
            "product_url": "http://example.com",
        }
    ]

    file_path = tmp_path / "english_keys.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

    return str(file_path)


class TestJsonReader:
    """Tests for JsonReader class."""

    def test_supports_json(self, json_reader):
        """Test that JsonReader supports .json files."""
        assert json_reader.supports("products.json") is True
        assert json_reader.supports("data.JSON") is True

    def test_supports_non_json(self, json_reader):
        """Test that JsonReader does not support non-JSON files."""
        assert json_reader.supports("products.xlsx") is False
        assert json_reader.supports("products.csv") is False
        assert json_reader.supports("products.txt") is False

    def test_read_json_file(self, json_reader, sample_json_file):
        """Test reading products from a JSON file."""
        products = json_reader.read(sample_json_file)

        assert len(products) == 4  # 5 items minus 1 with missing name

        # Check first product
        assert products[0].name == "HAGLOFS Alpha Jacket"
        assert products[0].spec == "Black/L"
        assert products[0].product_code == "HG001"
        assert products[0].spec_code == "HG001-BL-L"
        assert products[0].product_url == "https://haglofs.com/alpha"
        assert products[0].brand == "HAGLOFS"
        assert products[0].excel_row == 2  # Row 2 (index 1 + header offset)

        # Check second product
        assert products[1].name == "STONE ISLAND Ribbed Cotton"
        assert products[1].spec == "Navy"
        assert products[1].brand == "STONE_ISLAND"

        # Check third product (CANADA GOOSE with empty URL)
        assert products[2].name == "CANADA GOOSE Expedition Parka"
        assert products[2].product_url == ""
        assert products[2].brand == "CANADA_GOOSE"

        # Check fourth product (HELLY HANSEN with empty spec)
        assert products[3].name == "HELLY HANSEN Workwear"
        assert products[3].spec == ""
        assert products[3].brand == "HELLY_HANSEN"

    def test_read_nonexistent_file(self, json_reader):
        """Test reading a non-existent file returns empty list."""
        products = json_reader.read("nonexistent.json")
        assert products == []

    def test_brand_extraction(self, json_reader, sample_json_file):
        """Test that brand is correctly extracted from product name."""
        products = json_reader.read(sample_json_file)

        brands = [p.brand for p in products]
        assert "HAGLOFS" in brands
        assert "STONE_ISLAND" in brands
        assert "CANADA_GOOSE" in brands
        assert "HELLY_HANSEN" in brands

    def test_wrapped_structure(self, json_reader, json_with_wrapped_structure):
        """Test reading JSON with wrapped structure ({"products": [...]})."""
        products = json_reader.read(json_with_wrapped_structure)

        assert len(products) == 2
        assert products[0].name == "HAGLOFS Jacket"
        assert products[1].name == "STONE ISLAND Pants"

    def test_english_keys(self, json_reader, json_with_english_keys):
        """Test reading JSON with English keys."""
        products = json_reader.read(json_with_english_keys)

        assert len(products) == 1
        assert products[0].name == "HAGLOFS Jacket"
        assert products[0].spec == "Green"
        assert products[0].product_code == "HJ003"
        assert products[0].spec_code == "HJ003-G"
        assert products[0].product_url == "http://example.com"


class TestJsonReaderEdgeCases:
    """Tests for JsonReader edge cases."""

    def test_empty_json_array(self, json_reader, tmp_path):
        """Test reading a JSON file with empty array."""
        file_path = tmp_path / "empty.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump([], f)

        products = json_reader.read(str(file_path))
        assert products == []

    def test_single_object(self, json_reader, tmp_path):
        """Test reading a JSON file with single object (not array)."""
        data = {
            "商品名称": "HAGLOFS Jacket",
            "商品规格": "Red",
            "商品编码": "HJ001",
        }

        file_path = tmp_path / "single_object.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

        products = json_reader.read(str(file_path))
        assert len(products) == 1
        assert products[0].name == "HAGLOFS Jacket"

    def test_invalid_json(self, json_reader, tmp_path):
        """Test reading an invalid JSON file returns empty list."""
        file_path = tmp_path / "invalid.json"
        file_path.write_text("{not valid json}", encoding="utf-8")

        products = json_reader.read(str(file_path))
        assert products == []

    def test_missing_fields(self, json_reader, tmp_path):
        """Test handling of missing fields."""
        data = [
            {"商品名称": "HAGLOFS Jacket", "商品规格": "Red"},
            {"商品名称": "NIKE Sneaker"},  # Missing spec
            {"spec": "Blue"},  # Missing name - should be skipped
        ]

        file_path = tmp_path / "missing_fields.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

        products = json_reader.read(str(file_path))
        assert len(products) == 2
        assert products[0].spec == "Red"
        assert products[1].spec == ""  # Missing spec defaults to empty
