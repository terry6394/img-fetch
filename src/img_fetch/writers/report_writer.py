"""Excel report generation."""

from datetime import datetime
from pathlib import Path
from typing import Optional

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from img_fetch.core.product import Product


class ReportWriter:
    """Generates Excel reports with product fetch results."""

    REPORT_FILENAME = "report.xlsx"

    # Column definitions
    COLUMNS = [
        ("excel_row", "Excel Row", 10),
        ("name", "商品名称", 30),
        ("spec", "商品规格", 20),
        ("brand", "品牌", 15),
        ("status", "Status", 12),
        ("image_path", "Image Path", 40),
        ("source_domain", "Source Domain", 20),
        ("source_url", "Source URL", 50),
        ("source_page_title", "Source Page Title", 30),
        ("page_description", "Page Description", 40),
        ("page_keywords", "Page Keywords", 30),
        ("alt_text", "Alt Text", 30),
        ("captured_at", "Captured At", 20),
        ("error_message", "Error Message", 40),
        ("tried_sources", "Tried Sources", 25),
    ]

    def __init__(self, output_dir: Optional[Path] = None):
        """Initialize the report writer.

        Args:
            output_dir: Directory for output files. Defaults to config OUTPUT_DIR.
        """
        if output_dir is None:
            from img_fetch.config import OUTPUT_DIR
            output_dir = OUTPUT_DIR
        self.output_dir = Path(output_dir)
        self.report_path = self.output_dir / self.REPORT_FILENAME

    def write_report(self, products: list[Product]) -> None:
        """Write Excel report with all products.

        Args:
            products: List of products to include in report
        """
        wb = Workbook()
        ws = wb.active
        ws.title = "Product Images"

        # Write header
        self._write_header(ws)

        # Write data rows
        for row_idx, product in enumerate(products, start=2):
            self._write_product_row(ws, row_idx, product)

        # Auto-adjust column widths
        self._adjust_column_widths(ws)

        # Add statistics sheet
        self._add_statistics_sheet(wb, products)

        wb.save(self.report_path)

    def _write_header(self, ws: Workbook.active) -> None:
        """Write header row with column names."""
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

        thin_border = Border(
            left=Side(style="thin"),
            right=Side(style="thin"),
            top=Side(style="thin"),
            bottom=Side(style="thin"),
        )

        for col_idx, (key, header, _) in enumerate(self.COLUMNS, start=1):
            cell = ws.cell(row=1, column=col_idx, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = thin_border

        ws.row_dimensions[1].height = 30

    def _write_product_row(self, ws: Workbook.active, row_idx: int, product: Product) -> None:
        """Write a single product row."""
        thin_border = Border(
            left=Side(style="thin"),
            right=Side(style="thin"),
            top=Side(style="thin"),
            bottom=Side(style="thin"),
        )

        # Determine status color
        status_fill = self._get_status_fill(product.status)

        row_data = [
            ("excel_row", product.excel_row),
            ("name", product.name),
            ("spec", product.spec),
            ("brand", product.brand),
            ("status", product.status),
            ("image_path", str(product.image_path) if product.image_path else ""),
        ]

        # Add metadata if available
        if product.image_metadata:
            meta = product.image_metadata
            row_data.extend([
                ("source_domain", meta.source_domain),
                ("source_url", meta.source_url),
                ("source_page_title", meta.source_page_title),
                ("page_description", meta.page_description),
                ("page_keywords", ", ".join(meta.page_keywords)),
                ("alt_text", ", ".join(meta.alt_text)),
                ("captured_at", meta.captured_at.strftime("%Y-%m-%d %H:%M:%S") if meta.captured_at else ""),
            ])
        else:
            row_data.extend([
                ("source_domain", ""),
                ("source_url", ""),
                ("source_page_title", ""),
                ("page_description", ""),
                ("page_keywords", ""),
                ("alt_text", ""),
                ("captured_at", ""),
            ])

        row_data.extend([
            ("error_message", product.error_message),
            ("tried_sources", ", ".join(product.tried_sources)),
        ])

        for col_idx, (key, value) in enumerate(row_data, start=1):
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.border = thin_border

            # Apply status-based fill for status column
            if key == "status":
                cell.fill = status_fill
                cell.alignment = Alignment(horizontal="center")
            elif key in ("excel_row",):
                cell.alignment = Alignment(horizontal="center")

    def _get_status_fill(self, status: str) -> PatternFill:
        """Get fill color for status cell."""
        status_colors = {
            "success": PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid"),
            "failed": PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid"),
            "pending": PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid"),
            "skipped": PatternFill(start_color="D9D9D9", end_color="D9D9D9", fill_type="solid"),
        }
        return status_colors.get(status, PatternFill())

    def _adjust_column_widths(self, ws: Workbook.active) -> None:
        """Auto-adjust column widths based on content."""
        for col_idx, (_, _, width) in enumerate(self.COLUMNS, start=1):
            col_letter = get_column_letter(col_idx)
            # Set width with some padding
            ws.column_dimensions[col_letter].width = width

    def _add_statistics_sheet(self, wb: Workbook, products: list[Product]) -> None:
        """Add a statistics summary sheet."""
        ws = wb.create_sheet("Statistics")

        # Title
        ws["A1"] = "Image Fetch Task Statistics"
        ws["A1"].font = Font(bold=True, size=14)
        ws.merge_cells("A1:C1")

        # Generated timestamp
        ws["A2"] = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        ws["A2"].font = Font(italic=True)

        # Statistics
        headers = ["Metric", "Value"]
        for col_idx, header in enumerate(headers, start=1):
            cell = ws.cell(row=4, column=col_idx, value=header)
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="D9D9D9", end_color="D9D9D9", fill_type="solid")

        stats = [
            ("Total Products", len(products)),
            ("Success", sum(1 for p in products if p.status == "success")),
            ("Failed", sum(1 for p in products if p.status == "failed")),
            ("Pending", sum(1 for p in products if p.status == "pending")),
            ("Skipped", sum(1 for p in products if p.status == "skipped")),
        ]

        # Calculate source statistics
        source_stats: dict[str, int] = {}
        for product in products:
            for source in product.tried_sources:
                source_stats[source] = source_stats.get(source, 0) + 1

        for row_idx, (metric, value) in enumerate(stats, start=5):
            ws.cell(row=row_idx, column=1, value=metric)
            ws.cell(row=row_idx, column=2, value=value)

        # Source statistics
        ws["A12"] = "Source Usage Statistics"
        ws["A12"].font = Font(bold=True, size=12)

        ws["A13"] = "Source"
        ws["B13"] = "Attempts"
        ws["A13"].font = Font(bold=True)
        ws["B13"].font = Font(bold=True)
        ws["A13"].fill = PatternFill(start_color="D9D9D9", end_color="D9D9D9", fill_type="solid")
        ws["B13"].fill = PatternFill(start_color="D9D9D9", end_color="D9D9D9", fill_type="solid")

        for row_idx, (source, count) in enumerate(sorted(source_stats.items()), start=14):
            ws.cell(row=row_idx, column=1, value=source)
            ws.cell(row=row_idx, column=2, value=count)

        # Column widths
        ws.column_dimensions["A"].width = 25
        ws.column_dimensions["B"].width = 15

    def get_report_path(self) -> Path:
        """Get the path to the generated report.

        Returns:
            Path to the Excel report
        """
        return self.report_path
