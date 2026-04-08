"""Factory for creating readers with auto-discovery."""

import logging
from pathlib import Path
from typing import List, Optional

from .base import BaseReader

logger = logging.getLogger(__name__)


class ReaderFactory:
    """Factory for creating appropriate readers based on file type."""

    _readers: List[type[BaseReader]] = []
    _instance: Optional["ReaderFactory"] = None

    def __init__(self):
        """Initialize the factory with auto-discovery of readers."""
        self._reader_cache: dict[str, BaseReader] = {}
        self._discover_readers()

    @classmethod
    def get_instance(cls) -> "ReaderFactory":
        """Get singleton instance of the factory."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _discover_readers(self) -> None:
        """Auto-discover and register readers."""
        # Import all known reader types
        from .excel_reader import ExcelReader
        from .csv_reader import CsvReader
        from .json_reader import JsonReader

        self._readers = [
            ExcelReader,
            CsvReader,
            JsonReader,
        ]
        logger.debug(f"Discovered {len(self._readers)} readers: {[r.__name__ for r in self._readers]}")

    def register_reader(self, reader_class: type[BaseReader]) -> None:
        """
        Register a new reader class.

        Args:
            reader_class: A reader class that extends BaseReader
        """
        if reader_class not in self._readers:
            self._readers.append(reader_class)
            logger.debug(f"Registered reader: {reader_class.__name__}")

    def create_reader(self, source: str) -> Optional[BaseReader]:
        """
        Create an appropriate reader for the given source.

        Args:
            source: File path or URL

        Returns:
            A reader instance that supports the source, or None
        """
        # Check cache first
        source_lower = source.lower()
        if source_lower in self._reader_cache:
            return self._reader_cache[source_lower]

        # Find a reader that supports this source
        for reader_class in self._readers:
            reader = reader_class()
            if reader.supports(source):
                self._reader_cache[source_lower] = reader
                logger.debug(f"Selected reader {reader_class.__name__} for {source}")
                return reader

        logger.warning(f"No reader found for source: {source}")
        return None

    def read(self, source: str) -> List:
        """
        Read products from a source using the appropriate reader.

        Args:
            source: File path or URL

        Returns:
            List of Product objects
        """
        reader = self.create_reader(source)
        if reader is None:
            return []
        return reader.read(source)

    @property
    def available_readers(self) -> List[str]:
        """Get list of available reader names."""
        return [r.__name__ for r in self._readers]


def get_reader(source: str) -> Optional[BaseReader]:
    """
    Convenience function to get a reader for a source.

    Args:
        source: File path or URL

    Returns:
        A reader instance that supports the source, or None
    """
    return ReaderFactory.get_instance().create_reader(source)


def read_products(source: str) -> List:
    """
    Convenience function to read products from a source.

    Args:
        source: File path or URL

    Returns:
        List of Product objects
    """
    return ReaderFactory.get_instance().read(source)
