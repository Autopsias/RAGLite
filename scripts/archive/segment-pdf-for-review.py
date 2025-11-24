#!/usr/bin/env python3
"""
Extract 20-page segments from financial report PDF for systematic ground truth review.

This script:
1. Splits the 160-page PDF into 8 segments of 20 pages each
2. Preserves page numbers in filenames
3. Creates output directory with clear naming convention
4. Generates index file documenting the segmentation

Usage:
    python scripts/segment-pdf-for-review.py <input_pdf_path>

Output:
    docs/ground-truth-review/section-1-pages-1-20.pdf
    docs/ground-truth-review/section-2-pages-21-40.pdf
    ...
    docs/ground-truth-review/section-8-pages-141-160.pdf
    docs/ground-truth-review/INDEX.md
"""

import sys
from pathlib import Path

from pypdf import PdfReader, PdfWriter


def extract_pdf_segment(
    input_path: str,
    output_path: str,
    start_page: int,
    end_page: int,
) -> None:
    """Extract a page range from a PDF file.

    Args:
        input_path: Path to input PDF
        output_path: Path to output PDF segment
        start_page: Start page number (1-indexed, user-facing)
        end_page: End page number (1-indexed, user-facing, inclusive)
    """
    reader = PdfReader(input_path)

    # Convert to 0-indexed for pypdf
    start_idx = start_page - 1
    end_idx = end_page  # end_page is inclusive, so no -1 needed for range

    # Validate page range
    total_pages = len(reader.pages)
    if start_idx < 0 or end_idx > total_pages:
        raise ValueError(
            f"Invalid page range: {start_page}-{end_page}. PDF has {total_pages} pages."
        )

    # Create writer and add pages
    writer = PdfWriter()
    for page_idx in range(start_idx, end_idx):
        writer.add_page(reader.pages[page_idx])

    # Write output
    with open(output_path, "wb") as output_file:
        writer.write(output_file)

    print(f"✅ Extracted pages {start_page}-{end_page} → {output_path}")


def generate_index_file(output_dir: Path, segments: list[dict]) -> None:
    """Generate INDEX.md file documenting the segmentation.

    Args:
        output_dir: Output directory path
        segments: List of segment metadata dicts
    """
    index_content = """# Ground Truth Review - PDF Segmentation Index

**Date:** 2025-10-26
**Source:** Financial Report (160 pages)
**Purpose:** Systematic review for ground truth creation

---

## Segmentation Overview

The 160-page financial report has been split into 8 segments of 20 pages each for systematic review.

| Section | Pages | Filename | Review Status | Notes |
|---------|-------|----------|---------------|-------|
"""

    for segment in segments:
        section_id = segment["section_id"]
        start = segment["start_page"]
        end = segment["end_page"]
        filename = segment["filename"]

        index_content += (
            f"| Section {section_id} | {start}-{end} | `{filename}` | ⏳ Pending | - |\n"
        )

    index_content += """
---

## Review Instructions

For each section, document:

1. **Table Inventory:**
   - Table types (traditional vs transposed)
   - Table captions/titles
   - Page locations

2. **Metrics Present:**
   - Financial metrics (EBITDA, Turnover, Costs, etc.)
   - Operational metrics (Production, Sales Volumes, etc.)
   - Efficiency metrics (EUR/ton, GJ/ton, etc.)

3. **Entities Covered:**
   - Geographic entities (Portugal, Spain, Tunisia, etc.)
   - Business units (Cement, Ready-Mix, Aggregates)

4. **Time Periods:**
   - Actual periods (Aug-24, Aug-25, YTD)
   - Budget/Forecast periods
   - Comparisons available

5. **Sample Data Values:**
   - Record 5-10 actual values from tables
   - Include: entity, metric, period, value, unit
   - Use for ground truth answer validation

6. **Query Ideas:**
   - What questions can be answered from this section?
   - Point queries (single values)
   - Comparison queries (two entities/periods)
   - Trend queries (time series)

---

## Output Format

Create a YAML file for each section:

```yaml
section_id: 1
pages: [1, 20]
tables:
  - page: 6
    type: traditional
    caption: "EBITDA Summary"
    metrics: [EBITDA, Turnover, EBITDA/Turnover %]
    entities: [Portugal Cement, Spain Ready-Mix]
    periods: [Aug-24, Aug-25, Budget, YTD]
    sample_values:
      - entity: "Portugal Cement"
        metric: "EBITDA"
        period: "Aug-25"
        value: 12345
        unit: "EUR"
        page: 6
        table_index: 1

query_ideas:
  - query: "What was Portugal Cement's EBITDA in August 2025?"
    expected_answer: "12345 EUR"
    difficulty: easy
    category: point
```

Save as: `section-{N}-data-inventory.yaml`

---

## Next Steps

1. ✅ PDF segmentation complete
2. ⏳ Review Section 1 (pages 1-20)
3. ⏳ Review Section 2 (pages 21-40)
4. ⏳ Review Section 3 (pages 41-60)
5. ⏳ Review Section 4 (pages 61-80)
6. ⏳ Review Section 5 (pages 81-100)
7. ⏳ Review Section 6 (pages 101-120)
8. ⏳ Review Section 7 (pages 121-140)
9. ⏳ Review Section 8 (pages 141-160)
10. ⏳ Compile ground truth queries
11. ⏳ Design validation script

**Goal:** Create 50 high-quality ground truth queries with correct answers for RAG validation.
"""

    index_path = output_dir / "INDEX.md"
    with open(index_path, "w") as f:
        f.write(index_content)

    print(f"✅ Generated index file → {index_path}")


