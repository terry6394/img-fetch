"""Human-like behavior simulation for browser automation."""

import random
import time
from typing import Optional, Tuple

from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

from img_fetch.config import HUMAN_BEHAVIOR_CONFIG
from img_fetch.automation.browser import Browser


class HumanBehavior:
    """
    Simulates human-like behavior to avoid bot detection.

    Features:
    - Random delays between actions
    - Random mouse movements
    - Human-like scrolling
    - Random viewport changes
    """

    def __init__(
        self,
        browser: Browser,
        min_action_delay: float = None,
        max_action_delay: float = None,
        min_scroll_pause: float = None,
        max_scroll_pause: float = None,
        mouse_move_steps: int = None,
    ):
        """
        Initialize human behavior simulator.

        Args:
            browser: Browser instance to simulate behavior on
            min_action_delay: Minimum delay between actions (seconds)
            max_action_delay: Maximum delay between actions (seconds)
            min_scroll_pause: Minimum pause during scroll (seconds)
            max_scroll_pause: Maximum pause during scroll (seconds)
            mouse_move_steps: Number of steps for mouse movement
        """
        self.browser = browser
        config = HUMAN_BEHAVIOR_CONFIG

        self.min_action_delay = min_action_delay or config["min_action_delay"]
        self.max_action_delay = max_action_delay or config["max_action_delay"]
        self.min_scroll_pause = min_scroll_pause or config["min_scroll_pause"]
        self.max_scroll_pause = max_scroll_pause or config["max_scroll_pause"]
        self.mouse_move_steps = mouse_move_steps or config["mouse_move_steps"]

        self._action_chains: Optional[ActionChains] = None

    def _get_action_chains(self) -> ActionChains:
        """Get or create ActionChains instance."""
        if self._action_chains is None:
            self._action_chains = ActionChains(self.browser.driver)
        return self._action_chains

    def random_delay(self, min_delay: float = None, max_delay: float = None) -> float:
        """
        Wait for a random duration.

        Args:
            min_delay: Minimum delay (uses default if None)
            max_delay: Maximum delay (uses default if None)

        Returns:
            Actual delay in seconds
        """
        min_d = min_delay if min_delay is not None else self.min_action_delay
        max_d = max_delay if max_delay is not None else self.max_action_delay
        delay = random.uniform(min_d, max_d)
        time.sleep(delay)
        return delay

    def move_mouse_randomly(
        self,
        start_x: Optional[int] = None,
        start_y: Optional[int] = None,
        end_x: Optional[int] = None,
        end_y: Optional[int] = None,
    ) -> None:
        """
        Move mouse in a random, human-like path.

        Args:
            start_x: Starting X coordinate (random if None)
            start_y: Starting Y coordinate (random if None)
            end_x: Ending X coordinate (random if None)
            end_y: Ending Y coordinate (random if None)
        """
        if self.browser.driver is None:
            return

        # Get viewport dimensions
        viewport = self.browser.execute_script(
            "return { width: window.innerWidth, height: window.innerHeight }"
        )

        # Generate random coordinates if not provided
        start_x = start_x if start_x is not None else random.randint(0, viewport["width"])
        start_y = start_y if start_y is not None else random.randint(0, viewport["height"])
        end_x = end_x if end_x is not None else random.randint(0, viewport["width"])
        end_y = end_y if end_y is not None else random.randint(0, viewport["height"])

        # Create bezier curve points for natural movement
        action = self._get_action_chains()
        action.move_by_offset(start_x, start_y)

        # Add random intermediate points
        mid_x = (start_x + end_x) // 2 + random.randint(-50, 50)
        mid_y = (start_y + end_y) // 2 + random.randint(-50, 50)

        for step in range(self.mouse_move_steps):
            progress = step / self.mouse_move_steps
            # Use quadratic bezier curve for natural movement
            t = progress
            x = int((1 - t) ** 2 * start_x + 2 * (1 - t) * t * mid_x + t ** 2 * end_x)
            y = int((1 - t) ** 2 * start_y + 2 * (1 - t) * t * mid_y + t ** 2 * end_y)
            action.move_by_offset(x - start_x, y - start_y)
            start_x, start_y = x, y

        action.perform()
        self.random_delay(0.05, 0.15)

    def hover_element(self, element: WebElement) -> None:
        """
        Hover over an element with human-like movement.

        Args:
            element: WebElement to hover over
        """
        if self.browser.driver is None:
            return

        action = self._get_action_chains()
        action.move_to_element(element).perform()
        self.random_delay(0.1, 0.3)

    def click_element(self, element: WebElement) -> None:
        """
        Click an element with human-like delay and movement.

        Args:
            element: WebElement to click
        """
        if self.browser.driver is None:
            return

        self.random_delay()
        self.hover_element(element)
        self.random_delay(0.1, 0.2)
        element.click()

    def scroll_by(
        self,
        pixels: int,
        pause_before: bool = True,
        pause_after: bool = True,
    ) -> None:
        """
        Scroll by a specific number of pixels.

        Args:
            pixels: Number of pixels to scroll
            pause_before: Add random pause before scrolling
            pause_after: Add random pause after scrolling
        """
        if pause_before:
            self.random_delay(self.min_scroll_pause, self.max_scroll_pause)

        self.browser.execute_script(f"window.scrollBy(0, {pixels});")

        if pause_after:
            self.random_delay(self.min_scroll_pause, self.max_scroll_pause)

    def scroll_to_element(self, element: WebElement) -> None:
        """
        Scroll to bring element into view.

        Args:
            element: WebElement to scroll to
        """
        if self.browser.driver is None:
            return

        self.browser.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
        self.random_delay(0.5, 1.0)

    def scroll_page(
        self,
        pages: float = 1.0,
        direction: str = "down",
    ) -> None:
        """
        Scroll by approximate number of page heights.

        Args:
            pages: Number of page heights to scroll (can be fractional)
            direction: 'up' or 'down'
        """
        if self.browser.driver is None:
            return

        viewport_height = self.browser.execute_script("return window.innerHeight;")
        scroll_amount = int(viewport_height * pages)

        if direction == "up":
            scroll_amount = -scroll_amount

        # Scroll in smaller increments for more human-like behavior
        increments = max(3, int(pages * 3))
        per_increment = scroll_amount // increments

        for _ in range(increments):
            self.scroll_by(per_increment)
            self.random_delay(0.1, 0.3)

    def scroll_to_top(self) -> None:
        """Scroll to top of page."""
        if self.browser.driver is None:
            return

        self.browser.execute_script("window.scrollTo(0, 0);")
        self.random_delay(0.3, 0.5)

    def scroll_to_bottom(self) -> None:
        """Scroll to bottom of page."""
        if self.browser.driver is None:
            return

        self.browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        self.random_delay(0.3, 0.5)

    def random_scroll(self, min_pages: float = 0.5, max_pages: float = 2.0) -> None:
        """
        Scroll a random amount.

        Args:
            min_pages: Minimum pages to scroll
            max_pages: Maximum pages to scroll
        """
        pages = random.uniform(min_pages, max_pages)
        direction = random.choice(["up", "down"])
        self.scroll_page(pages, direction)

    def change_viewport(self, width: Optional[int] = None, height: Optional[int] = None) -> None:
        """
        Change browser viewport size.

        Args:
            width: New viewport width (random if None)
            height: New viewport height (random if None)
        """
        if self.browser.driver is None:
            return

        # Standard viewport sizes
        standard_widths = [375, 768, 1024, 1280, 1366, 1440, 1920]
        standard_heights = [667, 768, 800, 900, 1000, 1080, 1200]

        width = width or random.choice(standard_widths)
        height = height or random.choice(standard_heights)

        self.browser.set_window_size(width, height)
        self.random_delay(0.2, 0.5)

    def mimic_reading(self, min_seconds: float = 2.0, max_seconds: float = 5.0) -> None:
        """
        Simulate reading behavior with small movements.

        Args:
            min_seconds: Minimum reading time
            max_seconds: Maximum reading time
        """
        if self.browser.driver is None:
            return

        start_time = time.time()
        target_duration = random.uniform(min_seconds, max_seconds)

        while time.time() - start_time < target_duration:
            # Small random scroll
            self.random_scroll(0.2, 0.5)
            self.random_delay(0.5, 1.5)

    def human_search(
        self,
        by: By,
        value: str,
        max_attempts: int = 3,
    ) -> Optional[WebElement]:
        """
        Search for element with human-like scrolling and clicking.

        Args:
            by: Selenium By locator type
            value: Locator value
            max_attempts: Maximum scroll/search attempts

        Returns:
            Found WebElement or None
        """
        for attempt in range(max_attempts):
            element = self.browser.find_element(by, value)
            if element:
                return element

            # Scroll down a bit before next attempt
            self.scroll_page(1.0, "down")

        # Try scrolling back to top
        self.scroll_to_top()
        for _ in range(max_attempts):
            element = self.browser.find_element(by, value)
            if element:
                return element
            self.scroll_page(1.0, "down")

        return None
