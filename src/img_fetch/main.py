"""Slash command handler for /img-fetch."""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

from img_fetch.core.product import Product, FetchAttempt
from img_fetch.core.brand_extractor import extract_brand
from img_fetch.core.file_namer import normalize_filename, get_image_path
from img_fetch.config import OUTPUT_DIR, IMAGES_DIR
from img_fetch.writers.manifest_writer import ManifestWriter
from img_fetch.writers.report_writer import ReportWriter

logger = logging.getLogger(__name__)


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
    brand_field: Optional[str] = None,
    url_field: Optional[str] = "商品链接"
) -> list[Product]:
    """
    Load products from input file.

    Args:
        input_file: Path to input file (Excel/CSV/JSON)
        name_field: Field name for product name
        spec_field: Field name for product spec
        brand_field: Field name for brand (optional)
        url_field: Field name for product URL (optional, auto-detected for Chinese files)

    Returns:
        List of Product objects
    """
    path = Path(input_file)
    suffix = path.suffix.lower()

    products: list[Product] = []

    if suffix == ".xlsx" or suffix == ".xls":
        products = _load_from_excel(path, name_field, spec_field, brand_field, url_field)
    elif suffix == ".csv":
        products = _load_from_csv(path, name_field, spec_field, brand_field, url_field)
    elif suffix == ".json":
        products = _load_from_json(path, name_field, spec_field, brand_field, url_field)
    else:
        raise ValueError(f"Unsupported file format: {suffix}")

    return products


