"""Base reader interface."""

from abc import ABC, abstractmethod
from typing import List

from img_fetch.core.product import Product


class BaseReader(ABC):
    """Abstract base class for file readers."""

    @abstractmethod
    def read(self, source: str) -> List[Product]:
        """
        Read products from a source.

        Args:
            source: File path or URL

        Returns:
            List of Product objects
        """
        pass

    @abstractmethod
    def supports(self, source: str) -> bool:
        """
        Check if this reader supports the given source.

        Args:
            source: File path or URL

        Returns:
            True if supported, False otherwise
        """
        pass
