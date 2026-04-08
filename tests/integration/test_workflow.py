"""End-to-end integration tests for the img-fetch workflow."""

import json
import csv
import tempfile
from pathlib import Path

import pytest

from img_fetch.main import (
    parse_args,
    load_products,
    workflow,
    _load_from_excel,
    _load_from_csv,
    _load_from_json,
)
from img_fetch.core.product import Product


class TestParseArgs:
    """Test argument parsing."""

    def test_parse_required_args(self):
        """Test parsing only required arguments."""
        args = parse_args(["input.xlsx"])
        assert args.input_file == "input.xlsx"
        assert args.output_dir == "./output"
        assert args.name_field == "name"
        assert args.spec_field == "spec"

    def test_parse_all_args(self):
        """Test parsing all arguments."""
        args = parse_args([
            "input.xlsx",
            "-o", "/custom/output",
            "-b", "brand_col",
            "-n", "product_name",
            "-s", "specification"
        ])
        assert args.input_file == "input.xlsx"
        assert args.output_dir == "/custom/output"
        assert args.brand_field == "brand_col"
        assert args.name_field == "product_name"
        assert args.spec_field == "specification"

    def test_parse_short_flags(self):
        """Test short flag parsing."""
        args = parse_args([
            "input.csv",
            "-o", "/out",
            "-n", "name",
            "-s", "spec"
        ])
        assert args.output_dir == "/out"
        assert args.name_field == "name"
        assert args.spec_field == "spec"


class TestLoadProducts:
    """Test product loading from various file formats."""

    def test_load_from_excel(self, tmp_path):
        """Test loading products from Excel file."""
        import openpyxl

        # Create test Excel file
        xlsx_file = tmp_path / "test.xlsx"
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["name", "spec", "brand"])
        ws.append(["HAGLOFS Alpha Jacket", "BLACK-M", "HAGLOFS"])
        ws.append(["STONE ISLAND Cotton", "RED-L", "STONE_ISLAND"])
        wb.save(xlsx_file)

        # Load products
        products = load_products(str(xlsx_file), "name", "spec", "brand")

        assert len(products) == 2
        assert products[0].name == "HAGLOFS Alpha Jacket"
        assert products[0].spec == "BLACK-M"
        assert products[0].brand == "HAGLOFS"
        assert products[1].name == "STONE ISLAND Cotton"
        assert products[1].spec == "RED-L"
        assert products[1].brand == "STONE_ISLAND"

    def test_load_from_csv(self, tmp_path):
        """Test loading products from CSV file."""
        # Create test CSV file
        csv_file = tmp_path / "test.csv"
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["name", "spec", "brand"])
            writer.writerow(["HAGLOFS Alpha Jacket", "BLACK-M", "HAGLOFS"])
            writer.writerow(["STONE ISLAND Cotton", "RED-L", "STONE_ISLAND"])

        # Load products
        products = load_products(str(csv_file), "name", "spec", "brand")

        assert len(products) == 2
        assert products[0].name == "HAGLOFS Alpha Jacket"
        assert products[0].spec == "BLACK-M"
        assert products[0].brand == "HAGLOFS"

    def test_load_from_json(self, tmp_path):
        """Test loading products from JSON file."""
        # Create test JSON file
        json_file = tmp_path / "test.json"
        data = {
            "products": [
                {"name": "HAGLOFS Alpha Jacket", "spec": "BLACK-M", "brand": "HAGLOFS"},
                {"name": "STONE ISLAND Cotton", "spec": "RED-L", "brand": "STONE_ISLAND"}
            ]
        }
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(data, f)

        # Load products
        products = load_products(str(json_file), "name", "spec", "brand")

        assert len(products) == 2
        assert products[0].name == "HAGLOFS Alpha Jacket"
        assert products[0].brand == "HAGLOFS"

    def test_load_json_array_format(self, tmp_path):
        """Test loading products from JSON array format."""
        json_file = tmp_path / "test.json"
        data = [
            {"name": "HAGLOFS Alpha Jacket", "spec": "BLACK-M"},
            {"name": "STONE ISLAND Cotton", "spec": "RED-L"}
        ]
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(data, f)

        products = load_products(str(json_file), "name", "spec")

        assert len(products) == 2
        # Brand should be auto-detected
        assert products[0].brand == "HAGLOFS"
        assert products[1].brand == "STONE_ISLAND"

    def test_auto_brand_extraction(self, tmp_path):
        """Test that brand is auto-extracted when not provided."""
        csv_file = tmp_path / "test.csv"
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["name", "spec"])
            writer.writerow(["HAGLOFS Alpha Jacket", "BLACK-M"])
            writer.writerow(["STONE ISLAND Cotton", "RED-L"])

        products = load_products(str(csv_file), "name", "spec")

        assert len(products) == 2
        assert products[0].brand == "HAGLOFS"
        assert products[1].brand == "STONE_ISLAND"

    def test_load_with_custom_field_names(self, tmp_path):
        """Test loading with custom field names."""
        csv_file = tmp_path / "test.csv"
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["product_name", "specification"])
            writer.writerow(["HAGLOFS Alpha Jacket", "BLACK-M"])

        products = load_products(
            str(csv_file),
            name_field="product_name",
            spec_field="specification"
        )

        assert len(products) == 1
        assert products[0].name == "HAGLOFS Alpha Jacket"
        assert products[0].spec == "BLACK-M"

    def test_empty_rows_skipped(self, tmp_path):
        """Test that empty rows are skipped."""
        import openpyxl

        xlsx_file = tmp_path / "test.xlsx"
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["name", "spec"])
        ws.append(["HAGLOFS Alpha Jacket", "BLACK-M"])
        ws.append([])  # Empty row
        ws.append(["STONE ISLAND Cotton", "RED-L"])
        wb.save(xlsx_file)

        products = load_products(str(xlsx_file), "name", "spec")

        assert len(products) == 2


