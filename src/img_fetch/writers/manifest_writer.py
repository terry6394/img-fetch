"""Task progress tracking with manifest.json."""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from img_fetch.core.product import Product


class ManifestWriter:
    """Manages task progress tracking via manifest.json."""

    MANIFEST_FILENAME = "manifest.json"

    def __init__(self, output_dir: Optional[Path] = None):
        """Initialize the manifest writer.

        Args:
            output_dir: Directory for output files. Defaults to config OUTPUT_DIR.
        """
        if output_dir is None:
            from img_fetch.config import OUTPUT_DIR
            output_dir = OUTPUT_DIR
        self.output_dir = Path(output_dir)
        self.manifest_path = self.output_dir / self.MANIFEST_FILENAME

    def write_manifest(
        self,
        products: list[Product],
        task_status: str = "in_progress",
    ) -> None:
        """Write manifest with current task state.

        Args:
            products: List of products to track
            task_status: Overall task status (pending, in_progress, completed, failed)
        """
        manifest = self._build_manifest(products, task_status)
        self.manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))

    def _build_manifest(
        self,
        products: list[Product],
        task_status: str,
    ) -> dict:
        """Build manifest dictionary from products."""
        product_summaries = []
        for p in products:
            product_summaries.append({
                "excel_row": p.excel_row,
                "name": p.name,
                "spec": p.spec,
                "brand": p.brand,
                "status": p.status,
                "image_path": str(p.image_path) if p.image_path else "",
                "error_message": p.error_message,
                "tried_sources": p.tried_sources,
                "attempts": [
                    {
                        "source": a.source,
                        "status": a.status,
                        "url": a.url,
                        "error": a.error,
                    }
                    for a in p.attempts
                ],
            })

        return {
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "task_status": task_status,
            "total_products": len(products),
            "pending_count": sum(1 for p in products if p.status == "pending"),
            "success_count": sum(1 for p in products if p.status == "success"),
            "failed_count": sum(1 for p in products if p.status == "failed"),
            "skipped_count": sum(1 for p in products if p.status == "skipped"),
            "products": product_summaries,
        }

    def load_manifest(self) -> Optional[dict]:
        """Load existing manifest if present.

        Returns:
            Manifest dict or None if not found
        """
        if not self.manifest_path.exists():
            return None

        try:
            content = self.manifest_path.read_text()
            return json.loads(content)
        except (json.JSONDecodeError, IOError):
            return None

    def get_resumable_products(
        self,
        all_products: list[Product],
    ) -> tuple[list[Product], list[Product]]:
        """Get products that can be resumed and those that are new.

        Args:
            all_products: All products to process

        Returns:
            Tuple of (resumable_products, new_products)
        """
        manifest = self.load_manifest()
        if manifest is None:
            return [], all_products

        # Build map of existing product states by excel_row
        existing_states = {}
        for p_data in manifest.get("products", []):
            excel_row = p_data.get("excel_row")
            if excel_row is not None:
                existing_states[excel_row] = p_data

        resumable = []
        new_products = []

        for product in all_products:
            if product.excel_row in existing_states:
                state = existing_states[product.excel_row]
                # Only resume if not already succeeded
                if state.get("status") != "success":
                    # Update product state from manifest
                    product.status = state.get("status", "pending")
                    product.error_message = state.get("error_message", "")
                    product.tried_sources = state.get("tried_sources", [])
                    # Reconstruct attempts
                    product.attempts = []
                    for attempt_data in state.get("attempts", []):
                        from img_fetch.core.product import FetchAttempt
                        product.attempts.append(FetchAttempt(
                            source=attempt_data.get("source", ""),
                            status=attempt_data.get("status", "failed"),
                            url=attempt_data.get("url", ""),
                            error=attempt_data.get("error", ""),
                        ))
                    resumable.append(product)
                # else: already succeeded, don't include
            else:
                new_products.append(product)

        return resumable, new_products

    def get_statistics(self) -> dict:
        """Get current task statistics from manifest.

        Returns:
            Dict with statistics or empty dict if no manifest
        """
        manifest = self.load_manifest()
        if manifest is None:
            return {}

        return {
            "task_status": manifest.get("task_status", "unknown"),
            "total_products": manifest.get("total_products", 0),
            "pending_count": manifest.get("pending_count", 0),
            "success_count": manifest.get("success_count", 0),
            "failed_count": manifest.get("failed_count", 0),
            "skipped_count": manifest.get("skipped_count", 0),
            "created_at": manifest.get("created_at", ""),
            "updated_at": manifest.get("updated_at", ""),
        }

    def mark_task_complete(self, products: list[Product]) -> None:
        """Mark task as complete with final product states.

        Args:
            products: Final list of products
        """
        self.write_manifest(products, task_status="completed")

    def mark_task_failed(self, products: list[Product], reason: str = "") -> None:
        """Mark task as failed.

        Args:
            products: Current list of products
            reason: Failure reason
        """
        manifest = self._build_manifest(products, task_status="failed")
        manifest["failure_reason"] = reason
        self.manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
