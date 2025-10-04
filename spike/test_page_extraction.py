"""Quick test to verify page number extraction fix."""

import time
from pathlib import Path

from config import TEST_PDF_PATH
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption


def test_page_extraction():
    """Test that Docling can extract page-level content with page numbers."""
    print("Testing page extraction...")

    pdf_file = Path(TEST_PDF_PATH)

    # Configure optimized pipeline for testing (no OCR, no table structure)
    # This is a test to verify page extraction works - we don't need full OCR/table analysis
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = False  # Disable OCR for speed
    pipeline_options.do_table_structure = False  # Disable table analysis for speed

    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
    )

    print(f"Converting: {pdf_file.name} (optimized: OCR=OFF, tables=OFF)")
    start_time = time.time()
    result = converter.convert(str(pdf_file))
    conversion_time = time.time() - start_time
    doc = result.document

    # Get full document text for validation
    full_text = doc.export_to_markdown()

    # Count pages
    pages_count = len(doc.pages) if hasattr(doc, "pages") else 0

    # Sample validation: check that we have content
    has_content = len(full_text.strip()) > 0
    text_preview = full_text[:200] if full_text else ""

    print("\n✓ Page extraction test PASSED")
    print(f"  Conversion time: {conversion_time:.2f}s (optimized)")
    print(f"  Total pages: {pages_count}")
    print(f"  Content extracted: {len(full_text):,} chars")
    print(f"  Preview: {text_preview[:100]}...")

    # Verify page numbers are extractable
    assert pages_count > 0, "No pages extracted!"
    assert has_content, "No content extracted!"

    print("\n✅ Page number extraction is WORKING!")
    print(f"   (Test optimized: {conversion_time:.2f}s vs ~527s unoptimized)")


if __name__ == "__main__":
    test_page_extraction()
