"""JSON file reader for product data."""

import json
import logging
from pathlib import Path
from typing import Any, List, Optional

from img_fetch.core.brand_extractor import extract_brand
from img_fetch.core.product import Product

from .base import BaseReader

logger = logging.getLogger(__name__)


class JsonReader(BaseReader):
    """Reader for JSON files."""

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
        "url": "product_url",
    }

    def supports(self, source: str) -> bool:
        """Check if this reader supports the given source."""
        path = Path(source)
        return path.suffix.lower() == ".json"

    def read(self, source: str) -> List[Product]:
        """
        Read products from a JSON file.

        Args:
            source: Path to JSON file

        Returns:
            List of Product objects
        """
        path = Path(source)
        if not path.exists():
            logger.error(f"JSON file not found: {source}")
            return []

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            logger.error(f"Failed to read JSON file {source}: {e}")
            return []

        return self._parse_data(data, source)

    def _parse_data(self, data: Any, file_path: str) -> List[Product]:
        """Parse JSON data into Product objects."""
        products = []

        # Handle different JSON structures
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            # Common patterns: {"products": [...]}, {"data": [...]}, {"items": [...]}
            items = data.get("products") or data.get("data") or data.get("items") or [data]
        else:
            logger.warning(f"Unexpected JSON structure in {file_path}")
            return []

        if not isinstance(items, list):
            items = [items]

        for idx, item in enumerate(items, start=2):
            if not isinstance(item, dict):
                continue
            product = self._parse_item(item, idx, file_path)
            if product:
                products.append(product)

        return products

    def _parse_item(self, item: dict[str, Any], row_num: int, file_path: str) -> Optional[Product]:
        """Parse a single item into a Product object."""
        try:
            # Extract field values using various possible keys
            name = self._get_field_value(item, "name")
            if not name:
                return None

            spec = self._get_field_value(item, "spec")
            product_code = self._get_field_value(item, "product_code", "")
            spec_code = self._get_field_value(item, "spec_code", "")
            product_url = self._get_field_value(item, "product_url", "")

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
            logger.warning(f"Failed to parse item at row {row_num} in {file_path}: {e}")
            return None

    def _get_field_value(
        self, item: dict[str, Any], field: str, default: str = ""
    ) -> str:
        """Get a field value from an item, checking all possible keys."""
        # Check direct key in field mapping
        for source_key, target_field in {**self.FIELD_MAPPING, **self.ALT_FIELD_MAPPING}.items():
            if target_field == field and source_key in item:
                value = item[source_key]
                if value is not None:
                    return str(value).strip()

        # Check alternative keys directly
        alt_keys = [
            field,
            field.replace("_", ""),
            field.replace("_", " "),
        ]
        for key in alt_keys:
            if key in item and item[key] is not None:
                return str(item[key]).strip()

        return default
