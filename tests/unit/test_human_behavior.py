"""Unit tests for human_behavior module."""

import pytest
from unittest.mock import Mock, MagicMock, patch, PropertyMock
import time
from selenium.webdriver.common.by import By

from img_fetch.automation.human_behavior import HumanBehavior
from img_fetch.automation.browser import Browser


class TestHumanBehavior:
    """Tests for HumanBehavior class."""

    @pytest.fixture
    def mock_browser(self):
        """Create a mock Browser instance."""
        browser = Mock(spec=Browser)
        browser.driver = Mock()
        browser.execute_script = Mock(return_value={"width": 1920, "height": 1080})
        return browser

    @pytest.fixture
    def human_behavior(self, mock_browser):
        """Create HumanBehavior instance with mocked browser."""
        return HumanBehavior(
            browser=mock_browser,
            min_action_delay=0.01,
            max_action_delay=0.02,
            min_scroll_pause=0.01,
            max_scroll_pause=0.02,
            mouse_move_steps=5,
        )

    def test_random_delay_returns_float(self, human_behavior):
        """Test random_delay returns a float."""
        delay = human_behavior.random_delay()
        assert isinstance(delay, float)
        assert 0.01 <= delay <= 0.02

    def test_random_delay_with_custom_range(self, human_behavior):
        """Test random_delay with custom range."""
        delay = human_behavior.random_delay(min_delay=0.5, max_delay=1.0)
        assert 0.5 <= delay <= 1.0

    def test_move_mouse_randomly(self, human_behavior, mock_browser):
        """Test mouse movement with mocked browser."""
        mock_action_chains = Mock()
        human_behavior._action_chains = mock_action_chains

        human_behavior.move_mouse_randomly()

        mock_action_chains.move_by_offset.assert_called()
        mock_action_chains.perform.assert_called_once()

    def test_move_mouse_randomly_with_coordinates(self, human_behavior, mock_browser):
        """Test mouse movement with specified coordinates."""
        mock_action_chains = Mock()
        human_behavior._action_chains = mock_action_chains

        human_behavior.move_mouse_randomly(start_x=100, start_y=100, end_x=200, end_y=200)

        # Should have moved to start position and then to end
        assert mock_action_chains.move_by_offset.call_count >= 1
        mock_action_chains.perform.assert_called_once()

    def test_hover_element(self, human_behavior, mock_browser):
        """Test hovering over element."""
        mock_element = Mock()
        mock_action_chains = Mock()
        # move_to_element returns self (ActionChains) for chaining
        mock_action_chains.move_to_element.return_value = mock_action_chains
        human_behavior._action_chains = mock_action_chains

        human_behavior.hover_element(mock_element)

        mock_action_chains.move_to_element.assert_called_with(mock_element)
        mock_action_chains.perform.assert_called_once()

    def test_click_element(self, human_behavior, mock_browser):
        """Test clicking element with delay and hover."""
        mock_element = Mock()
        mock_action_chains = Mock()
        # move_to_element returns self (ActionChains) for chaining
        mock_action_chains.move_to_element.return_value = mock_action_chains
        human_behavior._action_chains = mock_action_chains

        with patch.object(human_behavior, 'random_delay') as mock_delay:
            mock_delay.return_value = 0.01
            human_behavior.click_element(mock_element)

        mock_action_chains.move_to_element.assert_called_with(mock_element)
        mock_action_chains.perform.assert_called()
        mock_element.click.assert_called_once()

    def test_scroll_by(self, human_behavior, mock_browser):
        """Test scrolling by pixels."""
        with patch.object(human_behavior, 'random_delay') as mock_delay:
            mock_delay.return_value = 0.01
            human_behavior.scroll_by(500)

        mock_browser.execute_script.assert_called_with("window.scrollBy(0, 500);")

    def test_scroll_by_no_pause(self, human_behavior, mock_browser):
        """Test scrolling without pauses."""
        human_behavior.scroll_by(500, pause_before=False, pause_after=False)

        mock_browser.execute_script.assert_called_with("window.scrollBy(0, 500);")

    def test_scroll_to_element(self, human_behavior, mock_browser):
        """Test scrolling to element."""
        mock_element = Mock()

        with patch.object(human_behavior, 'random_delay') as mock_delay:
            mock_delay.return_value = 0.01
            human_behavior.scroll_to_element(mock_element)

        call_args = mock_browser.execute_script.call_args[0]
        assert "scrollIntoView" in call_args[0]

    def test_scroll_page_down(self, human_behavior, mock_browser):
        """Test scrolling page down."""
        mock_browser.execute_script.return_value = 1080  # viewport height

        with patch.object(human_behavior, 'random_delay') as mock_delay:
            mock_delay.return_value = 0.01
            human_behavior.scroll_page(1.0, "down")

        # Should have called scrollBy multiple times
        assert mock_browser.execute_script.call_count >= 3

    def test_scroll_page_up(self, human_behavior, mock_browser):
        """Test scrolling page up."""
        mock_browser.execute_script.return_value = 1080

        with patch.object(human_behavior, 'random_delay') as mock_delay:
            mock_delay.return_value = 0.01
            human_behavior.scroll_page(1.0, "up")

        # Should have called scrollBy with negative values
        calls = mock_browser.execute_script.call_args_list
        for call in calls:
            if "scrollBy" in call[0][0]:
                assert "-" in call[0][0] or "0, -" in call[0][0]

    def test_scroll_to_top(self, human_behavior, mock_browser):
        """Test scrolling to top."""
        with patch.object(human_behavior, 'random_delay') as mock_delay:
            mock_delay.return_value = 0.01
            human_behavior.scroll_to_top()

        mock_browser.execute_script.assert_called_with("window.scrollTo(0, 0);")

    def test_scroll_to_bottom(self, human_behavior, mock_browser):
        """Test scrolling to bottom."""
        mock_browser.execute_script.return_value = "document height"

        with patch.object(human_behavior, 'random_delay') as mock_delay:
            mock_delay.return_value = 0.01
            human_behavior.scroll_to_bottom()

        mock_browser.execute_script.assert_called_with(
            "window.scrollTo(0, document.body.scrollHeight);"
        )

    def test_random_scroll(self, human_behavior, mock_browser):
        """Test random scroll."""
        mock_browser.execute_script.return_value = 1080

        with patch.object(human_behavior, 'random_delay') as mock_delay:
            mock_delay.return_value = 0.01
            human_behavior.random_scroll(min_pages=0.5, max_pages=1.0)

        assert mock_browser.execute_script.call_count >= 1

    def test_change_viewport(self, human_behavior, mock_browser):
        """Test changing viewport size."""
        human_behavior.change_viewport(width=1366, height=768)

        mock_browser.set_window_size.assert_called_with(1366, 768)

    def test_change_viewport_random(self, human_behavior, mock_browser):
        """Test changing viewport with random values."""
        human_behavior.change_viewport()

        mock_browser.set_window_size.assert_called_once()
        width, height = mock_browser.set_window_size.call_args[0]
        assert width > 0
        assert height > 0

    def test_mimic_reading(self, human_behavior, mock_browser):
        """Test reading simulation."""
        mock_browser.execute_script.return_value = 1080
        start_time = time.time()

        with patch.object(human_behavior, 'random_delay') as mock_delay:
            mock_delay.return_value = 0.01
            human_behavior.mimic_reading(min_seconds=0.1, max_seconds=0.2)

        elapsed = time.time() - start_time
        assert elapsed >= 0.1

    def test_human_search_finds_element(self, human_behavior, mock_browser):
        """Test human search when element is found."""
        mock_element = Mock()
        mock_browser.find_element.return_value = mock_element

        result = human_behavior.human_search(By.CSS_SELECTOR, ".product img")

        assert result == mock_element

    def test_human_search_scrolls_if_not_found(self, human_behavior, mock_browser):
        """Test human search scrolls if element not found initially."""
        mock_browser.find_element.return_value = None
        mock_browser.execute_script.return_value = 1080

        with patch.object(human_behavior, 'random_delay') as mock_delay:
            mock_delay.return_value = 0.01
            result = human_behavior.human_search(By.CSS_SELECTOR, ".product img", max_attempts=2)

        assert result is None

    def test_human_search_finds_after_scroll(self, human_behavior, mock_browser):
        """Test human search finds element after scrolling."""
        mock_element = Mock()
        # First call returns None, second returns element
        mock_browser.find_element.side_effect = [None, None, None, mock_element]
        mock_browser.execute_script.return_value = 1080

        with patch.object(human_behavior, 'random_delay') as mock_delay:
            mock_delay.return_value = 0.01
            result = human_behavior.human_search(By.CSS_SELECTOR, ".product img", max_attempts=2)

        assert result == mock_element

    def test_action_chains_reuse(self, human_behavior, mock_browser):
        """Test that ActionChains instance is reused."""
        mock_action_chains = Mock()
        human_behavior._action_chains = mock_action_chains

        action1 = human_behavior._get_action_chains()
        action2 = human_behavior._get_action_chains()

        assert action1 is action2

    def test_browser_driver_none_returns_early(self, human_behavior):
        """Test methods return early if driver is None."""
        human_behavior.browser.driver = None

        # Should not raise, just return
        human_behavior.move_mouse_randomly()
        human_behavior.scroll_page()
        human_behavior.change_viewport()


