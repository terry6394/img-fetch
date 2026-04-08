"""LLM-powered search strategy planner."""

import json
from typing import Optional

import anthropic

from img_fetch.config import ANTHROPIC_CONFIG, BRAND_WEBSITES, IMAGE_SOURCE_PRIORITY


class SearchStrategyPlanner:
    """Uses LLM to decide optimal search strategy for product images."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the planner.

        Args:
            api_key: Anthropic API key. If not provided, will try to get from env.
        """
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = ANTHROPIC_CONFIG["model"]
        self.max_tokens = ANTHROPIC_CONFIG["max_tokens"]

    def plan_search_strategy(
        self,
        product_name: str,
        product_spec: str = "",
        brand: str = "",
        known_product_url: str = "",
    ) -> dict:
        """Decide the optimal search strategy for a product.

        Args:
            product_name: Name of the product
            product_spec: Product specification/variant
            brand: Brand name (if known)
            known_product_url: Direct URL to product page (if known)

        Returns:
            JSON dict with search strategy containing:
            - search_query: The refined search query to use
            - sources_to_try: Ordered list of source types to try
            - source_details: Dict with details for each source
            - reasoning: Brief explanation of the strategy
        """
        prompt = self._build_strategy_prompt(
            product_name, product_spec, brand, known_product_url
        )

        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )

        return self._parse_strategy_response(response.content[0].text)

    def _build_strategy_prompt(
        self,
        product_name: str,
        product_spec: str,
        brand: str,
        known_product_url: str,
    ) -> str:
        """Build the prompt for strategy planning."""
        brand_list = ", ".join(BRAND_WEBSITES.keys())
        source_priority = ", ".join(IMAGE_SOURCE_PRIORITY)

        prompt = f"""You are a search strategy planner for product image fetching.

Given the following product information, decide the optimal search strategy:

Product Name: {product_name}
Product Spec: {product_spec or 'Not specified'}
Brand: {brand or 'Not specified'}
Known Product URL: {known_product_url or 'Not provided'}

Available brands: {brand_list}
Source priority order: {source_priority}

Possible sources to choose from:
- brand_site: Official brand website (highest priority if brand is known)
- ecommerce: E-commerce platforms like Amazon, JD, Taobao
- image_search: Google/Bing image search (fallback option)

Output a JSON object with the following structure:
{{
    "search_query": "refined search query combining product name and spec",
    "sources_to_try": ["source1", "source2", "source3"],
    "source_details": {{
        "brand_site": {{
            "enabled": true/false,
            "search_terms": "terms to search on brand site",
            "direct_url": "if known, direct product URL"
        }},
        "ecommerce": {{
            "enabled": true/false,
            "platforms": ["platform1", "platform2"],
            "search_terms": "terms to search"
        }},
        "image_search": {{
            "enabled": true/false,
            "search_query": "optimized image search query"
        }}
    }},
    "reasoning": "brief explanation of why this strategy was chosen"
}}

Output ONLY the JSON object, no additional text."""

        return prompt

    def _parse_strategy_response(self, response_text: str) -> dict:
        """Parse the LLM response into a strategy dict."""
        # Try to extract JSON from the response
        text = response_text.strip()

        # Handle cases where the response might have markdown code blocks
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            text = text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            text = text[start:end].strip()

        try:
            strategy = json.loads(text)
            # Validate required fields
            if "search_query" not in strategy:
                strategy["search_query"] = ""
            if "sources_to_try" not in strategy:
                strategy["sources_to_try"] = IMAGE_SOURCE_PRIORITY.copy()
            if "source_details" not in strategy:
                strategy["source_details"] = {}
            if "reasoning" not in strategy:
                strategy["reasoning"] = ""
            return strategy
        except json.JSONDecodeError:
            # Return a default strategy on parse failure
            return {
                "search_query": "",
                "sources_to_try": IMAGE_SOURCE_PRIORITY.copy(),
                "source_details": {},
                "reasoning": "Failed to parse LLM response, using default strategy",
            }


def create_search_strategy(
    product_name: str,
    product_spec: str = "",
    brand: str = "",
    known_product_url: str = "",
) -> dict:
    """Convenience function to create a search strategy.

    Args:
        product_name: Name of the product
        product_spec: Product specification/variant
        brand: Brand name (if known)
        known_product_url: Direct URL to product page (if known)

    Returns:
        Search strategy dict
    """
    planner = SearchStrategyPlanner()
    return planner.plan_search_strategy(
        product_name=product_name,
        product_spec=product_spec,
        brand=brand,
        known_product_url=known_product_url,
    )
