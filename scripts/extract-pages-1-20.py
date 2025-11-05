#!/usr/bin/env python3
"""Extract pages 1-20 for intermediate testing."""

from pathlib import Path

from pypdf import PdfReader, PdfWriter


def extract_pages(input_pdf: Path, output_pdf: Path, pages: list[int]):
    """Extract specific pages from PDF."""
    reader = PdfReader(input_pdf)
    writer = PdfWriter()

    for page_num in pages:
        writer.add_page(reader.pages[page_num - 1])

    with open(output_pdf, "wb") as f:
        writer.write(f)

    print(f"✅ Extracted {len(pages)} pages to {output_pdf}")
    print(f"   Pages: 1-{len(pages)}")
    print(f"   Size: {output_pdf.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    source = Path("docs/sample pdf/2025-08 Performance Review CONSO_v2.pdf")
    dest = Path("docs/sample pdf/test-pages-1-20.pdf")

    # Extract first 20 pages for comprehensive testing
    pages = list(range(1, 21))  # Pages 1-20

    extract_pages(source, dest, pages)
