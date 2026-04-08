"""Fetcher for Youzan e-commerce platform."""

import logging
import re
from typing import Optional
from urllib.parse import urljoin, urlparse

import requests

from img_fetch.config import RATE_LIMITS
from img_fetch.core.product import Product
from img_fetch.fetchers.base import BaseFetcher
from img_fetch.utils.exceptions import ImageNotFoundError, NetworkError
from img_fetch.utils.rate_limiter import RateLimiter


logger = logging.getLogger(__name__)


class YouzanFetcher(BaseFetcher):
    """
    Fetcher for Youzan e-commerce platform.

    Handles product pages on youzan.com and m.youzan.com domains.
    """

    # Rate limit for youzan.com
    DEFAULT_RATE_LIMIT = 30  # requests per minute

    def __init__(self, rate_limiter: Optional[RateLimiter] = None):
        """
        Initialize Youzan fetcher.

        Args:
            rate_limiter: Rate limiter instance (creates new if None)
        """
        self._rate_limiter = rate_limiter or RateLimiter(RATE_LIMITS)

    def supports(self, product: Product) -> bool:
        """
        Check if this fetcher supports the product.

        Youzan fetcher supports products with youzan.com URLs.

        Args:
            product: Product to check

        Returns:
            True if supported, False otherwise
        """
        if not product.product_url:
            return False

        return self._is_youzan_url(product.product_url)

    def _is_youzan_url(self, url: str) -> bool:
        """Check if URL is from Youzan platform."""
        url_lower = url.lower()
        return "youzan.com" in url_lower or "yzcdn.cn" in url_lower

    def can_retry(self) -> bool:
        """Check if retries are supported."""
        return True

    def fetch(self, product: Product) -> Optional[str]:
        """
        Fetch image from Youzan product page.

        Args:
            product: Product to fetch image for

        Returns:
            Path to saved image, or None if failed
        """
        if not self.supports(product):
            logger.warning(f"Youzan fetcher does not support product: {product.name}")
            return None

        # Apply rate limiting
        self._rate_limiter.wait(product.product_url)

        try:
            image_path = self._fetch_from_youzan(product)
            if image_path:
                product.status = "success"
            return image_path
        except NetworkError as e:
            logger.error(f"Network error fetching from Youzan: {e}")
            product.error_message = str(e)
            product.status = "failed"
            return None
        except ImageNotFoundError as e:
            logger.warning(f"Image not found on Youzan page: {e}")
            product.error_message = str(e)
            product.status = "failed"
            return None
        except Exception as e:
            logger.error(f"Error fetching from Youzan: {e}")
            product.error_message = str(e)
            product.status = "failed"
            return None

    def _fetch_from_youzan(self, product: Product) -> Optional[str]:
        """
        Perform actual fetch from Youzan page.

        Args:
            product: Product to fetch

        Returns:
            Path to saved image, or None if failed
        """
        try:
            # Fetch the product page
            response = requests.get(
                product.product_url,
                timeout=30,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
                }
            )
            response.raise_for_status()
            html = response.text

            # Extract image URL from HTML
            image_url = self._find_image_in_html(product.product_url, html)
            if not image_url:
                raise ImageNotFoundError(f"No image found on Youzan page: {product.product_url}")

            # Extract page metadata
            page_metadata = self._extract_page_metadata(product.product_url, html)

            # Download the image
            return self._download_image(image_url, product, page_metadata)

        except requests.HTTPError as e:
            raise NetworkError(f"HTTP error: {e.response.status_code}")
        except requests.RequestException as e:
            raise NetworkError(f"Request failed: {e}")

    def _find_image_in_html(self, base_url: str, html: str) -> Optional[str]:
        """
        Find image URL in Youzan page HTML.

        Args:
            base_url: Base URL for resolving relative URLs
            html: Page HTML content

        Returns:
            Image URL or None if not found
        """
        # Try og:image meta tag first (most reliable for products)
        og_image = self._extract_og_image(html)
        if og_image:
            return self._resolve_url(base_url, og_image)

        # Try youzan-specific data attributes
        yz_image = self._extract_youzan_image(html)
        if yz_image:
            return self._resolve_url(base_url, yz_image)

        # Try first img tag with valid image
        img_src = self._extract_first_image(html)
        if img_src:
            return self._resolve_url(base_url, img_src)

        return None

    def _extract_og_image(self, html: str) -> Optional[str]:
        """Extract og:image meta tag content."""
        patterns = [
            r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
        ]

        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    def _extract_youzan_image(self, html: str) -> Optional[str]:
        """Extract Youzan-specific image from data attributes or JSON."""
        # Try to find youzan image URLs in data attributes
        patterns = [
            r'data-src=["\']([^"\']+)["\']',
            r'data-image=["\']([^"\']+)["\']',
            r'"image":["\']([^"\']+)["\']',
            r'"pic_url":["\']([^"\']+)["\']',
        ]

        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                url = match.group(1)
                # Make sure it looks like an image URL
                if any(ext in url.lower() for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"]):
                    return url

        return None

    def _extract_first_image(self, html: str) -> Optional[str]:
        """Extract src from first img tag."""
        # Find img tags with src attribute
        pattern = r'<img[^>]+src=["\']([^"\']+)["\']'
        matches = re.finditer(pattern, html, re.IGNORECASE)

        for match in matches:
            src = match.group(1)
            # Skip icons, logos, sprites
            if self._is_valid_product_image(src):
                return src

        return None

    def _is_valid_product_image(self, url: str) -> bool:
        """Check if URL appears to be a product image (not icon/logo)."""
        url_lower = url.lower()

        # Exclude common non-product image patterns
        exclude_patterns = [
            "icon",
            "logo",
            "sprite",
            "banner",
            "placeholder",
            "loading",
            "spinner",
            "avatar",
            "qr",
            "code",
        ]

        if any(pattern in url_lower for pattern in exclude_patterns):
            return False

        # Include common product image patterns
        include_patterns = [
            "/product/",
            "/goods/",
            "/item/",
            "/upload/",
            "/image/",
            "/img/",
        ]

        # If URL contains these patterns, it's likely a product image
        if any(pattern in url_lower for pattern in include_patterns):
            return True

        # Otherwise, accept if it has an image extension
        return any(ext in url_lower for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"])

    def _resolve_url(self, base_url: str, url: str) -> str:
        """
        Resolve relative URL to absolute URL.

        Args:
            base_url: Base URL
            url: Potentially relative URL

        Returns:
            Absolute URL
        """
        if not url:
            return url

        # Handle protocol-relative URLs
        if url.startswith("//"):
            return "https:" + url

        # Already absolute
        if url.startswith("http"):
            return url

        # Relative URL - make absolute
        return urljoin(base_url, url)

    def _extract_page_metadata(self, base_url: str, html: str) -> dict:
        """
        Extract page metadata from HTML.

        Args:
            base_url: Base URL
            html: Page HTML content

        Returns:
            Dict with title, description, keywords, etc.
        """
        metadata = {
            "title": "",
            "description": "",
            "keywords": [],
            "alt_text": [],
        }

        # Extract title
        title_match = re.search(r'<title[^>]*>([^<]+)</title>', html, re.IGNORECASE)
        if title_match:
            metadata["title"] = title_match.group(1).strip()

        # Extract description
        desc_patterns = [
            r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']',
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']description["\']',
        ]
        for pattern in desc_patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                metadata["description"] = match.group(1).strip()
                break

        # Extract keywords
        kw_patterns = [
            r'<meta[^>]+name=["\']keywords["\'][^>]+content=["\']([^"\']+)["\']',
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']keywords["\']',
        ]
        for pattern in kw_patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                keywords = match.group(1).strip()
                metadata["keywords"] = [k.strip() for k in keywords.split(",")]
                break

        # Extract alt text from images
        alt_pattern = r'<img[^>]+alt=["\']([^"\']*)["\'][^>]*>'
        alt_matches = re.finditer(alt_pattern, html, re.IGNORECASE)
        for match in alt_matches:
            alt = match.group(1).strip()
            if alt:
                metadata["alt_text"].append(alt)

        return metadata

    def _download_image(
        self,
        image_url: str,
        product: Product,
        page_metadata: Optional[dict] = None
    ) -> Optional[str]:
        """
        Download image from URL.

        Args:
            image_url: Image URL to download
            product: Product the image is for
            page_metadata: Optional page metadata to store

        Returns:
            Path to saved image, or None if failed
        """
        try:
            import requests
            from img_fetch.core.file_namer import normalize_filename, get_image_path
            from img_fetch.config import IMAGES_DIR
            from datetime import datetime

            # Download image using requests (handles SOCKS proxy natively)
            response = requests.get(image_url, timeout=30, allow_redirects=True)
            response.raise_for_status()

            content_type = response.headers.get("content-type", "")
            if "image" not in content_type:
                # Try to determine from URL
                ext = self._get_extension_from_url(image_url)
                if not ext:
                    raise ImageNotFoundError(f"URL does not return an image: {content_type}")
            else:
                ext = self._get_extension_from_content_type(content_type)

            # Generate filename
            filename = normalize_filename(product.name, product.spec, product.brand)
            if not filename.endswith(ext):
                filename = filename.rsplit(".", 1)[0] + ext

            # Determine save path
            brand_dir = IMAGES_DIR / product.brand.upper().replace(" ", "_")
            brand_dir.mkdir(parents=True, exist_ok=True)
            save_path = brand_dir / filename

            # Save image
            save_path.write_bytes(response.content)

            # Update product with image path and metadata
            product.image_path = str(save_path)

            # Create and store image metadata
            from urllib.parse import urlparse
            from img_fetch.core.product import ImageMetadata

            domain = urlparse(image_url).netloc

            product.image_metadata = ImageMetadata(
                source_url=image_url,
                source_domain=domain,
                source_page_title=page_metadata.get("title", "") if page_metadata else "",
                page_description=page_metadata.get("description", "") if page_metadata else "",
                page_keywords=page_metadata.get("keywords", []) if page_metadata else [],
                alt_text=",".join(page_metadata.get("alt_text", [])) if page_metadata else "",
            )

            logger.info(f"Downloaded image for {product.name} from {image_url}")

            return str(save_path)

        except requests.HTTPError as e:
            raise NetworkError(f"HTTP error downloading image: {e.response.status_code}")
        except requests.RequestException as e:
            raise NetworkError(f"Network error downloading image: {e}")
        except Exception as e:
            logger.error(f"Error downloading image: {e}")
            raise

    def _get_extension_from_url(self, url: str) -> Optional[str]:
        """Get file extension from URL."""
        if "." in url:
            ext = url.rsplit(".", 1)[-1].split("?")[0]
            if ext.lower() in ["jpg", "jpeg", "png", "webp", "gif"]:
                return f".{ext.lower()}"
        return None

    def _get_extension_from_content_type(self, content_type: str) -> str:
        """Get file extension from content type."""
        mapping = {
            "image/jpeg": ".jpg",
            "image/jpg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
            "image/gif": ".gif",
        }
        return mapping.get(content_type.lower(), ".jpg")