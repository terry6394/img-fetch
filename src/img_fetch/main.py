"""Slash command handler for /img-fetch."""

import argparse
import sys
from pathlib import Path
from typing import Optional

from img_fetch.core.product import Product
from img_fetch.core.brand_extractor import extract_brand
from img_fetch.core.file_namer import normalize_filename, get_image_path
from img_fetch.config import OUTPUT_DIR, IMAGES_DIR


def parse_args(args: Optional[list[str]] = None) -> argparse.Namespace:
    """Parse command arguments."""
    parser = argparse.ArgumentParser(
        prog="img-fetch",
        description="Fetch product images from Excel/CSV/JSON files"
    )
    parser.add_argument(
        "input_file",
        type=str,
        help="Input file path (Excel/CSV/JSON)"
    )
    parser.add_argument(
        "-o", "--output-dir",
        type=str,
        default="./output",
        help="Output directory path (default: ./output)"
    )
    parser.add_argument(
        "-b", "--brand-field",
        type=str,
        default=None,
        help="Brand field name (optional, auto-detected from product name)"
    )
    parser.add_argument(
        "-n", "--name-field",
        type=str,
        default="name",
        help="Product name field name (default: name)"
    )
    parser.add_argument(
        "-s", "--spec-field",
        type=str,
        default="spec",
        help="Product spec field name (default: spec)"
    )
    return parser.parse_args(args)


def load_products(
    input_file: str,
    name_field: str = "name",
    spec_field: str = "spec",
    brand_field: Optional[str] = None
) -> list[Product]:
    """
    Load products from input file.

    Args:
        input_file: Path to input file (Excel/CSV/JSON)
        name_field: Field name for product name
        spec_field: Field name for product spec
        brand_field: Field name for brand (optional)

    Returns:
        List of Product objects
    """
    path = Path(input_file)
    suffix = path.suffix.lower()

    products: list[Product] = []

    if suffix == ".xlsx" or suffix == ".xls":
        products = _load_from_excel(path, name_field, spec_field, brand_field)
    elif suffix == ".csv":
        products = _load_from_csv(path, name_field, spec_field, brand_field)
    elif suffix == ".json":
        products = _load_from_json(path, name_field, spec_field, brand_field)
    else:
        raise ValueError(f"Unsupported file format: {suffix}")

    return products


def _load_from_excel(
    path: Path,
    name_field: str,
    spec_field: str,
    brand_field: Optional[str]
) -> list[Product]:
    """Load products from Excel file."""
    import openpyxl

    products: list[Product] = []
    wb = openpyxl.load_workbook(path)
    ws = wb.active

    # Get header row
    headers = [cell.value for cell in ws[1]]
    if not headers:
        raise ValueError("Excel file has no headers")

    # Find column indices
    name_idx = _find_column_index(headers, name_field)
    spec_idx = _find_column_index(headers, spec_field)
    brand_idx = _find_column_index(headers, brand_field) if brand_field else None

    # Read data rows
    for row_num, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if not row or all(cell is None for cell in row):
            continue

        name = row[name_idx] if name_idx is not None else ""
        spec = row[spec_idx] if spec_idx is not None else ""
        brand = row[brand_idx] if brand_idx is not None and brand_idx < len(row) else ""

        if not name:
            continue

        product = Product(
            excel_row=row_num,
            name=str(name),
            spec=str(spec) if spec else "",
            brand=str(brand) if brand else ""
        )

        # Auto-detect brand if not provided
        if not product.brand:
            product.brand = extract_brand(product.name)

        products.append(product)

    return products


def _load_from_csv(
    path: Path,
    name_field: str,
    spec_field: str,
    brand_field: Optional[str]
) -> list[Product]:
    """Load products from CSV file."""
    import csv

    products: list[Product] = []

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row_num, row in enumerate(reader, start=2):
            name = row.get(name_field, "")
            if not name:
                continue

            spec = row.get(spec_field, "")
            brand = row.get(brand_field, "") if brand_field else ""

            product = Product(
                excel_row=row_num,
                name=name,
                spec=spec or "",
                brand=brand or ""
            )

            if not product.brand:
                product.brand = extract_brand(product.name)

            products.append(product)

    return products


def _load_from_json(
    path: Path,
    name_field: str,
    spec_field: str,
    brand_field: Optional[str]
) -> list[Product]:
    """Load products from JSON file."""
    import json

    products: list[Product] = []

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    items = data if isinstance(data, list) else data.get("products", [])
    for row_num, item in enumerate(items, start=2):
        name = item.get(name_field, "")
        if not name:
            continue

        spec = item.get(spec_field, "")
        brand = item.get(brand_field, "") if brand_field else ""

        product = Product(
            excel_row=row_num,
            name=name,
            spec=spec or "",
            brand=brand or ""
        )

        if not product.brand:
            product.brand = extract_brand(product.name)

        products.append(product)

    return products


def _find_column_index(headers: list, field_name: str) -> Optional[int]:
    """Find column index by field name (case-insensitive)."""
    field_lower = field_name.lower()
    for idx, header in enumerate(headers):
        if header and header.lower() == field_lower:
            return idx
    # Try partial match
    for idx, header in enumerate(headers):
        if header and field_lower in header.lower():
            return idx
    raise ValueError(f"Field '{field_name}' not found in headers: {headers}")


def workflow(
    input_file: str,
    output_dir: str = "./output",
    brand_field: Optional[str] = None,
    name_field: str = "name",
    spec_field: str = "spec"
) -> list[Product]:
    """
    Main workflow orchestration for image fetching.

    Args:
        input_file: Input file path (Excel/CSV/JSON)
        output_dir: Output directory path
        brand_field: Brand field name (optional)
        name_field: Product name field name
        spec_field: Product spec field name

    Returns:
        List of processed Product objects
    """
    # Parse arguments
    args = parse_args([
        input_file,
        "-o", output_dir,
        "-b", brand_field or "",
        "-n", name_field,
        "-s", spec_field
    ])

    # Resolve output directory
    output_path = Path(args.output_dir).resolve()
    output_path.mkdir(parents=True, exist_ok=True)

    # Load products
    print(f"Loading products from {input_file}...")
    products = load_products(
        args.input_file,
        name_field=args.name_field,
        spec_field=args.spec_field,
        brand_field=args.brand_field if args.brand_field else None
    )
    print(f"Loaded {len(products)} products")

    # Process each product
    print(f"Processing products...")
    for product in products:
        print(f"  [{product.excel_row}] {product.name} ({product.brand})")
        # TODO: Implement actual image fetching logic
        # For now, just demonstrate the naming logic
        filename = normalize_filename(product.name, product.spec, product.brand)
        image_path = get_image_path(product.brand, filename, output_path)
        product.image_path = str(image_path)
        product.status = "success"
        print(f"    -> {image_path}")

    return products


def main():
    """Entry point for /img-fetch command."""
    try:
        args = parse_args()
        products = workflow(
            input_file=args.input_file,
            output_dir=args.output_dir,
            brand_field=args.brand_field,
            name_field=args.name_field,
            spec_field=args.spec_field
        )
        print(f"\nCompleted: {len(products)} products processed")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
