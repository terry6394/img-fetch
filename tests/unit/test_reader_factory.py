"""Unit tests for ReaderFactory."""

import pytest
import json

from img_fetch.readers.factory import ReaderFactory, get_reader, read_products
from img_fetch.readers.base import BaseReader
from img_fetch.readers.excel_reader import ExcelReader
from img_fetch.readers.csv_reader import CsvReader
from img_fetch.readers.json_reader import JsonReader


@pytest.fixture
def factory():
    """Create a fresh ReaderFactory instance."""
    return ReaderFactory()


class TestReaderFactory:
    """Tests for ReaderFactory class."""

    def test_singleton_pattern(self):
        """Test that get_instance returns the same instance."""
        instance1 = ReaderFactory.get_instance()
        instance2 = ReaderFactory.get_instance()
        assert instance1 is instance2

    def test_discover_readers(self, factory):
        """Test that readers are auto-discovered on initialization."""
        readers = factory.available_readers
        assert "ExcelReader" in readers
        assert "CsvReader" in readers
        assert "JsonReader" in readers

    def test_create_reader_for_xlsx(self, factory):
        """Test creating a reader for .xlsx file."""
        reader = factory.create_reader("products.xlsx")
        assert reader is not None
        assert isinstance(reader, ExcelReader)

    def test_create_reader_for_csv(self, factory):
        """Test creating a reader for .csv file."""
        reader = factory.create_reader("products.csv")
        assert reader is not None
        assert isinstance(reader, CsvReader)

    def test_create_reader_for_json(self, factory):
        """Test creating a reader for .json file."""
        reader = factory.create_reader("products.json")
        assert reader is not None
        assert isinstance(reader, JsonReader)

    def test_create_reader_unsupported_file(self, factory):
        """Test creating a reader for unsupported file type."""
        reader = factory.create_reader("products.txt")
        assert reader is None

    def test_create_reader_caches_result(self, factory):
        """Test that reader creation is cached."""
        reader1 = factory.create_reader("products.xlsx")
        reader2 = factory.create_reader("products.xlsx")
        assert reader1 is reader2

    def test_register_reader(self, factory):
        """Test registering a new reader."""
        class CustomReader(BaseReader):
            def supports(self, source):
                return source.endswith(".custom")

            def read(self, source):
                return []

        factory.register_reader(CustomReader)
        assert "CustomReader" in factory.available_readers

        reader = factory.create_reader("data.custom")
        assert isinstance(reader, CustomReader)


class TestReaderFactoryIntegration:
    """Integration tests for ReaderFactory with actual files."""

    def test_read_xlsx_file(self, factory, tmp_path):
        """Test reading an Excel file through the factory."""
        from openpyxl import Workbook

        wb = Workbook()
        ws = wb.active
        ws.append(["商品名称", "商品规格", "商品编码", "规格编码", "商品链接"])
        ws.append(["HAGLOFS Jacket", "Red", "HJ001", "HJ001-R", "http://example.com"])

        file_path = tmp_path / "products.xlsx"
        wb.save(file_path)
        wb.close()

        products = factory.read(str(file_path))
        assert len(products) == 1
        assert products[0].name == "HAGLOFS Jacket"
        assert products[0].brand == "HAGLOFS"

    def test_read_csv_file(self, factory, tmp_path):
        """Test reading a CSV file through the factory."""
        content = "商品名称,商品规格,商品编码\nHAGLOFS Jacket,Red,HJ001"
        file_path = tmp_path / "products.csv"
        file_path.write_text(content, encoding="utf-8")

        products = factory.read(str(file_path))
        assert len(products) == 1
        assert products[0].name == "HAGLOFS Jacket"

    def test_read_json_file(self, factory, tmp_path):
        """Test reading a JSON file through the factory."""
        data = [{"商品名称": "HAGLOFS Jacket", "商品规格": "Red"}]
        file_path = tmp_path / "products.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

        products = factory.read(str(file_path))
        assert len(products) == 1
        assert products[0].name == "HAGLOFS Jacket"


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_get_reader_function(self, tmp_path):
        """Test the get_reader convenience function."""
        from openpyxl import Workbook

        wb = Workbook()
        ws = wb.active
        ws.append(["商品名称", "商品规格", "商品编码", "规格编码", "商品链接"])
        ws.append(["HAGLOFS Jacket", "Red", "HJ001", "HJ001-R", "http://example.com"])

        file_path = tmp_path / "test.xlsx"
        wb.save(file_path)
        wb.close()

        reader = get_reader(str(file_path))
        assert isinstance(reader, ExcelReader)

    def test_read_products_function(self, tmp_path):
        """Test the read_products convenience function."""
        content = "商品名称,商品规格,商品编码\nSTONE ISLAND Pants,Blue,SP001"
        file_path = tmp_path / "test.csv"
        file_path.write_text(content, encoding="utf-8")

        products = read_products(str(file_path))
        assert len(products) == 1
        assert products[0].name == "STONE ISLAND Pants"
        assert products[0].brand == "STONE_ISLAND"
