"""Fetcher for brand official websites."""

import logging
import time
from typing import Optional

from selenium.webdriver.common.by import By

from img_fetch.config import BRAND_WEBSITES, RATE_LIMITS, BROWSER_CONFIG
from img_fetch.core.product import Product
from img_fetch.fetchers.base import BaseFetcher
from img_fetch.automation.browser import Browser
from img_fetch.automation.human_behavior import HumanBehavior
from img_fetch.utils.exceptions import ImageNotFoundError, AntiBotDetectedError
from img_fetch.utils.rate_limiter import RateLimiter


logger = logging.getLogger(__name__)


class BrandFetcher(BaseFetcher):
    """
    Fetcher for brand official websites.

    Fetches product images from brand websites like Canada Goose,
    Helly Hansen, Stone Island, etc.
    """

    def __init__(
        self,
        browser: Optional[Browser] = None,
        rate_limiter: Optional[RateLimiter] = None,
        output_dir: Optional["Path"] = None,
    ):
        """
        Initialize brand fetcher.

        Args:
            browser: Browser instance (creates new if None)
            rate_limiter: Rate limiter instance (creates new if None)
            output_dir: Output directory for images (defaults to IMAGES_DIR)
        """
        from img_fetch.config import IMAGES_DIR
        self._browser = browser
        self._rate_limiter = rate_limiter or RateLimiter(RATE_LIMITS)
        self._human_behavior: Optional[HumanBehavior] = None
        self._output_dir = output_dir or IMAGES_DIR

    @property
    def browser(self) -> Browser:
        """Get or create browser instance."""
        if self._browser is None:
            self._browser = Browser(
                headless=BROWSER_CONFIG["headless"],
                window_width=BROWSER_CONFIG["window_width"],
                window_height=BROWSER_CONFIG["window_height"],
                page_load_timeout=BROWSER_CONFIG["page_load_timeout"],
                implicit_wait=BROWSER_CONFIG["implicit_wait"],
            )
        return self._browser

    @property
    def human_behavior(self) -> HumanBehavior:
        """Get or create human behavior instance."""
        if self._human_behavior is None:
            self._human_behavior = HumanBehavior(self.browser)
        return self._human_behavior

    def supports(self, product: Product) -> bool:
        """
        Check if this fetcher supports the product.

        Brand fetcher supports products with recognized brands.

        Args:
            product: Product to check

        Returns:
            True if supported, False otherwise
        """
        if not product.brand:
            return False

        brand_upper = product.brand.upper()
        return brand_upper in BRAND_WEBSITES

    def can_retry(self) -> bool:
        """Check if retries are supported."""
        return True

    def fetch(self, product: Product) -> Optional[str]:
        """
        Fetch image from brand website.

        Args:
            product: Product to fetch image for

        Returns:
            Path to saved image, or None if failed
        """
        if not self.supports(product):
            logger.warning(f"Brand fetcher does not support product: {product.name}")
            return None

        brand_key = product.brand.upper()
        brand_url = BRAND_WEBSITES.get(brand_key)

        if not brand_url:
            return None

        # Apply rate limiting
        self._rate_limiter.wait(brand_url)

        try:
            return self._fetch_from_brand(product, brand_url)
        except AntiBotDetectedError:
            logger.warning(f"Anti-bot detection triggered for brand: {brand_key}")
            return None
        except Exception as e:
            logger.error(f"Error fetching from brand {brand_key}: {e}")
            return None

    def _fetch_from_brand(self, product: Product, brand_url: str) -> Optional[str]:
        """
        Perform actual fetch from brand website.

        Args:
            product: Product to fetch
            brand_url: Brand website URL

        Returns:
            Path to saved image, or None if failed
        """
        search_url = self._build_search_url(brand_url, product)
        if not search_url:
            return None

        with self.browser as browser:
            browser.get(search_url)
            self.human_behavior.random_delay(1.0, 2.0)

            # Check for anti-bot detection
            if self._is_blocked(browser):
                raise AntiBotDetectedError("Anti-bot page detected")

            # Find product image
            image_url = self._find_product_image(browser, product)
            if not image_url:
                logger.warning(f"No image found for product: {product.name}")
                return None

            # Download image
            return self._download_image(image_url, product)

    def _build_search_url(self, brand_url: str, product: Product) -> Optional[str]:
        """
        Build search URL for product on brand website.

        Args:
            brand_url: Base brand URL
            product: Product to search for

        Returns:
            Search URL, or None if not possible
        """
        # Build search query from product name and spec
        query = product.search_query or f"{product.name} {product.spec}".strip()

        # Handle different brand website URL patterns
        if "canadagoose" in brand_url:
            return f"{brand_url}/en-ca/search?q={query}"
        elif "hellyhansen" in brand_url:
            return f"{brand_url}/en-us/search?q={query}"
        elif "haglofs" in brand_url:
            return f"{brand_url}/en/search?q={query}"
        elif "stoneisland" in brand_url:
            return f"{brand_url}/search?q={query}"
        else:
            # Generic search URL pattern
            return f"{brand_url}/search?q={query}"

    def _is_blocked(self, browser: Browser) -> bool:
        """
        Check if page shows anti-bot detection.

        Args:
            browser: Browser instance

        Returns:
            True if blocked, False otherwise
        """
        page_source = browser.get_page_source().lower()

        # Check for common anti-bot indicators
        blocked_indicators = [
            "access denied",
            "blocked",
            "security check",
            "captcha",
            "robot check",
            "unusual traffic",
        ]

        return any(indicator in page_source for indicator in blocked_indicators)

    def _find_product_image(self, browser: Browser, product: Product) -> Optional[str]:
        """
        Find product image URL on page.

        Args:
            browser: Browser instance
            product: Product being fetched

        Returns:
            Image URL, or None if not found
        """
        # Try common image selectors
        image_selectors = [
            # Product grid images
            ("css", '[data-testid="product-card-image"]'),
            ("css", ".product-card img"),
            ("css", ".product-grid img"),
            ("css", ".search-results img"),
            ("css", '[class*="product"] img'),
            ("css", "article img"),
            # General image containers
            ("css", ".image-container img"),
            ("css", ".gallery img"),
            # Picture elements
            ("css", "picture img"),
        ]

        for selector_type, selector in image_selectors:
            by = By.CSS_SELECTOR if selector_type == "css" else By.XPATH
            elements = browser.find_elements(by, selector)

            for img in elements:
                src = img.get_attribute("src") or ""
                data_src = img.get_attribute("data-src") or ""
                srcset = img.get_attribute("srcset") or ""

                # Prefer high-res images
                image_url = self._select_best_image(src, data_src, srcset)
                if image_url and self._is_product_image(image_url, product):
                    return image_url

        # Fallback: search for largest image on page
        return self._find_largest_image(browser)

    def _select_best_image(
        self,
        src: str,
        data_src: str,
        srcset: str,
    ) -> Optional[str]:
        """
        Select best quality image from available sources.

        Args:
            src: src attribute
            data_src: data-src attribute
            srcset: srcset attribute

        Returns:
            Best image URL
        """
        # Prefer data-src (lazy loaded)
        if data_src:
            return data_src

        # Parse srcset for highest resolution
        if srcset:
            srcset_parts = [s.strip().split() for s in srcset.split(",")]
            if srcset_parts:
                # Sort by size and return largest
                sorted_parts = sorted(srcset_parts, key=lambda x: int(x[1]) if len(x) > 1 else 0)
                return sorted_parts[-1][0]

        return src if src else None

    def _is_product_image(self, url: str, product: Product) -> bool:
        """
        Check if image URL likely contains product image.

        Args:
            url: Image URL
            product: Product being fetched

        Returns:
            True if likely product image
        """
        if not url:
            return False

        # Exclude logos and icons
        exclude_patterns = [
            "logo",
            "icon",
            "banner",
            "advertisement",
            "sprite",
        ]

        url_lower = url.lower()
        if any(pattern in url_lower for pattern in exclude_patterns):
            return False

        # Product images typically have product identifiers or common patterns
        # Accept if no strong negative indicators
        return True

    def _find_largest_image(self, browser: Browser) -> Optional[str]:
        """
        Find largest image on page as fallback.

        Args:
            browser: Browser instance

        Returns:
            URL of largest image, or None
        """
        script = """
        const images = Array.from(document.querySelectorAll('img'));
        const validImages = images.filter(img => {
            return img.naturalWidth > 200 && img.naturalHeight > 200;
        });
        if (validImages.length === 0) return null;

        validImages.sort((a, b) => (b.naturalWidth * b.naturalHeight) - (a.naturalWidth * a.naturalHeight));
        return validImages[0].src;
        """

        result = browser.execute_script(script)
        return result if isinstance(result, str) else None

    def _download_image(self, url: str, product: Product) -> Optional[str]:
        """
        Download image from URL with placeholder detection.

        Args:
            url: Image URL
            product: Product the image is for

        Returns:
            Path to saved image, or None if failed
        """
        # Import here to avoid circular imports
        from img_fetch.core.file_namer import FileNamer
        from img_fetch.config import IMAGES_DIR

        try:
            import requests
            from PIL import Image
            import io

            response = requests.get(url, timeout=30)
            response.raise_for_status()

            content_type = response.headers.get("content-type", "")
            if "image" not in content_type and not url.endswith((".jpg", ".jpeg", ".png", ".webp")):
                logger.warning(f"URL does not appear to be an image: {url}")
                return None

            image_content = response.content

            # Check image size (skip if < 5KB, likely placeholder)
            if len(image_content) < 5 * 1024:
                logger.warning(f"Image too small ({len(image_content)} bytes), likely placeholder: {url}")
                return None

            # Check image dimensions using PIL
            try:
                img = Image.open(io.BytesIO(image_content))
                width, height = img.size

                # Skip if image is too small (less than 200x200)
                if width < 200 or height < 200:
                    logger.warning(f"Image too small ({width}x{height}), likely placeholder: {url}")
                    return None

                # Skip if image is too large (unreasonably huge)
                if width > 10000 or height > 10000:
                    logger.warning(f"Image too large ({width}x{height}), likely invalid: {url}")
                    return None

            except Exception as img_error:
                logger.warning(f"Could not verify image dimensions: {img_error}")
                # Continue anyway if we can't check dimensions

            # Determine extension
            ext = self._get_extension_from_url(url) or self._get_extension_from_content_type(content_type) or ".jpg"

            # Generate filename
            namer = FileNamer()
            filename = namer.generate_filename(product, ext)
            filepath = self._output_dir / filename

            # Ensure brand directory exists
            filepath.parent.mkdir(parents=True, exist_ok=True)

            # Save image
            filepath.write_bytes(image_content)

            logger.info(f"Downloaded image ({width}x{height}, {len(image_content)} bytes) for {product.name}")
            return str(filepath)

        except Exception as e:
            logger.error(f"Error downloading image: {e}")
            return None

    def _get_extension_from_url(self, url: str) -> Optional[str]:
        """Get file extension from URL."""
        if "." in url:
            ext = url.rsplit(".", 1)[-1].split("?")[0]
            if ext in ["jpg", "jpeg", "png", "webp", "gif"]:
                return f".{ext}"
        return None

    def _get_extension_from_content_type(self, content_type: str) -> Optional[str]:
        """Get file extension from content type."""
        mapping = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
            "image/gif": ".gif",
        }
        return mapping.get(content_type.lower())
