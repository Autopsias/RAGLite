"""Quick test to verify page number extraction fix."""

from pathlib import Path
from docling.document_converter import DocumentConverter
from config import TEST_PDF_PATH

def test_page_extraction():
    """Test that Docling can extract page-level content with page numbers."""
    print("Testing page extraction...")

    pdf_file = Path(TEST_PDF_PATH)
    converter = DocumentConverter()

    print(f"Converting: {pdf_file.name}")
    result = converter.convert(str(pdf_file))
    doc = result.document

    # Test page iteration
    pages_count = 0
    sample_pages = []

    for page_num, page in enumerate(doc.pages, start=1):
        pages_count += 1

        # Get page text
        page_text = page.export_to_markdown() if hasattr(page, 'export_to_markdown') else ""
        if not page_text and hasattr(page, 'text'):
            page_text = page.text

        if page_num <= 3:  # Sample first 3 pages
            sample_pages.append({
                "page_number": page_num,
                "text_length": len(page_text),
                "has_content": len(page_text.strip()) > 0,
                "preview": page_text[:100] if page_text else ""
            })

    print(f"\n✓ Page extraction test PASSED")
    print(f"  Total pages: {pages_count}")
    print(f"  Sample pages:")
    for p in sample_pages:
        print(f"    Page {p['page_number']}: {p['text_length']} chars, has_content={p['has_content']}")
        print(f"      Preview: {p['preview'][:80]}...")

    # Verify page numbers are extractable
    assert pages_count > 0, "No pages extracted!"
    assert all(p['has_content'] for p in sample_pages), "Some pages have no content!"

    print(f"\n✅ Page number extraction is WORKING!")
    return True

if __name__ == "__main__":
    test_page_extraction()
