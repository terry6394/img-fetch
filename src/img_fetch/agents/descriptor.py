"""Page description extractor."""

from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

import httpx


@dataclass
class PageDescription:
    """Extracted description from a product page."""
    title: str = ""
    description: str = ""
    keywords: list[str] = None
    alt_text: list[str] = None
    domain: str = ""

    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []
        if self.alt_text is None:
            self.alt_text = []


class DescriptionExtractor:
    """Extracts title, description, keywords, and alt text from product pages."""

    def __init__(self, timeout: float = 10.0):
        """Initialize the extractor.

        Args:
            timeout: HTTP request timeout in seconds
        """
        self.timeout = timeout

    async def extract_from_url(self, url: str) -> PageDescription:
        """Extract description metadata from a URL.

        Args:
            url: The page URL to extract from

        Returns:
            PageDescription with extracted data
        """
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=self.timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
                html_content = response.text
                content_type = response.headers.get("content-type", "")

                domain = urlparse(url).netloc

                # Only parse HTML pages
                if "text/html" in content_type or not content_type:
                    return self._extract_from_html(html_content, domain)
                else:
                    # For non-HTML content, return minimal description
                    return PageDescription(domain=domain)
        except Exception:
            return PageDescription()

    def _extract_from_html(self, html: str, domain: str) -> PageDescription:
        """Extract metadata from HTML content.

        Args:
            html: HTML content
            domain: Domain name for the page

        Returns:
            PageDescription with extracted data
        """
        # Simple regex-based extraction for common meta tags
        # In production, consider using a proper HTML parser like BeautifulSoup

        title = self._extract_title(html)
        description = self._extract_meta_description(html)
        keywords = self._extract_meta_keywords(html)
        alt_texts = self._extract_img_alts(html)

        return PageDescription(
            title=title,
            description=description,
            keywords=keywords,
            alt_text=alt_texts,
            domain=domain,
        )

    def _extract_title(self, html: str) -> str:
        """Extract page title from HTML."""
        import re
        # Try <title> tag first
        match = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
        if match:
            return match.group(1).strip()

        # Try og:title
        match = re.search(
            r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']',
            html,
            re.IGNORECASE,
        )
        if match:
            return match.group(1).strip()

        # Try alternative og:title format
        match = re.search(
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:title["\']',
            html,
            re.IGNORECASE,
        )
        if match:
            return match.group(1).strip()

        return ""

    def _extract_meta_description(self, html: str) -> str:
        """Extract meta description from HTML."""
        import re
        # Try name="description"
        match = re.search(
            r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']',
            html,
            re.IGNORECASE,
        )
        if match:
            return match.group(1).strip()

        # Try alternative format
        match = re.search(
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']description["\']',
            html,
            re.IGNORECASE,
        )
        if match:
            return match.group(1).strip()

        # Try og:description
        match = re.search(
            r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\']([^"\']+)["\']',
            html,
            re.IGNORECASE,
        )
        if match:
            return match.group(1).strip()

        return ""

    def _extract_meta_keywords(self, html: str) -> list[str]:
        """Extract meta keywords from HTML."""
        import re
        match = re.search(
            r'<meta[^>]+name=["\']keywords["\'][^>]+content=["\']([^"\']+)["\']',
            html,
            re.IGNORECASE,
        )
        if match:
            keywords_str = match.group(1).strip()
            return [k.strip() for k in keywords_str.split(",")]

        # Try alternative format
        match = re.search(
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']keywords["\']',
            html,
            re.IGNORECASE,
        )
        if match:
            keywords_str = match.group(1).strip()
            return [k.strip() for k in keywords_str.split(",")]

        return []

    def _extract_img_alts(self, html: str) -> list[str]:
        """Extract alt text from all img tags in HTML."""
        import re
        alt_texts = []
        # Find all img tags with alt attribute
        matches = re.findall(r'<img[^>]+alt=["\']([^"\']*)["\'][^>]*>', html, re.IGNORECASE)
        for alt in matches:
            if alt.strip():
                alt_texts.append(alt.strip())

        # Also try img tags where alt comes before src
        matches = re.findall(
            r'<img[^>]+alt=["\']([^"\']*)["\'][^>]*>', html, re.IGNORECASE
        )
        for alt in matches:
            if alt.strip() and alt.strip() not in alt_texts:
                alt_texts.append(alt.strip())

        return alt_texts


async def extract_page_description(url: str) -> PageDescription:
    """Convenience function to extract page description.

    Args:
        url: The page URL to extract from

    Returns:
        PageDescription with extracted data
    """
    extractor = DescriptionExtractor()
    return await extractor.extract_from_url(url)
