"""Abstract fetcher interface."""

from abc import ABC, abstractmethod
from typing import List, Optional

from img_fetch.core.product import Product


class BaseFetcher(ABC):
    """Abstract base class for image fetchers."""

    @abstractmethod
    def fetch(self, product: Product) -> Optional[str]:
        """
        Fetch image for a product.

        Args:
            product: Product to fetch image for

        Returns:
            Path to saved image, or None if failed
        """
        pass

    @abstractmethod
    def supports(self, product: Product) -> bool:
        """
        Check if this fetcher supports the given product.

        Args:
            product: Product to check

        Returns:
            True if supported, False otherwise
        """
        pass

    @abstractmethod
    def can_retry(self) -> bool:
        """
        Check if this fetcher supports retries.

        Returns:
            True if retries are supported, False otherwise
        """
        pass

    def fetch_multiple(self, products: List[Product]) -> List[Product]:
        """
        Fetch images for multiple products.

        Args:
            products: List of products to fetch

        Returns:
            List of products with updated status
        """
        results = []
        for product in products:
            result = self.fetch(product)
            if result:
                product.status = "success"
                product.image_path = result
            else:
                product.status = "failed"
            results.append(product)
        return results

    def get_name(self) -> str:
        """
        Get fetcher name for logging.

        Returns:
            Fetcher name
        """
        return self.__class__.__name__
