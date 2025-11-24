#!/usr/bin/env python3
"""Task 1.1: Extract pages 18-50 from 160-page PDF to create 30-page test excerpt.

This script extracts pages 18-50 from the full 160-page financial report PDF
to create a manageable test excerpt for rapid iteration during Story 2.14 development.

The excerpt contains key entities (Portugal, Tunisia, Angola, Brazil, Group)
covering most ground truth query data points.
"""

import sys
from pathlib import Path

from pypdf import PdfReader, PdfWriter

# Configuration
SOURCE_PDF = Path(
    "/Users/ricardocarvalho/DeveloperFolder/RAGLite/docs/sample pdf/2025-08 Performance Review CONSO_v2.pdf"
)
OUTPUT_PDF = Path(
    "/Users/ricardocarvalho/DeveloperFolder/RAGLite/docs/sample pdf/test-pages-18-50.pdf"
)

START_PAGE = 17  # 0-indexed: page 18
END_PAGE = 49  # 0-indexed: page 50 (inclusive)
TOTAL_PAGES = END_PAGE - START_PAGE + 1


def extract_pages(source_path: Path, output_path: Path, start_page: int, end_page: int) -> None:
    """Extract specific page range from PDF.

    Args:
        source_path: Path to source PDF
        output_path: Path to output excerpt PDF
        start_page: 0-indexed start page (inclusive)
        end_page: 0-indexed end page (inclusive)

    Raises:
        FileNotFoundError: If source PDF doesn't exist
        Exception: If extraction fails
    """
    if not source_path.exists():
        raise FileNotFoundError(f"Source PDF not found: {source_path}")

    print(f"📄 Extracting pages {start_page + 1}-{end_page + 1} from {source_path.name}...")

    with open(source_path, "rb") as input_file:
        reader = PdfReader(input_file)
        total_pages = len(reader.pages)

        print(f"   Source PDF: {total_pages} pages")

        if end_page >= total_pages:
            raise ValueError(f"End page {end_page + 1} exceeds PDF total of {total_pages} pages")

        # Create new PDF with selected pages
        writer = PdfWriter()
        for page_num in range(start_page, end_page + 1):
            page = reader.pages[page_num]
            writer.add_page(page)
            if (page_num - start_page + 1) % 10 == 0:
                print(f"   Processed {page_num - start_page + 1}/{TOTAL_PAGES} pages...")

        # Write output
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as output_file:
            writer.write(output_file)

        print(f"✅ Excerpt created: {output_path}")
        print(f"   Pages: {TOTAL_PAGES}")
        print(f"   Size: {output_path.stat().st_size / (1024 * 1024):.1f} MB")


if __name__ == "__main__":
    try:
        extract_pages(SOURCE_PDF, OUTPUT_PDF, START_PAGE, END_PAGE)
        print("\n✅ Task 1.1 Complete: PDF excerpt extracted successfully")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Failed to extract PDF: {e}", file=sys.stderr)
        sys.exit(1)