class TestWorkflow:
    """Test main workflow orchestration."""

    def test_workflow_basic(self, tmp_path):
        """Test basic workflow execution."""
        # Create test CSV
        csv_file = tmp_path / "products.csv"
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["name", "spec"])
            writer.writerow(["HAGLOFS Alpha Jacket", "BLACK-M"])

        output_dir = tmp_path / "output"
        products = workflow(
            input_file=str(csv_file),
            output_dir=str(output_dir),
            name_field="name",
            spec_field="spec"
        )

        assert len(products) == 1
        assert products[0].status == "success"
        assert "HAGLOFS" in products[0].image_path

    def test_workflow_creates_output_dir(self, tmp_path):
        """Test that workflow creates output directory."""
        csv_file = tmp_path / "products.csv"
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["name", "spec"])
            writer.writerow(["HAGLOFS Alpha Jacket", "BLACK-M"])

        output_dir = tmp_path / "new_output_dir"
        workflow(
            input_file=str(csv_file),
            output_dir=str(output_dir),
            name_field="name",
            spec_field="spec"
        )

        assert output_dir.exists()

    def test_workflow_multiple_products(self, tmp_path):
        """Test workflow with multiple products."""
        csv_file = tmp_path / "products.csv"
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["name", "spec"])
            writer.writerow(["HAGLOFS Alpha Jacket", "BLACK-M"])
            writer.writerow(["STONE ISLAND Cotton", "RED-L"])
            writer.writerow(["CANADA GOOSE Parka", "WHITE-L"])

        output_dir = tmp_path / "output"
        products = workflow(
            input_file=str(csv_file),
            output_dir=str(output_dir),
            name_field="name",
            spec_field="spec"
        )

        assert len(products) == 3
        assert all(p.status == "success" for p in products)
        # Check brands are extracted correctly
        brands = {p.brand for p in products}
        assert "HAGLOFS" in brands
        assert "STONE_ISLAND" in brands
        assert "CANADA_GOOSE" in brands


class TestErrorHandling:
    """Test error handling."""

    def test_unsupported_file_format(self):
        """Test error on unsupported file format."""
        with pytest.raises(ValueError, match="Unsupported file format"):
            load_products("test.txt", "name", "spec")

    def test_missing_field(self, tmp_path):
        """Test error on missing field."""
        csv_file = tmp_path / "test.csv"
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["name", "spec"])
            writer.writerow(["HAGLOFS Alpha Jacket", "BLACK-M"])

        with pytest.raises(ValueError, match="not found"):
            load_products(str(csv_file), "nonexistent_field", "spec")
