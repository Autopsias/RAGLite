#!/usr/bin/env python3
"""Debug Docling table extraction to see what items are generated."""

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
from docling.document_converter import DocumentConverter, PdfFormatOption

# Configure Docling with table extraction
pipeline_options = PdfPipelineOptions(do_table_structure=True)
pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE

converter = DocumentConverter(
    format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
)

# Convert only part 2 (pages 41-80) which includes page 46
pdf_path = "docs/sample pdf/split/2025-08 Performance Review CONSO_v2_part02_pages041-080.pdf"
print(f"Converting: {pdf_path}")
print("=" * 80)

result = converter.convert(pdf_path)

# Inspect items from page 46 (page 6 in part 2)
print("\nInspecting items from page 6 (page 46 in original PDF)...")
print("=" * 80)

table_items = []
text_items = []

for item, _level in result.document.iterate_items():
    # Get page number
    page_no = None
    if hasattr(item, "prov") and item.prov:
        page_no = item.prov[0].page_no

    # Only look at page 6
    if page_no == 6:
        item_type = type(item).__name__

        # Check for table items
        if "Table" in item_type:
            table_items.append(item)
            print(f"\n📊 TABLE ITEM ({item_type}):")
            print(f"   Attributes: {dir(item)}")

            # Check for text
            if hasattr(item, "text"):
                print(f"   .text: {item.text[:200]}")

            # Check for data/grid
            if hasattr(item, "data"):
                print(f"   .data: {type(item.data)}")
            if hasattr(item, "grid"):
                print(f"   .grid: {type(item.grid)}")
            if hasattr(item, "export_to_markdown"):
                try:
                    md = item.export_to_markdown()
                    print(f"   .export_to_markdown(): {md[:300]}")
                except Exception as e:
                    print(f"   .export_to_markdown() failed: {e}")
        else:
            text_items.append(item)

print("\n\nSUMMARY:")
print(f"  Table items on page 6: {len(table_items)}")
print(f"  Text items on page 6: {len(text_items)}")

# Try exporting full document to markdown
print("\n" + "=" * 80)
print("Exporting full document to markdown...")
print("=" * 80)

markdown = result.document.export_to_markdown()

# Search for "23.2" in markdown
if "23.2" in markdown:
    print("\n✅ Found '23.2' in markdown export")
    # Show context
    idx = markdown.find("23.2")
    print(f"\nContext:\n{markdown[max(0, idx - 200) : idx + 200]}")
else:
    print("\n❌ '23.2' NOT FOUND in markdown export")

# Check if tables are in markdown format
if "```" in markdown or "|" in markdown:
    print("\n✅ Markdown contains table formatting")
else:
    print("\n❌ No table formatting found in markdown")
