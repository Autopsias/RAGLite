#!/usr/bin/env python3
"""Extract specific pages from PDF for faster testing."""

from pathlib import Path

from pypdf import PdfReader, PdfWriter


def extract_pages(input_pdf: Path, output_pdf: Path, pages: list[int]):
    """Extract specific pages from PDF.

    Args:
        input_pdf: Source PDF path
        output_pdf: Destination PDF path
        pages: List of page numbers (1-indexed)
    """
    reader = PdfReader(input_pdf)
    writer = PdfWriter()

    for page_num in pages:
        # pypdf uses 0-indexed pages
        writer.add_page(reader.pages[page_num - 1])

    with open(output_pdf, "wb") as f:
        writer.write(f)

    print(f"✅ Extracted {len(pages)} pages to {output_pdf}")
    print(f"   Pages: {pages}")
    print(f"   Size: {output_pdf.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    source = Path("docs/sample pdf/2025-08 Performance Review CONSO_v2.pdf")
    dest = Path("docs/sample pdf/test-pages-4-10-20.pdf")

    # Extract pages with different table structures
    # Page 4: Multi-header (Entity-Metric-Period)
    # Page 10: Temporal columns (Cols=Periods, Rows=Metrics)
    # Page 20: Another layout variant
    pages = [4, 10, 20]

    extract_pages(source, dest, pages)
