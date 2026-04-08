"""Unit tests for CsvReader."""

import pytest
from pathlib import Path

from img_fetch.core.product import Product
from img_fetch.readers.csv_reader import CsvReader


@pytest.fixture
def csv_reader():
    """Create a CsvReader instance."""
    return CsvReader()


@pytest.fixture
def sample_csv_file(tmp_path):
    """Create a sample CSV file for testing."""
    content = """商品名称,商品规格,商品编码,规格编码,商品链接
HAGLOFS Alpha Jacket,Black/L,HG001,HG001-BL-L,https://haglofs.com/alpha
STONE ISLAND Ribbed Cotton,Navy,SI002,SI002-NV,https://stoneisland.com/ribbed
CANADA GOOSE Expedition Parka,Black,CG003,CG003-BK,
HELLY HANSEN Workwear,,HH005,HH005-WK,https://hellyhansen.com/workwear
,Missing Name,HG004,HG004-BL-L,"""

    file_path = tmp_path / "products.csv"
    file_path.write_text(content, encoding="utf-8-sig")
    return str(file_path)


@pytest.fixture
def csv_with_english_headers(tmp_path):
    """Create a CSV file with English headers."""
    content = """name,spec,product_code,spec_code,product_url
HAGLOFS Jacket,Red,HJ001,HJ001-R,http://example.com
STONE ISLAND Pants,Blue,SP002,SP002-B,http://example.com/2"""

    file_path = tmp_path / "english_headers.csv"
    file_path.write_text(content, encoding="utf-8")
    return str(file_path)


class TestCsvReader:
    """Tests for CsvReader class."""

    def test_supports_csv(self, csv_reader):
        """Test that CsvReader supports .csv files."""
        assert csv_reader.supports("products.csv") is True
        assert csv_reader.supports("data.CSV") is True

    def test_supports_non_csv(self, csv_reader):
        """Test that CsvReader does not support non-CSV files."""
        assert csv_reader.supports("products.xlsx") is False
        assert csv_reader.supports("products.json") is False
        assert csv_reader.supports("products.txt") is False
        assert csv_reader.supports("products.tsv") is False

    def test_read_csv_file(self, csv_reader, sample_csv_file):
        """Test reading products from a CSV file."""
        products = csv_reader.read(sample_csv_file)

        assert len(products) == 4  # 5 rows minus 1 with missing name

        # Check first product
        assert products[0].name == "HAGLOFS Alpha Jacket"
        assert products[0].spec == "Black/L"
        assert products[0].product_code == "HG001"
        assert products[0].spec_code == "HG001-BL-L"
        assert products[0].product_url == "https://haglofs.com/alpha"
        assert products[0].brand == "HAGLOFS"
        assert products[0].excel_row == 2  # Row 2 (after header)

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

    def test_read_nonexistent_file(self, csv_reader):
        """Test reading a non-existent file returns empty list."""
        products = csv_reader.read("nonexistent.csv")
        assert products == []

    def test_brand_extraction(self, csv_reader, sample_csv_file):
        """Test that brand is correctly extracted from product name."""
        products = csv_reader.read(sample_csv_file)

        brands = [p.brand for p in products]
        assert "HAGLOFS" in brands
        assert "STONE_ISLAND" in brands
        assert "CANADA_GOOSE" in brands
        assert "HELLY_HANSEN" in brands

    def test_excel_row_tracking(self, csv_reader, sample_csv_file):
        """Test that excel_row is correctly set for each product."""
        products = csv_reader.read(sample_csv_file)

        # First data row is row 2 (after header)
        assert products[0].excel_row == 2
        assert products[1].excel_row == 3
        assert products[2].excel_row == 4
        assert products[3].excel_row == 6  # Skipped row 5 due to missing name

    def test_english_headers(self, csv_reader, csv_with_english_headers):
        """Test that English headers are correctly mapped."""
        products = csv_reader.read(csv_with_english_headers)

        assert len(products) == 2
        assert products[0].name == "HAGLOFS Jacket"
        assert products[0].spec == "Red"
        assert products[0].product_code == "HJ001"
        assert products[1].name == "STONE ISLAND Pants"
        assert products[1].spec == "Blue"


class TestCsvReaderEdgeCases:
    """Tests for CsvReader edge cases."""

    def test_empty_csv_file(self, csv_reader, tmp_path):
        """Test reading an empty CSV file."""
        file_path = tmp_path / "empty.csv"
        file_path.write_text("", encoding="utf-8")

        products = csv_reader.read(str(file_path))
        assert products == []

    def test_csv_with_only_header(self, csv_reader, tmp_path):
        """Test CSV with only header row."""
        file_path = tmp_path / "header_only.csv"
        file_path.write_text("商品名称,商品规格\n", encoding="utf-8")

        products = csv_reader.read(str(file_path))
        assert products == []

    def test_missing_fields(self, csv_reader, tmp_path):
        """Test handling of missing fields in some rows."""
        content = """商品名称,商品规格,商品编码
HAGLOFS Jacket,Red,HG001
NIKE Sneaker,,NK001
ADIDAS Shoes,Blue"""

        file_path = tmp_path / "missing_fields.csv"
        file_path.write_text(content, encoding="utf-8")

        products = csv_reader.read(str(file_path))
        assert len(products) == 3
        assert products[0].spec == "Red"
        assert products[1].spec == ""  # Empty spec
        assert products[2].product_code == ""  # Missing product code
