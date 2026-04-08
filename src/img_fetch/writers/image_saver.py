"""Image download and save functionality."""

from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx
from PIL import Image
from PIL.Image import Image as PILImage

from img_fetch.core.file_namer import normalize_filename, get_image_path
from img_fetch.core.product import ImageMetadata
from img_fetch.utils.exceptions import ImageNotFoundError, NetworkError


class ImageSaver:
    """Handles downloading and saving images with metadata."""

    def __init__(
        self,
        output_dir: Optional[Path] = None,
        timeout: float = 30.0,
    ):
        """Initialize the image saver.

        Args:
            output_dir: Directory to save images. Defaults to config IMAGES_DIR.
            timeout: HTTP request timeout in seconds.
        """
        if output_dir is None:
            from img_fetch.config import IMAGES_DIR
            output_dir = IMAGES_DIR
        self.output_dir = Path(output_dir)
        self.timeout = timeout

    async def download_image(
        self,
        url: str,
        brand: str,
        product_name: str,
        product_spec: str = "",
        page_metadata: Optional[dict] = None,
    ) -> tuple[Path, ImageMetadata]:
        """Download an image from URL and save it.

        Args:
            url: Image URL to download
            brand: Brand name for directory organization
            product_name: Product name for filename
            product_spec: Product specification for filename
            page_metadata: Optional dict with page metadata (title, description, etc.)

        Returns:
            Tuple of (saved_path, image_metadata)

        Raises:
            ImageNotFoundError: If image cannot be downloaded
            NetworkError: If HTTP request fails
        """
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=self.timeout) as client:
                response = await client.get(url)
                response.raise_for_status()

                content_type = response.headers.get("content-type", "")
                if not self._is_valid_image_content_type(content_type):
                    raise ImageNotFoundError(f"URL does not return a valid image: {content_type}")

                image_content = response.content

        except httpx.HTTPStatusError as e:
            raise NetworkError(f"HTTP error downloading image: {e.response.status_code}")
        except httpx.RequestError as e:
            raise NetworkError(f"Network error downloading image: {e}")

        # Generate filename
        filename = normalize_filename(product_name, product_spec, brand)

        # Determine image path
        brand_normalized = brand.upper().replace(" ", "_") if brand else "UNKNOWN"
        save_path = get_image_path(brand_normalized, filename, self.output_dir)

        # Save image
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_bytes(image_content)

        # Extract metadata
        metadata = self._extract_metadata(
            url=url,
            image_path=save_path,
            page_metadata=page_metadata,
        )

        return save_path, metadata

    def _is_valid_image_content_type(self, content_type: str) -> bool:
        """Check if content type is a valid image type."""
        valid_types = [
            "image/jpeg",
            "image/jpg",
            "image/png",
            "image/gif",
            "image/webp",
            "image/bmp",
        ]
        return any(vt in content_type.lower() for vt in valid_types)

    def _extract_metadata(
        self,
        url: str,
        image_path: Path,
        page_metadata: Optional[dict] = None,
    ) -> ImageMetadata:
        """Extract metadata from saved image and page info.

        Args:
            url: Source URL
            image_path: Path where image was saved
            page_metadata: Optional page metadata dict

        Returns:
            ImageMetadata instance
        """
        width = 0
        height = 0

        try:
            with Image.open(image_path) as img:
                width, height = img.size
        except Exception:
            # If we can't read the image, just continue without dimensions
            pass

        from urllib.parse import urlparse
        domain = urlparse(url).netloc

        metadata = ImageMetadata(
            source_url=url,
            source_domain=domain,
            source_page_title=page_metadata.get("title", "") if page_metadata else "",
            page_description=page_metadata.get("description", "") if page_metadata else "",
            page_keywords=page_metadata.get("keywords", []) if page_metadata else [],
            alt_text=page_metadata.get("alt_text", []) if page_metadata else [],
            image_width=width,
            image_height=height,
            captured_at=datetime.now(),
        )

        return metadata

    def verify_image(self, image_path: Path) -> bool:
        """Verify that a saved file is a valid image.

        Args:
            image_path: Path to image file

        Returns:
            True if valid image, False otherwise
        """
        try:
            with Image.open(image_path) as img:
                img.verify()
            return True
        except Exception:
            return False

    def get_image_info(self, image_path: Path) -> Optional[dict]:
        """Get information about a saved image.

        Args:
            image_path: Path to image file

        Returns:
            Dict with image info or None if not found/invalid
        """
        if not image_path.exists():
            return None

        try:
            with Image.open(image_path) as img:
                return {
                    "format": img.format,
                    "mode": img.mode,
                    "size": img.size,
                    "width": img.width,
                    "height": img.height,
                }
        except Exception:
            return None


async def save_image(
    url: str,
    brand: str,
    product_name: str,
    product_spec: str = "",
    output_dir: Optional[Path] = None,
    page_metadata: Optional[dict] = None,
) -> tuple[Path, ImageMetadata]:
    """Convenience function to download and save an image.

    Args:
        url: Image URL to download
        brand: Brand name
        product_name: Product name
        product_spec: Product specification
        output_dir: Output directory
        page_metadata: Optional page metadata

    Returns:
        Tuple of (saved_path, image_metadata)
    """
    saver = ImageSaver(output_dir=output_dir)
    return await saver.download_image(
        url=url,
        brand=brand,
        product_name=product_name,
        product_spec=product_spec,
        page_metadata=page_metadata,
    )
