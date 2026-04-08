"""Product data model."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class ImageMetadata:
    """Metadata for a fetched image."""
    source_url: str
    source_page_title: str = ""
    source_domain: str = ""
    page_description: str = ""
    page_keywords: list[str] = field(default_factory=list)
    alt_text: str = ""
    image_width: int = 0
    image_height: int = 0
    captured_at: datetime = field(default_factory=datetime.now)


@dataclass
class FetchAttempt:
    """A single fetch attempt for a product."""
    source: str
    status: str  # "success", "failed", "skipped"
    url: str = ""
    error: str = ""


@dataclass
class Product:
    """Represents a product to fetch images for."""
    excel_row: int
    name: str
    spec: str
    product_code: str = ""
    spec_code: str = ""
    product_url: str = ""
    brand: str = ""
    status: str = "pending"  # "pending", "success", "failed", "skipped"
    image_path: str = ""
    image_metadata: Optional[ImageMetadata] = None
    search_query: str = ""
    tried_sources: list[str] = field(default_factory=list)
    attempts: list[FetchAttempt] = field(default_factory=list)
    error_message: str = ""
    retries: int = 0

    def __post_init__(self):
        """Build search query from name and spec."""
        if not self.search_query and self.name:
            parts = [self.name]
            if self.spec:
                parts.append(self.spec)
            self.search_query = " ".join(parts)
