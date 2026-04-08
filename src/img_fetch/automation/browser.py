"""Selenium browser controller with anti-detection features."""

import time
from pathlib import Path
from typing import Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    WebDriverException,
    TimeoutException,
    NoSuchElementException,
)

from img_fetch.config import BROWSER_CONFIG, HUMAN_BEHAVIOR_CONFIG
from img_fetch.utils.exceptions import BrowserError, AntiBotDetectedError


# Custom user agent to avoid detection
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


class Browser:
    """
    Selenium browser controller with headless Chrome and anti-detection features.

    Features:
    - Headless Chrome configuration
    - Anti-blink features disabled (avoid automation detection)
    - Custom user-agent
    - Screenshot capture on error
    - Context manager support
    """

    def __init__(
        self,
        headless: bool = None,
        window_width: int = None,
        window_height: int = None,
        page_load_timeout: int = None,
        implicit_wait: int = None,
        screenshot_dir: Optional[Path] = None,
    ):
        """
        Initialize browser controller.

        Args:
            headless: Run browser in headless mode (default from config)
            window_width: Browser window width (default from config)
            window_height: Browser window height (default from config)
            page_load_timeout: Page load timeout in seconds (default from config)
            implicit_wait: Implicit wait timeout in seconds (default from config)
            screenshot_dir: Directory to save error screenshots
        """
        self.headless = headless if headless is not None else BROWSER_CONFIG["headless"]
        self.window_width = window_width or BROWSER_CONFIG["window_width"]
        self.window_height = window_height or BROWSER_CONFIG["window_height"]
        self.page_load_timeout = page_load_timeout or BROWSER_CONFIG["page_load_timeout"]
        self.implicit_wait = implicit_wait or BROWSER_CONFIG["implicit_wait"]
        self.screenshot_dir = screenshot_dir

        self.driver: Optional[webdriver.Chrome] = None
        self._initialize_driver()

    def _initialize_driver(self) -> None:
        """Initialize Chrome WebDriver with anti-detection features."""
        options = self._get_chrome_options()

        try:
            self.driver = webdriver.Chrome(options=options)
            self._configure_driver()
        except WebDriverException as e:
            raise BrowserError(f"Failed to initialize Chrome driver: {e}")

    def _get_chrome_options(self) -> Options:
        """Get Chrome options with anti-detection features."""
        options = Options()

        if self.headless:
            options.add_argument("--headless=new")

        # Window size
        options.add_argument(f"--window-size={self.window_width},{self.window_height}")

        # Disable automation detection flags
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        # Disable info bars
        options.add_argument("--disable-infobars")

        # Disable hardware acceleration
        options.add_argument("--disable-hardware-acceleration")

        # Disable software rasterizer
        options.add_argument("--disable-software-rasterizer")

        # Disable-dev-shm-usage for Docker/Linux
        options.add_argument("--disable-dev-shm-usage")

        # Disable GPU for stability
        options.add_argument("--disable-gpu")

        # Custom user agent
        options.add_argument(f"--user-agent={USER_AGENT}")

        # Language and locale
        options.add_argument("--lang=en-US")
        options.add_argument("--accept-lang=en-US,en;q=0.9")

        # Disable automation flags in prefs
        prefs = {
            "profile.default_content_setting_values.notifications": 2,
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
        }
        options.add_experimental_option("prefs", prefs)

        return options

    def _configure_driver(self) -> None:
        """Configure driver settings."""
        if self.driver is None:
            return

        # Set timeouts
        self.driver.set_page_load_timeout(self.page_load_timeout)
        self.driver.implicitly_wait(self.implicit_wait)

        # Execute CDP commands to hide automation
        self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
                window.chrome = {
                    runtime: {}
                };
            """
        })

    def get(self, url: str) -> None:
        """
        Navigate to URL.

        Args:
            url: URL to navigate to

        Raises:
            BrowserError: If navigation fails
            AntiBotDetectedError: If anti-bot detection is triggered
        """
        if self.driver is None:
            raise BrowserError("Browser driver not initialized")

        try:
            self.driver.get(url)
        except TimeoutException:
            raise BrowserError(f"Page load timeout for URL: {url}")
        except WebDriverException as e:
            self._handle_error(f"Failed to navigate to {url}: {e}")
            raise

    def wait_for_element(
        self,
        by: By,
        value: str,
        timeout: Optional[int] = None,
    ) -> Optional[webdriver.remote.webelement.WebElement]:
        """
        Wait for element to be present.

        Args:
            by: Selenium By locator type
            value: Locator value
            timeout: Wait timeout in seconds

        Returns:
            WebElement if found, None otherwise
        """
        if self.driver is None:
            raise BrowserError("Browser driver not initialized")

        timeout = timeout or self.page_load_timeout

        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return element
        except TimeoutException:
            return None

    def wait_for_clickable(
        self,
        by: By,
        value: str,
        timeout: Optional[int] = None,
    ) -> Optional[webdriver.remote.webelement.WebElement]:
        """
        Wait for element to be clickable.

        Args:
            by: Selenium By locator type
            value: Locator value
            timeout: Wait timeout in seconds

        Returns:
            WebElement if found, None otherwise
        """
        if self.driver is None:
            raise BrowserError("Browser driver not initialized")

        timeout = timeout or self.page_load_timeout

        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((by, value))
            )
            return element
        except TimeoutException:
            return None

    def find_element(
        self,
        by: By,
        value: str,
    ) -> Optional[webdriver.remote.webelement.WebElement]:
        """
        Find single element.

        Args:
            by: Selenium By locator type
            value: Locator value

        Returns:
            WebElement if found, None otherwise
        """
        if self.driver is None:
            raise BrowserError("Browser driver not initialized")

        try:
            return self.driver.find_element(by, value)
        except NoSuchElementException:
            return None

    def find_elements(
        self,
        by: By,
        value: str,
    ) -> list[webdriver.remote.webelement.WebElement]:
        """
        Find multiple elements.

        Args:
            by: Selenium By locator type
            value: Locator value

        Returns:
            List of WebElements (empty if none found)
        """
        if self.driver is None:
            raise BrowserError("Browser driver not initialized")

        try:
            return self.driver.find_elements(by, value)
        except NoSuchElementException:
            return []

    def execute_script(self, script: str, *args):
        """
        Execute JavaScript.

        Args:
            script: JavaScript code
            *args: Arguments to pass to script

        Returns:
            Script execution result
        """
        if self.driver is None:
            raise BrowserError("Browser driver not initialized")

        return self.driver.execute_script(script, *args)

    def take_screenshot(self, filename: str) -> Optional[Path]:
        """
        Take screenshot and save to file.

        Args:
            filename: Screenshot filename

        Returns:
            Path to saved screenshot, None if failed
        """
        if self.driver is None:
            return None

        if self.screenshot_dir:
            self.screenshot_dir.mkdir(parents=True, exist_ok=True)
            filepath = self.screenshot_dir / filename
        else:
            filepath = Path(filename)

        try:
            self.driver.save_screenshot(str(filepath))
            return filepath
        except WebDriverException:
            return None

    def _handle_error(self, message: str) -> None:
        """Handle error by taking screenshot."""
        if self.screenshot_dir:
            timestamp = int(time.time())
            self.take_screenshot(f"error_{timestamp}.png")

    def get_page_source(self) -> str:
        """
        Get current page source.

        Returns:
            Page source HTML
        """
        if self.driver is None:
            raise BrowserError("Browser driver not initialized")

        return self.driver.page_source

    def get_current_url(self) -> str:
        """
        Get current URL.

        Returns:
            Current URL
        """
        if self.driver is None:
            raise BrowserError("Browser driver not initialized")

        return self.driver.current_url

    def get_title(self) -> str:
        """
        Get page title.

        Returns:
            Page title
        """
        if self.driver is None:
            raise BrowserError("Browser driver not initialized")

        return self.driver.title

    def back(self) -> None:
        """Navigate back in browser history."""
        if self.driver is None:
            raise BrowserError("Browser driver not initialized")

        self.driver.back()

    def forward(self) -> None:
        """Navigate forward in browser history."""
        if self.driver is None:
            raise BrowserError("Browser driver not initialized")

        self.driver.forward()

    def refresh(self) -> None:
        """Refresh current page."""
        if self.driver is None:
            raise BrowserError("Browser driver not initialized")

        self.driver.refresh()

    def set_window_size(self, width: int, height: int) -> None:
        """
        Set browser window size.

        Args:
            width: Window width
            height: Window height
        """
        if self.driver is None:
            raise BrowserError("Browser driver not initialized")

        self.driver.set_window_size(width, height)

    def maximize_window(self) -> None:
        """Maximize browser window."""
        if self.driver is None:
            raise BrowserError("Browser driver not initialized")

        self.driver.maximize_window()

    def close(self) -> None:
        """Close current window."""
        if self.driver is not None:
            self.driver.close()

    def quit(self) -> None:
        """Quit browser and end session."""
        if self.driver is not None:
            self.driver.quit()
            self.driver = None

    def __enter__(self) -> "Browser":
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager."""
        self.quit()