class TestHumanBehaviorConfiguration:
    """Tests for HumanBehavior configuration."""

    def test_default_configuration(self, mock_browser):
        """Test default configuration is loaded from HUMAN_BEHAVIOR_CONFIG."""
        with patch('img_fetch.automation.human_behavior.HUMAN_BEHAVIOR_CONFIG', {
            "min_action_delay": 1.0,
            "max_action_delay": 3.0,
            "min_scroll_pause": 0.5,
            "max_scroll_pause": 1.5,
            "mouse_move_steps": 10,
        }):
            hb = HumanBehavior(mock_browser)

            assert hb.min_action_delay == 1.0
            assert hb.max_action_delay == 3.0
            assert hb.min_scroll_pause == 0.5
            assert hb.max_scroll_pause == 1.5
            assert hb.mouse_move_steps == 10

    def test_custom_configuration(self, mock_browser):
        """Test custom configuration overrides defaults."""
        hb = HumanBehavior(
            browser=mock_browser,
            min_action_delay=0.5,
            max_action_delay=1.0,
            min_scroll_pause=0.1,
            max_scroll_pause=0.2,
            mouse_move_steps=5,
        )

        assert hb.min_action_delay == 0.5
        assert hb.max_action_delay == 1.0
        assert hb.min_scroll_pause == 0.1
        assert hb.max_scroll_pause == 0.2
        assert hb.mouse_move_steps == 5


# Helper for creating mock browser
@pytest.fixture
def mock_browser():
    """Create a mock Browser instance."""
    browser = Mock(spec=Browser)
    browser.driver = Mock()
    browser.execute_script = Mock(return_value={"width": 1920, "height": 1080})
    return browser
