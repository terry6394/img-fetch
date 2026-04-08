"""Configuration for img_fetch."""

from pathlib import Path
import os


# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
IMAGES_DIR = OUTPUT_DIR / "images"
CACHE_DIR = OUTPUT_DIR / "cache"

# Create output directories
OUTPUT_DIR.mkdir(exist_ok=True)
IMAGES_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)


# Brand to official website mapping
BRAND_WEBSITES = {
    "CANADA_GOOSE": "https://www.canadagoose.com",
    "HAGLOFS": "https://www.haglofs.com",
    "HELLY_HANSEN": "https://www.hellyhansen.com",
    "STONE_ISLAND": "https://www.stoneisland.com",
    "L.I.M": "https://www.limitstorem.com",
}

# E-commerce platforms
ECOMMERCE_SITES = {
    "amazon": "https://www.amazon.com",
    "jd": "https://www.jd.com",
    "taobao": "https://www.taobao.com",
}

# Image source priority
IMAGE_SOURCE_PRIORITY = [
    "brand_site",
    "ecommerce",
    "image_search",
]

# Rate limiting (requests per minute per domain)
RATE_LIMITS = {
    "canadagoose.com": 2,
    "haglofs.com": 3,
    "hellyhansen.com": 3,
    "stoneisland.com": 3,
    "amazon.com": 10,
    "jd.com": 5,
    "taobao.com": 3,
    "youzan.com": 30,
}

# Browser settings
BROWSER_CONFIG = {
    "headless": True,
    "window_width": 1920,
    "window_height": 1080,
    "page_load_timeout": 30,
    "implicit_wait": 10,
}

# Retry settings
MAX_RETRIES = 3
RETRY_DELAYS = [5, 15, 30]  # seconds

# Human behavior settings
HUMAN_BEHAVIOR_CONFIG = {
    "min_action_delay": 1.0,  # seconds
    "max_action_delay": 3.0,
    "min_scroll_pause": 0.5,
    "max_scroll_pause": 1.5,
    "mouse_move_steps": 10,
}

# Anthropic API settings
ANTHROPIC_CONFIG = {
    "model": "claude-3-5-sonnet-20241022",
    "max_tokens": 1024,
}

# File naming
MAX_FILENAME_LENGTH = 200
FORBIDDEN_CHARS = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
