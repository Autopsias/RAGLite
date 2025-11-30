#!/usr/bin/env python3
"""Extract sample pages from Week 0 PDF for fast integration testing."""

from pathlib import Path

from pypdf import PdfReader, PdfWriter


def create_sample_pdf():
    """Extract first 10 pages from Week 0 PDF."""
    input_pdf = Path("docs/sample pdf/2025-08 Performance Review CONSO_v2.pdf")
    output_pdf = Path("tests/fixtures/sample_financial_report.pdf")

    if not input_pdf.exists():
        print(f"❌ Input PDF not found: {input_pdf}")
        return

    print(f"📄 Reading PDF: {input_pdf}")
    reader = PdfReader(str(input_pdf))
    writer = PdfWriter()

    # Extract pages 1-10
    total_pages = min(10, len(reader.pages))
    print(f"✂️  Extracting pages 1-{total_pages}...")

    for page_num in range(total_pages):
        writer.add_page(reader.pages[page_num])

    # Ensure output directory exists
    output_pdf.parent.mkdir(parents=True, exist_ok=True)

    # Write sample PDF
    with open(output_pdf, "wb") as f:
        writer.write(f)

    input_size = input_pdf.stat().st_size / (1024 * 1024)
    output_size = output_pdf.stat().st_size / (1024 * 1024)

    print(f"✅ Created sample PDF: {output_pdf}")
    print(f"   Input size: {input_size:.2f} MB ({len(reader.pages)} pages)")
    print(f"   Output size: {output_size:.2f} MB ({total_pages} pages)")
    print(f"   Reduction: {(1 - output_size / input_size) * 100:.1f}%")


if __name__ == "__main__":
    create_sample_pdf()
