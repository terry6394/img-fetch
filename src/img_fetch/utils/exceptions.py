"""Custom exceptions for img_fetch."""


class ImgFetchError(Exception):
    """Base exception for img_fetch."""
    pass


class UnsupportedSourceError(ImgFetchError):
    """Raised when the input source type is not supported."""
    pass


class ImageNotFoundError(ImgFetchError):
    """Raised when an image cannot be found after trying all sources."""
    pass


class AntiBotDetectedError(ImgFetchError):
    """Raised when anti-bot detection is triggered."""
    pass


class NetworkError(ImgFetchError):
    """Raised when a network request fails."""
    pass


class BrowserError(ImgFetchError):
    """Raised when browser automation fails."""
    pass


class ProductParseError(ImgFetchError):
    """Raised when a product cannot be parsed from input."""
    pass


class RateLimitError(ImgFetchError):
    """Raised when rate limit is exceeded."""
    pass
