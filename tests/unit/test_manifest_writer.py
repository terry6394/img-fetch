"""Tests for manifest_writer module."""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from img_fetch.core.product import Product, FetchAttempt, ImageMetadata
from img_fetch.writers.manifest_writer import ManifestWriter


@pytest.fixture
def temp_output_dir():
    """Create a temporary output directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_products():
    """Create sample products for testing."""
    products = [
        Product(
            excel_row=1,
            name="Alpha Jacket",
            spec="Black-L",
            brand="HAGLOFS",
            status="success",
            image_path="/images/HAGLOFS/HAGLOFS_Alpha_Jacket_Black-L.jpg",
            tried_sources=["brand_site"],
            attempts=[
                FetchAttempt(source="brand_site", status="success", url="https://haglofs.com/product/123"),
            ],
        ),
        Product(
            excel_row=2,
            name="Beta Vest",
            spec="Red-M",
            brand="HAGLOFS",
            status="pending",
            tried_sources=[],
            attempts=[],
        ),
        Product(
            excel_row=3,
            name="Gamma Pants",
            spec="Blue-XL",
            brand="HAGLOFS",
            status="failed",
            error_message="Image not found",
            tried_sources=["brand_site", "ecommerce"],
            attempts=[
                FetchAttempt(source="brand_site", status="failed", url="", error="Not found"),
                FetchAttempt(source="ecommerce", status="failed", url="", error="No image"),
            ],
        ),
    ]
    return products


class TestManifestWriter:
    """Tests for ManifestWriter class."""

    def test_write_manifest(self, temp_output_dir, sample_products):
        """Test writing a manifest file."""
        writer = ManifestWriter(output_dir=temp_output_dir)
        writer.write_manifest(sample_products, task_status="in_progress")

        manifest_path = temp_output_dir / "manifest.json"
        assert manifest_path.exists()

        with open(manifest_path) as f:
            manifest = json.load(f)

        assert manifest["version"] == "1.0"
        assert manifest["task_status"] == "in_progress"
        assert manifest["total_products"] == 3
        assert manifest["success_count"] == 1
        assert manifest["pending_count"] == 1
        assert manifest["failed_count"] == 1
        assert len(manifest["products"]) == 3

    def test_write_manifest_includes_product_details(self, temp_output_dir, sample_products):
        """Test that manifest includes all product details."""
        writer = ManifestWriter(output_dir=temp_output_dir)
        writer.write_manifest(sample_products)

        manifest_path = temp_output_dir / "manifest.json"
        with open(manifest_path) as f:
            manifest = json.load(f)

        # Check first product (success)
        p1 = manifest["products"][0]
        assert p1["excel_row"] == 1
        assert p1["name"] == "Alpha Jacket"
        assert p1["spec"] == "Black-L"
        assert p1["brand"] == "HAGLOFS"
        assert p1["status"] == "success"
        assert p1["tried_sources"] == ["brand_site"]
        assert len(p1["attempts"]) == 1
        assert p1["attempts"][0]["source"] == "brand_site"
        assert p1["attempts"][0]["status"] == "success"

        # Check third product (failed with error)
        p3 = manifest["products"][2]
        assert p3["status"] == "failed"
        assert p3["error_message"] == "Image not found"
        assert p3["tried_sources"] == ["brand_site", "ecommerce"]
        assert len(p3["attempts"]) == 2

    def test_load_manifest(self, temp_output_dir, sample_products):
        """Test loading an existing manifest."""
        writer = ManifestWriter(output_dir=temp_output_dir)
        writer.write_manifest(sample_products)

        # Load with new writer instance
        reader = ManifestWriter(output_dir=temp_output_dir)
        manifest = reader.load_manifest()

        assert manifest is not None
        assert manifest["total_products"] == 3
        assert manifest["success_count"] == 1

    def test_load_manifest_returns_none_for_missing_file(self, temp_output_dir):
        """Test that loading non-existent manifest returns None."""
        writer = ManifestWriter(output_dir=temp_output_dir)
        manifest = writer.load_manifest()
        assert manifest is None

    def test_load_manifest_returns_none_for_invalid_json(self, temp_output_dir):
        """Test that loading invalid JSON returns None."""
        manifest_path = temp_output_dir / "manifest.json"
        manifest_path.write_text("not valid json")

        writer = ManifestWriter(output_dir=temp_output_dir)
        manifest = writer.load_manifest()
        assert manifest is None

    def test_get_resumable_products_with_no_manifest(self, temp_output_dir, sample_products):
        """Test getting resumable products when no manifest exists."""
        writer = ManifestWriter(output_dir=temp_output_dir)
        resumable, new = writer.get_resumable_products(sample_products)

        assert len(resumable) == 0
        assert len(new) == 3

    def test_get_resumable_products_with_existing_manifest(self, temp_output_dir, sample_products):
        """Test getting resumable products from existing manifest."""
        writer = ManifestWriter(output_dir=temp_output_dir)
        writer.write_manifest(sample_products)

        # All products should be resumable except the successful one
        reader = ManifestWriter(output_dir=temp_output_dir)
        resumable, new = reader.get_resumable_products(sample_products)

        assert len(resumable) == 2  # pending and failed
        assert len(new) == 0
        assert all(p.status != "success" for p in resumable)

    def test_get_resumable_products_does_not_include_success(self, temp_output_dir, sample_products):
        """Test that successful products are not included in resumable."""
        writer = ManifestWriter(output_dir=temp_output_dir)
        writer.write_manifest(sample_products)

        reader = ManifestWriter(output_dir=temp_output_dir)
        resumable, new = reader.get_resumable_products(sample_products)

        success_rows = [p.excel_row for p in resumable if p.status == "success"]
        assert len(success_rows) == 0

    def test_get_resumable_products_restores_state(self, temp_output_dir, sample_products):
        """Test that resumable products have their state restored."""
        writer = ManifestWriter(output_dir=temp_output_dir)
        writer.write_manifest(sample_products)

        reader = ManifestWriter(output_dir=temp_output_dir)
        resumable, _ = reader.get_resumable_products(sample_products)

        # Find the failed product
        failed_product = next(p for p in resumable if p.excel_row == 3)
        assert failed_product.status == "failed"
        assert failed_product.error_message == "Image not found"
        assert failed_product.tried_sources == ["brand_site", "ecommerce"]
        assert len(failed_product.attempts) == 2

    def test_get_statistics(self, temp_output_dir, sample_products):
        """Test getting statistics from manifest."""
        writer = ManifestWriter(output_dir=temp_output_dir)
        writer.write_manifest(sample_products)

        reader = ManifestWriter(output_dir=temp_output_dir)
        stats = reader.get_statistics()

        assert stats["task_status"] == "in_progress"
        assert stats["total_products"] == 3
        assert stats["success_count"] == 1
        assert stats["pending_count"] == 1
        assert stats["failed_count"] == 1

    def test_get_statistics_returns_empty_for_no_manifest(self, temp_output_dir):
        """Test that statistics returns empty dict when no manifest."""
        writer = ManifestWriter(output_dir=temp_output_dir)
        stats = writer.get_statistics()
        assert stats == {}

    def test_mark_task_complete(self, temp_output_dir, sample_products):
        """Test marking task as complete."""
        writer = ManifestWriter(output_dir=temp_output_dir)
        writer.mark_task_complete(sample_products)

        reader = ManifestWriter(output_dir=temp_output_dir)
        manifest = reader.load_manifest()

        assert manifest["task_status"] == "completed"

    def test_mark_task_failed(self, temp_output_dir, sample_products):
        """Test marking task as failed."""
        writer = ManifestWriter(output_dir=temp_output_dir)
        writer.mark_task_failed(sample_products, reason="Network error")

        reader = ManifestWriter(output_dir=temp_output_dir)
        manifest = reader.load_manifest()

        assert manifest["task_status"] == "failed"
        assert manifest["failure_reason"] == "Network error"


class TestManifestWriterEdgeCases:
    """Edge case tests for ManifestWriter."""

    def test_write_manifest_with_empty_products(self, temp_output_dir):
        """Test writing manifest with empty product list."""
        writer = ManifestWriter(output_dir=temp_output_dir)
        writer.write_manifest([], task_status="completed")

        manifest_path = temp_output_dir / "manifest.json"
        with open(manifest_path) as f:
            manifest = json.load(f)

        assert manifest["total_products"] == 0
        assert manifest["success_count"] == 0
        assert manifest["pending_count"] == 0

    def test_write_manifest_preserves_iso_timestamps(self, temp_output_dir, sample_products):
        """Test that timestamps are in ISO format."""
        writer = ManifestWriter(output_dir=temp_output_dir)
        writer.write_manifest(sample_products)

        manifest_path = temp_output_dir / "manifest.json"
        with open(manifest_path) as f:
            manifest = json.load(f)

        # Check created_at and updated_at are valid ISO format
        assert "created_at" in manifest
        assert "updated_at" in manifest
        # Should be parseable as datetime
        datetime.fromisoformat(manifest["created_at"])
        datetime.fromisoformat(manifest["updated_at"])

    def test_product_with_metadata(self, temp_output_dir):
        """Test writing product with image metadata."""
        product = Product(
            excel_row=1,
            name="Test Product",
            spec="Spec1",
            brand="TEST",
            status="success",
            image_metadata=ImageMetadata(
                source_url="https://example.com/image.jpg",
                source_page_title="Test Product Page",
                source_domain="example.com",
                page_description="A test product",
                page_keywords=["test", "product"],
                alt_text=["product image"],
                image_width=800,
                image_height=600,
            ),
        )

        writer = ManifestWriter(output_dir=temp_output_dir)
        writer.write_manifest([product])

        manifest_path = temp_output_dir / "manifest.json"
        with open(manifest_path) as f:
            manifest = json.load(f)

        # Metadata is not stored in manifest (only in report)
        # but the product itself should be recorded
        assert manifest["products"][0]["name"] == "Test Product"
