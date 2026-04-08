"""Fetcher for e-commerce platforms."""

import logging
import time
from typing import Optional, Dict
from urllib.parse import urljoin

from selenium.webdriver.common.by import By

from img_fetch.config import ECOMMERCE_SITES, RATE_LIMITS, BROWSER_CONFIG
from img_fetch.core.product import Product
from img_fetch.fetchers.base import BaseFetcher
from img_fetch.automation.browser import Browser
from img_fetch.automation.human_behavior import HumanBehavior
from img_fetch.utils.exceptions import ImageNotFoundError, AntiBotDetectedError, BrowserError
from img_fetch.utils.rate_limiter import RateLimiter


logger = logging.getLogger(__name__)


class EcommerceFetcher(BaseFetcher):
    """
    Fetcher for e-commerce platforms (Amazon, JD, Taobao).

    Handles platform-specific navigation and image extraction.
    """

    def __init__(
        self,
        browser: Optional[Browser] = None,
        rate_limiter: Optional[RateLimiter] = None,
    ):
        """
        Initialize e-commerce fetcher.

        Args:
            browser: Browser instance (creates new if None)
            rate_limiter: Rate limiter instance (creates new if None)
        """
        self._browser = browser
        self._rate_limiter = rate_limiter or RateLimiter(RATE_LIMITS)
        self._human_behavior: Optional[HumanBehavior] = None

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

        E-commerce fetcher supports products with product URLs
        from known e-commerce platforms.

        Args:
            product: Product to check

        Returns:
            True if supported, False otherwise
        """
        if not product.product_url:
            return False

        return self._get_platform(product.product_url) is not None

    def can_retry(self) -> bool:
        """Check if retries are supported."""
        return True

    def fetch(self, product: Product) -> Optional[str]:
        """
        Fetch image from e-commerce platform.

        Args:
            product: Product to fetch image for

        Returns:
            Path to saved image, or None if failed
        """
        if not self.supports(product):
            logger.warning(f"E-commerce fetcher does not support product: {product.name}")
            return None

        platform = self._get_platform(product.product_url)
        if not platform:
            return None

        # Apply rate limiting
        self._rate_limiter.wait(product.product_url)

        try:
            return self._fetch_from_platform(product, platform)
        except AntiBotDetectedError:
            logger.warning(f"Anti-bot detection triggered for: {product.product_url}")
            return None
        except BrowserError as e:
            logger.error(f"Browser error fetching product: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching from e-commerce: {e}")
            return None

    def _get_platform(self, url: str) -> Optional[str]:
        """
        Identify e-commerce platform from URL.

        Args:
            url: Product URL

        Returns:
            Platform name or None
        """
        url_lower = url.lower()

        for platform, base_url in ECOMMERCE_SITES.items():
            if platform in url_lower or base_url.replace("https://www.", "") in url_lower:
                return platform

        return None

    def _fetch_from_platform(self, product: Product, platform: str) -> Optional[str]:
        """
        Perform actual fetch from e-commerce platform.

        Args:
            product: Product to fetch
            platform: Platform name

        Returns:
            Path to saved image, or None if failed
        """
        if platform == "amazon":
            return self._fetch_from_amazon(product)
        elif platform == "jd":
            return self._fetch_from_jd(product)
        elif platform == "taobao":
            return self._fetch_from_taobao(product)
        else:
            logger.warning(f"Unsupported platform: {platform}")
            return None

    def _fetch_from_amazon(self, product: Product) -> Optional[str]:
        """
        Fetch image from Amazon.

        Args:
            product: Product to fetch

        Returns:
            Path to saved image, or None if failed
        """
        with self.browser as browser:
            browser.get(product.product_url)
            self.human_behavior.random_delay(2.0, 4.0)

            if self._is_blocked(browser):
                raise AntiBotDetectedError("Amazon blocked")

            image_url = self._find_amazon_image(browser)

            if not image_url:
                # Try alternate method - find image in script tag
                image_url = self._extract_amazon_image_from_script(browser)

            if not image_url:
                logger.warning(f"No image found for Amazon product: {product.name}")
                return None

            return self._download_image(image_url, product)

    def _find_amazon_image(self, browser: Browser) -> Optional[str]:
        """Find image on Amazon product page."""
        # Try main product image
        selectors = [
            "#landingImage",
            "#imgTagWrapperId img",
            "#main-image-container img",
            ".a-dynamic-image",
            "[data-testid='product-image'] img",
        ]

        for selector in selectors:
            img = browser.find_element(By.CSS_SELECTOR, selector)
            if img:
                src = img.get_attribute("src") or ""
                if src and "sprite" not in src.lower():
                    return src

        return None

    def _extract_amazon_image_from_script(self, browser: Browser) -> Optional[str]:
        """Extract image URL from Amazon's JavaScript data."""
        script = """
        const scripts = Array.from(document.querySelectorAll('script[type="application/json"]'));
        for (const s of scripts) {
            try {
                const data = JSON.parse(s.textContent);
                if (data && data.productImages && data.productImages.images) {
                    const images = data.productImages.images;
                    for (const key of Object.keys(images)) {
                        if (images[key] && images[key].large) {
                            return images[key].large;
                        }
                    }
                }
            } catch (e) {}
        }
        return null;
        """
        return browser.execute_script(script)

    def _fetch_from_jd(self, product: Product) -> Optional[str]:
        """
        Fetch image from JD.com.

        Args:
            product: Product to fetch

        Returns:
            Path to saved image, or None if failed
        """
        with self.browser as browser:
            browser.get(product.product_url)
            self.human_behavior.random_delay(2.0, 3.0)

            if self._is_blocked(browser):
                raise AntiBotDetectedError("JD blocked")

            image_url = self._find_jd_image(browser)
            if not image_url:
                logger.warning(f"No image found for JD product: {product.name}")
                return None

            return self._download_image(image_url, product)

    def _find_jd_image(self, browser: Browser) -> Optional[str]:
        """Find image on JD.com product page."""
        # JD image selectors
        selectors = [
            "#spec-img",
            ".jqzoom img",
            "#detail-img img",
            "[class*='product-image'] img",
            "[class*='gallery'] img",
        ]

        for selector in selectors:
            img = browser.find_element(By.CSS_SELECTOR, selector)
            if img:
                src = img.get_attribute("src") or ""
                zoom_src = img.get_attribute("jqimg") or ""
                return zoom_src or src

        return None

    def _fetch_from_taobao(self, product: Product) -> Optional[str]:
        """
        Fetch image from Taobao.

        Args:
            product: Product to fetch

        Returns:
            Path to saved image, or None if failed
        """
        with self.browser as browser:
            browser.get(product.product_url)
            self.human_behavior.random_delay(2.0, 4.0)

            if self._is_blocked(browser):
                raise AntiBotDetectedError("Taobao blocked")

            image_url = self._find_taobao_image(browser)
            if not image_url:
                logger.warning(f"No image found for Taobao product: {product.name}")
                return None

            return self._download_image(image_url, product)

    def _find_taobao_image(self, browser: Browser) -> Optional[str]:
        """Find image on Taobao product page."""
        # Taobao image selectors
        selectors = [
            "#J_ImgBooth",
            ".tb-booth a img",
            "[class*='J_BoxAttr'] img",
            "[class*='itemInfo'] img",
            "[class*='mainPic'] img",
        ]

        for selector in selectors:
            img = browser.find_element(By.CSS_SELECTOR, selector)
            if img:
                src = img.get_attribute("src") or ""
                data_src = img.get_attribute("data-src") or ""
                return data_src or src

        return None

    def _is_blocked(self, browser: Browser) -> bool:
        """
        Check if page shows anti-bot detection.

        Args:
            browser: Browser instance

        Returns:
            True if blocked, False otherwise
        """
        page_source = browser.get_page_source().lower()

        blocked_indicators = [
            "access denied",
            "blocked",
            "security check",
            "captcha",
            "robot check",
            "unusual traffic",
            "访问过于频繁",
            "请输入验证码",
            "账号异常",
        ]

        return any(indicator in page_source for indicator in blocked_indicators)

    def _download_image(self, url: str, product: Product) -> Optional[str]:
        """
        Download image from URL.

        Args:
            url: Image URL
            product: Product the image is for

        Returns:
            Path to saved image, or None if failed
        """
        from img_fetch.core.file_namer import FileNamer

        try:
            import requests
            from img_fetch.config import IMAGES_DIR

            # Handle protocol-relative URLs
            if url.startswith("//"):
                url = "https:" + url

            response = requests.get(url, timeout=30)
            response.raise_for_status()

            content_type = response.headers.get("content-type", "")
            if "image" not in content_type and not url.endswith((".jpg", ".jpeg", ".png", ".webp")):
                logger.warning(f"URL does not appear to be an image: {url}")
                return None

            ext = self._get_extension_from_url(url) or self._get_extension_from_content_type(content_type) or ".jpg"

            namer = FileNamer()
            filename = namer.generate_filename(product, ext)
            filepath = IMAGES_DIR / filename

            filepath.write_bytes(response.content)

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
