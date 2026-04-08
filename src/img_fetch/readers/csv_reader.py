"""CSV file reader for product data."""

import csv
import logging
from pathlib import Path
from typing import List, Optional

from img_fetch.core.brand_extractor import extract_brand
from img_fetch.core.product import Product

from .base import BaseReader

logger = logging.getLogger(__name__)


class CsvReader(BaseReader):
    """Reader for CSV files."""

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
        """Initialize CSV reader."""
        self._field_map: Optional[dict[str, int]] = None

    def supports(self, source: str) -> bool:
        """Check if this reader supports the given source."""
        path = Path(source)
        return path.suffix.lower() == ".csv"

    def read(self, source: str) -> List[Product]:
        """
        Read products from a CSV file.

        Args:
            source: Path to CSV file

        Returns:
            List of Product objects
        """
        path = Path(source)
        if not path.exists():
            logger.error(f"CSV file not found: {source}")
            return []

        products = []
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                reader = csv.reader(f)
                # Read header row
                try:
                    header = next(reader)
                except StopIteration:
                    logger.warning(f"Empty CSV file: {source}")
                    return []

                self._field_map = self._build_field_map(header)

                if not self._field_map:
                    logger.warning(f"No matching fields found in CSV header: {source}")
                    return []

                # Read data rows
                for row_num, row in enumerate(reader, start=2):
                    product = self._parse_row(row, row_num, source)
                    if product:
                        products.append(product)

        except Exception as e:
            logger.error(f"Failed to read CSV file {source}: {e}")
            return []

        return products

    def _build_field_map(self, header: list[str]) -> dict[str, int]:
        """Build a mapping from field names to column indices."""
        field_map = {}
        for idx, col_name in enumerate(header):
            if col_name is None:
                continue
            col_name = col_name.strip()
            # Check direct mapping
            if col_name in self.FIELD_MAPPING:
                field = self.FIELD_MAPPING[col_name]
                field_map[field] = idx
            # Check alternative mapping (case-insensitive)
            elif col_name.lower() in self.ALT_FIELD_MAPPING:
                field = self.ALT_FIELD_MAPPING[col_name.lower()]
                field_map[field] = idx
        return field_map

    def _parse_row(self, row: list[str], row_num: int, file_path: str) -> Optional[Product]:
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
        self, row: list[str], field: str, default: str = ""
    ) -> str:
        """Get a field value from a row."""
        if self._field_map is None or field not in self._field_map:
            return default

        idx = self._field_map[field]
        if idx >= len(row):
            return default

        value = row[idx]
        if value is None:
            return default

        return str(value).strip()
