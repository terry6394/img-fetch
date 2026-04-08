"""File naming utilities."""

import re
from pathlib import Path
from typing import Optional

from img_fetch.config import MAX_FILENAME_LENGTH, FORBIDDEN_CHARS


def normalize_filename(name: str, spec: str = "", brand: str = "") -> str:
    """
    Create a normalized filename from product information.

    Format: {BRAND}_{NAME}_{SPEC}.{ext}

    Args:
        name: Product name
        spec: Product specification
        brand: Brand name (optional, will be extracted from name if not provided)
        ext: File extension (default: jpg)

    Returns:
        Normalized filename safe for filesystem use

    Examples:
        >>> normalize_filename("Ribbed Soft Cotton", "BLACK-M", "STONE_ISLAND")
        'STONE_ISLAND_Ribbed_Soft_Cotton_BLACK-M.jpg'
        >>> normalize_filename("Alpha Jacket", "RED-L", "HAGLOFS")
        'HAGLOFS_Alpha_Jacket_RED-L.jpg'
    """
    parts = []

    # Add brand
    if brand:
        parts.append(_normalize_part(brand))
    elif name:
        # Brand will be extracted by caller, but we keep this for fallback
        pass

    # Add product name
    if name:
        parts.append(_normalize_part(name))

    # Add spec (without leading hyphen if it starts with one)
    if spec:
        spec_clean = spec.strip()
        if spec_clean.startswith("-"):
            spec_clean = spec_clean[1:]
        parts.append(_normalize_part(spec_clean))

    # Join parts with underscore
    filename = "_".join(parts)

    # Ensure not too long (leave room for extension)
    if len(filename) > MAX_FILENAME_LENGTH - 5:
        filename = filename[:MAX_FILENAME_LENGTH - 5]

    return f"{filename}.jpg"


def _normalize_part(text: str) -> str:
    """
    Normalize a single part of a filename.

    - Replace spaces with underscores
    - Remove or replace forbidden characters
    - Convert to uppercase for consistency
    """
    if not text:
        return ""

    # Strip and convert to uppercase
    normalized = text.strip().upper()

    # Replace spaces with underscores
    normalized = re.sub(r"\s+", "_", normalized)

    # Replace forbidden characters with underscore or remove
    for char in FORBIDDEN_CHARS:
        normalized = normalized.replace(char, "_")

    # Replace multiple consecutive underscores with single
    normalized = re.sub(r"_+", "_", normalized)

    # Remove leading/trailing underscores
    normalized = normalized.strip("_")

    return normalized


def get_image_path(brand: str, filename: str, output_dir: Optional[Path] = None) -> Path:
    """
    Get the full image path for a brand and filename.

    Args:
        brand: Normalized brand name
        filename: Normalized filename
        output_dir: Output directory (defaults to IMAGES_DIR from config)

    Returns:
        Full path to save the image

    Examples:
        >>> path = get_image_path("STONE_ISLAND", "STONE_ISLAND_Cotton_BLACK.jpg")
        >>> path.parts[-3:]  # just check last 3 parts
        ('images', 'STONE_ISLAND', 'STONE_ISLAND_Cotton_BLACK.jpg')
    """
    if output_dir is None:
        from img_fetch.config import IMAGES_DIR
        output_dir = IMAGES_DIR

    brand_dir = output_dir / brand
    brand_dir.mkdir(parents=True, exist_ok=True)

    return brand_dir / filename


def is_safe_filename(filename: str) -> bool:
    """
    Check if a filename is safe for filesystem use.

    Args:
        filename: Filename to check

    Returns:
        True if safe, False otherwise
    """
    if not filename or filename != filename.strip():
        return False

    # Check for forbidden characters
    for char in FORBIDDEN_CHARS:
        if char in filename:
            return False

    # Check for path traversal attempts
    if ".." in filename or filename.startswith("/"):
        return False

    # Check for special Windows names
    windows_reserved = ["CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3",
                        "COM4", "LPT1", "LPT2", "LPT3"]
    name_upper = filename.split(".")[0].upper()
    if name_upper in windows_reserved:
        return False

    return True


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to make it safe.

    Args:
        filename: Potentially unsafe filename

    Returns:
        Safe filename
    """
    if not filename:
        return "unnamed"

    # Replace forbidden characters
    for char in FORBIDDEN_CHARS:
        filename = filename.replace(char, "_")

    # Remove path traversal
    filename = filename.replace("..", "")
    filename = filename.lstrip("/")

    # Ensure not empty
    if not filename or filename.strip() == "":
        return "unnamed"

    return filename.strip()
