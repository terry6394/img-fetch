"""Brand extraction from product names."""

import re
from typing import Optional


# Brand prefix to full name mapping
BRAND_PREFIX_MAP: dict[str, str] = {
    "CANADA": "CANADA_GOOSE",
    "HAGLOFS": "HAGLOFS",
    "HELLY": "HELLY_HANSEN",
    "L.I.M": "L.I.M",
    "STONE": "STONE_ISLAND",
}

# Regex pattern for brand detection
BRAND_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"^CANADA\s*GOOSE", re.IGNORECASE), "CANADA_GOOSE"),
    (re.compile(r"^HAGLOFS", re.IGNORECASE), "HAGLOFS"),
    (re.compile(r"^HELLY\s*HANSEN", re.IGNORECASE), "HELLY_HANSEN"),
    (re.compile(r"^L\.I\.M", re.IGNORECASE), "L.I.M"),
    (re.compile(r"^STONE\s*ISLAND", re.IGNORECASE), "STONE_ISLAND"),
]


def extract_brand(product_name: str) -> str:
    """
    Extract brand from the first segment of a product name.

    Args:
        product_name: Full product name (e.g., "STONE ISLAND Ribbed Soft Cotton")

    Returns:
        Normalized brand name (e.g., "STONE_ISLAND")

    Examples:
        >>> extract_brand("STONE ISLAND Ribbed Soft Cotton")
        'STONE_ISLAND'
        >>> extract_brand("CANADA GOOSE Expedition Parka")
        'CANADA_GOOSE'
        >>> extract_brand("HAGLOFS Alpha Jacket")
        'HAGLOFS'
        >>> extract_brand("Some Unknown Brand Product")
        'SOME_UNKNOWN_BRAND'
    """
    if not product_name or not product_name.strip():
        return ""

    # Clean the input
    cleaned = product_name.strip()

    # Try pattern matching first (handles multi-word brands like "CANADA GOOSE")
    for pattern, brand_name in BRAND_PATTERNS:
        if pattern.match(cleaned):
            return brand_name

    # Fall back to first word prefix mapping
    first_word = cleaned.split()[0].upper()

    # Remove punctuation from first word
    first_word = re.sub(r"[^\w]", "", first_word)

    # Check prefix map
    if first_word in BRAND_PREFIX_MAP:
        return BRAND_PREFIX_MAP[first_word]

    # Unknown brand - normalize the first word
    return first_word.replace(" ", "_")


def normalize_brand(brand: str) -> str:
    """
    Normalize a brand name to a safe directory name.

    Args:
        brand: Raw brand name

    Returns:
        Normalized brand name safe for directory creation

    Examples:
        >>> normalize_brand("CANADA_GOOSE")
        'CANADA_GOOSE'
        >>> normalize_brand("HelLY HansEn")
        'HELLY_HANSEN'
    """
    if not brand:
        return ""

    # Upper case and replace spaces with underscores
    normalized = brand.upper().strip()
    normalized = re.sub(r"\s+", "_", normalized)

    # Remove any remaining unsafe characters
    normalized = re.sub(r"[^\w._-]", "", normalized)

    return normalized


def extract_brand_from_url(url: str) -> Optional[str]:
    """
    Extract brand name from a URL if possible.

    Args:
        url: Product URL

    Returns:
        Extracted brand name or None if not found
    """
    if not url:
        return None

    url_lower = url.lower()

    brand_domains = {
        "canadagoose.com": "CANADA_GOOSE",
        "haglofs.com": "HAGLOFS",
        "hellyhansen.com": "HELLY_HANSEN",
        "stoneisland.com": "STONE_ISLAND",
        "youzan.com": None,  # Don't extract from youzan
    }

    for domain, brand in brand_domains.items():
        if domain in url_lower:
            return brand

    return None
