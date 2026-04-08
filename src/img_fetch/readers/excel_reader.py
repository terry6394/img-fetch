"""Excel file reader for product data."""

import logging
from pathlib import Path
from typing import List, Optional

import openpyxl

from img_fetch.core.brand_extractor import extract_brand
from img_fetch.core.product import Product

from .base import BaseReader

logger = logging.getLogger(__name__)


class ExcelReader(BaseReader):
    """Reader for Excel files (.xlsx, .xls)."""

    # Field name mapping from Chinese to English
    FIELD_MAPPING = {
        "商品名称": "name",
        "商品规格": "spec",
        "商品编码": "product_code",
        "规格编码": "spec_code",
        "商品链接": "product_url",
    }

    # Alternative field names (case-insensitive variants)
    ALT_FIELD_MAPPING = {
        "name": "name",
        "spec": "spec",
        "product_code": "product_code",
        "spec_code": "spec_code",
        "product_url": "product_url",
        "productlink": "product_url",
        "link": "product_url",
    }

    def __init__(self):
        """Initialize Excel reader."""
        self._column_map: Optional[dict[str, int]] = None

    def supports(self, source: str) -> bool:
        """Check if this reader supports the given source."""
        path = Path(source)
        return path.suffix.lower() in (".xlsx", ".xls")

    def read(self, source: str) -> List[Product]:
        """
        Read products from an Excel file.

        Args:
            source: Path to Excel file

        Returns:
            List of Product objects
        """
        path = Path(source)
        if not path.exists():
            logger.error(f"Excel file not found: {source}")
            return []

        try:
            workbook = openpyxl.load_workbook(path, data_only=True)
        except Exception as e:
            logger.error(f"Failed to open Excel file {source}: {e}")
            return []

        products = []
        for sheet_name in workbook.sheetnames:
            sheet = workbook[sheet_name]
            products.extend(self._read_sheet(sheet, source))

        workbook.close()
        return products

    def _read_sheet(self, sheet, file_path: str) -> List[Product]:
        """Read products from a single sheet."""
        if sheet.max_row < 2:
            return []

        # Build column map from header row
        self._column_map = self._build_column_map(sheet[1])

        if not self._column_map:
            return []

        products = []
        for row_num in range(2, sheet.max_row + 1):
            row = sheet[row_num]
            product = self._parse_row(row, row_num, file_path)
            if product:
                products.append(product)

        return products

    def _build_column_map(self, header_row) -> dict[str, int]:
        """Build a mapping from field names to column indices."""
        column_map = {}
        for idx, cell in enumerate(header_row):
            if cell.value is None:
                continue
            header = str(cell.value).strip()
            # Check direct mapping
            if header in self.FIELD_MAPPING:
                field = self.FIELD_MAPPING[header]
                column_map[field] = idx
            # Check alternative mapping (case-insensitive)
            elif header.lower() in self.ALT_FIELD_MAPPING:
                field = self.ALT_FIELD_MAPPING[header.lower()]
                column_map[field] = idx
        return column_map

    def _parse_row(self, row, row_num: int, file_path: str) -> Optional[Product]:
        """Parse a single row into a Product object."""
        try:
            # Extract field values
            name = self._get_field_value(row, "name")
            if not name:
                return None

            spec = self._get_field_value(row, "spec")
            product_code = self._get_field_value(row, "product_code", "")
            spec_code = self._get_field_value(row, "spec_code", "")
            product_url = self._get_field_value(row, "product_url", "")

            # Extract brand from name
            brand = extract_brand(name)

            return Product(
                excel_row=row_num,
                name=name,
                spec=spec,
                product_code=product_code,
                spec_code=spec_code,
                product_url=product_url,
                brand=brand,
            )
        except Exception as e:
            logger.warning(f"Failed to parse row {row_num} in {file_path}: {e}")
            return None

    def _get_field_value(
        self, row, field: str, default: str = ""
    ) -> str:
        """Get a field value from a row."""
        if self._column_map is None or field not in self._column_map:
            return default

        idx = self._column_map[field]
        cell = row[idx] if idx < len(row) else None

        if cell is None or cell.value is None:
            return default

        return str(cell.value).strip()
