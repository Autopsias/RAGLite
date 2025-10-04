from docling.document_converter import DocumentConverter

converter = DocumentConverter()
result = converter.convert("docs/sample pdf/2025-08 Performance Review CONSO_v2.pdf")
doc = result.document

print(f"Total pages: {len(doc.pages)}")

if doc.pages:
    page = doc.pages[0]
    print(f"\nPage object type: {type(page).__name__}")

    # Check available attributes
    attrs = [a for a in dir(page) if not a.startswith("_")]
    print(f"\nPage attributes: {attrs[:15]}")

    # Try different text extraction methods
    print(f'\nHas "text" attr: {hasattr(page, "text")}')
    print(f'Has "export_to_markdown" method: {hasattr(page, "export_to_markdown")}')
    print(f'Has "page_no" attr: {hasattr(page, "page_no")}')

    # Try to get text
    if hasattr(page, "text"):
        print(f'\npage.text value: "{str(page.text)[:100]}"')

    # Check if we need to use doc.export_to_markdown with page parameter
    print(f"\nFull doc export (first 500 chars): {doc.export_to_markdown()[:500]}")