def _load_from_excel(
    path: Path,
    name_field: str,
    spec_field: str,
    brand_field: Optional[str],
    url_field: Optional[str] = "商品链接"
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
    url_idx = _find_column_index(headers, url_field) if url_field else None

    # Read data rows
    for row_num, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if not row or all(cell is None for cell in row):
            continue

        name = row[name_idx] if name_idx is not None else ""
        spec = row[spec_idx] if spec_idx is not None else ""
        brand = row[brand_idx] if brand_idx is not None and brand_idx < len(row) else ""
        url = row[url_idx] if url_idx is not None and url_idx < len(row) else ""

        if not name:
            continue

        product = Product(
            excel_row=row_num,
            name=str(name),
            spec=str(spec) if spec else "",
            brand=str(brand) if brand else "",
            product_url=str(url) if url else ""
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
    brand_field: Optional[str],
    url_field: Optional[str] = None
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
            url = row.get(url_field, "") if url_field else ""

            product = Product(
                excel_row=row_num,
                name=name,
                spec=spec or "",
                brand=brand or "",
                product_url=url or ""
            )

            if not product.brand:
                product.brand = extract_brand(product.name)

            products.append(product)

    return products


def _load_from_json(
    path: Path,
    name_field: str,
    spec_field: str,
    brand_field: Optional[str],
    url_field: Optional[str] = None
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
        url = item.get(url_field, "") if url_field else ""

        product = Product(
            excel_row=row_num,
            name=name,
            spec=spec or "",
            brand=brand or "",
            product_url=url or ""
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

    # Initialize manifest and report writers
    manifest_writer = ManifestWriter(output_path)
    report_writer = ReportWriter(output_path)

    # Create images subdirectory
    images_path = output_path / "images"
    images_path.mkdir(parents=True, exist_ok=True)

    # Load products
    print(f"Loading products from {input_file}...")
    products = load_products(
        args.input_file,
        name_field=args.name_field,
        spec_field=args.spec_field,
        brand_field=args.brand_field if args.brand_field else None
    )
    print(f"Loaded {len(products)} products")

    # Write initial manifest
    manifest_writer.write_manifest(products, task_status="in_progress")

    # Process each product
    print(f"Processing products...")
    for product in products:
        print(f"  [{product.excel_row}] {product.name} ({product.brand})")

        # Try to fetch image using mock fetcher
        success, image_path = _fetch_product_image(product, output_path)

        if success and image_path:
            product.status = "success"
            product.image_path = image_path
            print(f"    -> SUCCESS: {image_path}")
        else:
            product.status = "failed"
            print(f"    -> FAILED: {product.error_message or 'No image found'}")

        # Update manifest after each product
        manifest_writer.write_manifest(products, task_status="in_progress")

    # Mark task as complete
    manifest_writer.mark_task_complete(products)

    # Generate report
    print(f"Generating report...")
    report_writer.write_report(products)
    print(f"Report saved to: {report_writer.get_report_path()}")

    return products


def _fetch_product_image(product: Product, output_dir: Path) -> tuple[bool, Optional[str]]:
    """
    Fetch image for a single product using appropriate fetcher.

    Image Source Priority:
    1. Brand official website (highest priority)
    2. Amazon / JD / Taobao
    3. Youzan (only as last resort)

    Args:
        product: Product to fetch image for
        output_dir: Output directory path

    Returns:
        Tuple of (success: bool, image_path: Optional[str])
    """
    from img_fetch.core.product import FetchAttempt
    from img_fetch.fetchers.youzan_fetcher import YouzanFetcher
    from img_fetch.fetchers.ecommerce_fetcher import EcommerceFetcher
    from img_fetch.config import ECOMMERCE_SITES

    # 1. Try brand website first (highest priority)
    if product.brand:
        attempt = _try_brand_fetcher(product, output_dir)
        product.attempts.append(attempt)
        if attempt.source not in product.tried_sources:
            product.tried_sources.append(attempt.source)

        if attempt.status == "success" and product.image_path:
            return True, product.image_path

    # 2. If product has a direct URL from e-commerce, try it
    if product.product_url:
        url_lower = product.product_url.lower()
        is_ecommerce = any(
            platform in url_lower or base_url.replace("https://www.", "") in url_lower
            for platform, base_url in ECOMMERCE_SITES.items()
        )

        if is_ecommerce:
            attempt = _try_ecommerce_fetcher(product, output_dir)
            product.attempts.append(attempt)
            if attempt.source not in product.tried_sources:
                product.tried_sources.append(attempt.source)

            if attempt.status == "success" and product.image_path:
                return True, product.image_path
        elif "youzan.com" in url_lower or "yzcdn.cn" in url_lower:
            # 3. Try Youzan as last resort
            attempt = _try_youzan_fetcher(product, output_dir)
            product.attempts.append(attempt)
            if attempt.source not in product.tried_sources:
                product.tried_sources.append(attempt.source)

            if attempt.status == "success" and product.image_path:
                return True, product.image_path
        else:
            # Try direct URL fetch for other URLs
            attempt = _try_fetch_from_url(product.product_url, product, output_dir)
            product.attempts.append(attempt)
            if attempt.source not in product.tried_sources:
                product.tried_sources.append(attempt.source)

            if attempt.status == "success" and product.image_path:
                return True, product.image_path

    # All attempts failed
    if not product.error_message:
        product.error_message = "No image could be fetched from any source"

    return False, None


def _try_youzan_fetcher(product: Product, output_dir: Path) -> FetchAttempt:
    """
    Try to fetch image using YouzanFetcher.

    Args:
        product: Product to fetch
        output_dir: Output directory

    Returns:
        FetchAttempt with results
    """
    from img_fetch.core.product import FetchAttempt
    from img_fetch.fetchers.youzan_fetcher import YouzanFetcher

    source = "youzan"

    try:
        images_path = output_dir / "images"
        images_path.mkdir(parents=True, exist_ok=True)
        fetcher = YouzanFetcher(output_dir=images_path)
        image_path = fetcher.fetch(product)

        if image_path and product.image_path:
            return FetchAttempt(
                source=source,
                status="success",
                url=product.product_url,
                error=""
            )
        else:
            return FetchAttempt(
                source=source,
                status="failed",
                url=product.product_url,
                error=product.error_message or "No image found"
            )

    except Exception as e:
        return FetchAttempt(
            source=source,
            status="failed",
            url=product.product_url,
            error=str(e)
        )


def _try_ecommerce_fetcher(product: Product, output_dir: Path) -> FetchAttempt:
    """
    Try to fetch image using e-commerce fetcher (Amazon, JD, Taobao).

    Args:
        product: Product to fetch
        output_dir: Output directory

    Returns:
        FetchAttempt with results
    """
    from img_fetch.core.product import FetchAttempt
    from img_fetch.fetchers.ecommerce_fetcher import EcommerceFetcher

    source = "ecommerce"

    try:
        images_path = output_dir / "images"
        images_path.mkdir(parents=True, exist_ok=True)
        fetcher = EcommerceFetcher(output_dir=images_path)
        image_path = fetcher.fetch(product)

        if image_path and product.image_path:
            return FetchAttempt(
                source=source,
                status="success",
                url=product.product_url,
                error=""
            )
        else:
            return FetchAttempt(
                source=source,
                status="failed",
                url=product.product_url,
                error=product.error_message or "No image found on e-commerce site"
            )
    except Exception as e:
        return FetchAttempt(
            source=source,
            status="failed",
            url=product.product_url,
            error=str(e)
        )


def _try_fetch_from_url(url: str, product: Product, output_dir: Path) -> FetchAttempt:
    """
    Try to fetch image directly from product URL.

    Args:
        url: Product page URL
        product: Product object
        output_dir: Output directory

    Returns:
        FetchAttempt with results
    """
    from img_fetch.core.product import FetchAttempt
    from urllib.parse import urlparse

    source = f"url:{urlparse(url).netloc}"

    try:
        import requests
        from img_fetch.core.file_namer import normalize_filename

        # Make request to the product URL
        response = requests.get(url, timeout=30, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })
        response.raise_for_status()

        # Try to extract image URL from page (simple mock implementation)
        image_url = _extract_image_url_from_html(response.text, url)

        if not image_url:
            return FetchAttempt(
                source=source,
                status="failed",
                url=url,
                error="No image found on page"
            )

        # Download the image
        image_response = requests.get(image_url, timeout=30)
        image_response.raise_for_status()

        # Save image
        filename = normalize_filename(product.name, product.spec, product.brand)
        brand_dir = output_dir / "images" / product.brand.upper().replace(" ", "_")
        brand_dir.mkdir(parents=True, exist_ok=True)
        image_path = brand_dir / filename

        # Determine extension from content type or URL
        ext = _get_extension_from_url(image_url)
        if not ext:
            ext = ".jpg"
        if not str(image_path).endswith(ext):
            image_path = Path(str(image_path).replace(".jpg", ext).replace(".jpeg", ext))

        image_path.write_bytes(image_response.content)
        product.image_path = str(image_path)

        return FetchAttempt(
            source=source,
            status="success",
            url=image_url,
            error=""
        )

    except Exception as e:
        return FetchAttempt(
            source=source,
            status="failed",
            url=url,
            error=str(e)
        )


def _extract_image_url_from_html(html: str, base_url: str) -> Optional[str]:
    """Extract image URL from HTML page (simple implementation)."""
    from urllib.parse import urljoin
    import re

    # Common image patterns in HTML
    patterns = [
        r'<img[^>]+src=["\']([^"\']+)["\']',
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'["\']image["\']\s*:\s*["\']([^"\']+)["\']',
    ]

    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            url = match.group(1)
            # Handle protocol-relative URLs
            if url.startswith("//"):
                url = "https:" + url
            # Make relative URLs absolute
            elif not url.startswith("http"):
                url = urljoin(base_url, url)
            return url

    return None


def _get_extension_from_url(url: str) -> Optional[str]:
    """Get file extension from URL."""
    if "." in url:
        ext = url.rsplit(".", 1)[-1].split("?")[0]
        if ext.lower() in ["jpg", "jpeg", "png", "webp", "gif"]:
            return f".{ext.lower()}"
    return None


def _try_brand_fetcher(product: Product, output_dir: Path) -> FetchAttempt:
    """
    Try to fetch image using brand fetcher with real browser automation.

    Args:
        product: Product object
        output_dir: Output directory

    Returns:
        FetchAttempt with results
    """
    from img_fetch.core.product import FetchAttempt
    from img_fetch.config import BRAND_WEBSITES
    from img_fetch.fetchers.brand_fetcher import BrandFetcher

    brand_key = product.brand.upper().replace(" ", "_").replace(".", "")
    website = BRAND_WEBSITES.get(brand_key)

    if not website:
        return FetchAttempt(
            source=f"brand:{product.brand}",
            status="failed",
            url="",
            error=f"No known website for brand: {product.brand}"
        )

    try:
        images_path = output_dir / "images"
        images_path.mkdir(parents=True, exist_ok=True)
        fetcher = BrandFetcher(output_dir=images_path)
        image_path = fetcher.fetch(product)

        if image_path and product.image_path:
            return FetchAttempt(
                source=f"brand:{product.brand}",
                status="success",
                url=website,
                error=""
            )
        else:
            return FetchAttempt(
                source=f"brand:{product.brand}",
                status="failed",
                url=website,
                error=product.error_message or "No image found on brand website"
            )
    except Exception as e:
        return FetchAttempt(
            source=f"brand:{product.brand}",
            status="failed",
            url=website,
            error=str(e)
        )


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