def main():
    """Main execution function."""
    print("=" * 80)
    print("GROUND TRUTH REVIEW: PDF SEGMENTATION")
    print("=" * 80)
    print()

    # Check command line arguments
    if len(sys.argv) != 2:
        print("Usage: python scripts/segment-pdf-for-review.py <input_pdf_path>")
        print()
        print("Example:")
        print("  python scripts/segment-pdf-for-review.py data/financial_report_160pages.pdf")
        sys.exit(1)

    input_pdf = sys.argv[1]
    input_path = Path(input_pdf)

    # Validate input file exists
    if not input_path.exists():
        print(f"❌ Error: Input PDF not found at {input_pdf}")
        sys.exit(1)

    print(f"📄 Source PDF: {input_pdf}")

    # Check PDF page count
    reader = PdfReader(input_pdf)
    total_pages = len(reader.pages)
    print(f"📊 Total pages: {total_pages}")

    if total_pages < 160:
        print(f"⚠️  Warning: Expected 160 pages, found {total_pages}")
        print("   Proceeding with available pages...")
    print()

    # Create output directory
    output_dir = Path("docs/ground-truth-review")
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"📁 Output directory: {output_dir}")
    print()

    # Define segments (20 pages each)
    segments = [
        {"section_id": 1, "start_page": 1, "end_page": 20},
        {"section_id": 2, "start_page": 21, "end_page": 40},
        {"section_id": 3, "start_page": 41, "end_page": 60},
        {"section_id": 4, "start_page": 61, "end_page": 80},
        {"section_id": 5, "start_page": 81, "end_page": 100},
        {"section_id": 6, "start_page": 101, "end_page": 120},
        {"section_id": 7, "start_page": 121, "end_page": 140},
        {"section_id": 8, "start_page": 141, "end_page": 160},
    ]

    # Extract each segment
    print("Extracting segments...")
    print()

    for segment in segments:
        section_id = segment["section_id"]
        start_page = segment["start_page"]
        end_page = min(segment["end_page"], total_pages)  # Handle partial PDFs

        filename = f"section-{section_id}-pages-{start_page}-{end_page}.pdf"
        output_path = output_dir / filename
        segment["filename"] = filename

        try:
            extract_pdf_segment(
                input_path=str(input_path),
                output_path=str(output_path),
                start_page=start_page,
                end_page=end_page,
            )
        except Exception as e:
            print(f"❌ Error extracting section {section_id}: {e}")
            continue

    print()
    print("Generating index file...")
    generate_index_file(output_dir, segments)

    print()
    print("=" * 80)
    print("✅ PDF SEGMENTATION COMPLETE")
    print("=" * 80)
    print()
    print("Next steps:")
    print("1. Review each PDF segment manually")
    print("2. Document tables, metrics, entities, periods in each section")
    print("3. Record sample data values for ground truth")
    print("4. Create section-{N}-data-inventory.yaml files")
    print("5. Design ground truth queries with expected answers")
    print()
    print(f"Review directory: {output_dir}")


if __name__ == "__main__":
    main()
