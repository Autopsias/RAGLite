#!/usr/bin/env python3
"""Comprehensive table structure analysis to categorize extraction patterns.

Goal: Understand WHY 86.5% NULL entity and 77.5% NULL metric occur.
Analyze table diversity to detect correct extraction strategy per table type.
"""

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter
from docling_core.types.doc import TableItem

from raglite.ingestion.adaptive_table_extraction import HeaderType, classify_header
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


def analyze_table_orientation(table_item: TableItem, page_no: int, table_idx: int) -> dict:
    """Analyze table structure to determine data orientation.

    Returns:
        dict with orientation analysis:
        - row_header_types: What types appear in row headers
        - col_header_types: What types appear in column headers
        - dominant_row_type: Most common row header type
        - dominant_col_type: Most common column header type
        - suggested_pattern: Predicted extraction pattern
    """
    table_cells = table_item.data.table_cells
    num_rows = table_item.data.num_rows
    num_cols = table_item.data.num_cols

    # Separate headers
    column_headers = [cell for cell in table_cells if cell.column_header]
    row_headers = [cell for cell in table_cells if cell.row_header]
    data_cells = [cell for cell in table_cells if not cell.column_header and not cell.row_header]

    # Count column header rows
    col_header_rows = sorted({cell.start_row_offset_idx for cell in column_headers})

    # Classify all headers
    row_types = Counter()
    col_types = Counter()

    row_samples = []
    col_samples = []

    for cell in row_headers[:10]:  # Sample first 10
        h_type = classify_header(cell.text)
        row_types[h_type] += 1
        row_samples.append((cell.text[:40] if cell.text else "", h_type.value))

    for cell in column_headers[:10]:  # Sample first 10
        h_type = classify_header(cell.text)
        col_types[h_type] += 1
        col_samples.append((cell.text[:40] if cell.text else "", h_type.value))

    # Determine dominant types
    dominant_row = row_types.most_common(1)[0] if row_types else (HeaderType.UNKNOWN, 0)
    dominant_col = col_types.most_common(1)[0] if col_types else (HeaderType.UNKNOWN, 0)

    # Suggest extraction pattern based on orientation
    suggested_pattern = "UNKNOWN"
    confidence = "low"

    # Pattern 1: Row=TEMPORAL, Col=ENTITY → Values are metrics over time per entity
    if dominant_row[0] == HeaderType.TEMPORAL and dominant_col[0] == HeaderType.ENTITY:
        suggested_pattern = "temporal_rows_entity_cols"
        confidence = "high" if dominant_row[1] >= 5 and dominant_col[1] >= 3 else "medium"

    # Pattern 2: Row=METRIC, Col=TEMPORAL → Values are metrics per period
    elif dominant_row[0] == HeaderType.METRIC and dominant_col[0] == HeaderType.TEMPORAL:
        suggested_pattern = "metric_rows_temporal_cols"
        confidence = "high" if dominant_row[1] >= 5 and dominant_col[1] >= 3 else "medium"

    # Pattern 3: Row=METRIC, Col=ENTITY → Values are metrics per entity
    elif dominant_row[0] == HeaderType.METRIC and dominant_col[0] == HeaderType.ENTITY:
        suggested_pattern = "metric_rows_entity_cols"
        confidence = "high" if dominant_row[1] >= 5 and dominant_col[1] >= 3 else "medium"

    # Pattern 4: Multi-header (2+ col header rows) + Row=METRIC
    elif len(col_header_rows) >= 2 and dominant_row[0] == HeaderType.METRIC:
        suggested_pattern = "multi_header_metric_rows"
        confidence = "high" if dominant_row[1] >= 5 else "medium"

    # Pattern 5: Row=TEMPORAL, Col=METRIC → Values are time series per metric
    elif dominant_row[0] == HeaderType.TEMPORAL and dominant_col[0] == HeaderType.METRIC:
        suggested_pattern = "temporal_rows_metric_cols"
        confidence = "medium"

    return {
        "page": page_no,
        "table": table_idx,
        "dimensions": f"{num_rows}x{num_cols}",
        "col_header_rows": len(col_header_rows),
        "num_row_headers": len(row_headers),
        "num_col_headers": len(column_headers),
        "num_data_cells": len(data_cells),
        "row_header_types": dict(row_types),
        "col_header_types": dict(col_types),
        "dominant_row_type": dominant_row[0].value,
        "dominant_col_type": dominant_col[0].value,
        "suggested_pattern": suggested_pattern,
        "confidence": confidence,
        "row_samples": row_samples,
        "col_samples": col_samples,
    }


def explain_null_problem(analysis: dict) -> str:
    """Explain why current extraction produces NULLs for this table."""
    pattern = analysis["suggested_pattern"]

    explanations = {
        "temporal_rows_entity_cols": """
❌ PROBLEM: Row headers are TEMPORAL (dates), not metrics!
   Current fallback assumes: row_header → metric
   Reality: row_header → period

   Result:
   - metric = NULL (expecting in rows, but they're temporal)
   - period = column_header (correct!)
   - entity = NULL (should be from column headers but may be mixed with other types)

   FIX NEEDED: Extract entity from column headers, period from row headers
""",
        "metric_rows_temporal_cols": """
✅ NEAR-CORRECT: Row headers are metrics (as expected)
   Current fallback assumes: row_header → metric ✓

   Result:
   - metric = row_header (correct!)
   - period = column_header (should work if classified as TEMPORAL)
   - entity = NULL (not present in this table type - acceptable)

   ISSUE: May still produce NULL if header classification fails
""",
        "metric_rows_entity_cols": """
✅ NEAR-CORRECT: Row=metrics, Col=entities (standard financial table)
   Current fallback should work for this pattern

   Possible NULL causes:
   - Entity headers misclassified as UNKNOWN
   - Need stronger entity detection patterns
""",
        "multi_header_metric_rows": """
⚠️ COMPLEX: Multi-header with metrics in rows
   Current fallback may struggle with multi-header flattening

   Result:
   - metric = row_header (correct!)
   - entity/period = from multi-row column headers (needs hierarchical join)

   FIX NEEDED: Implement hierarchical header flattening per research
""",
        "UNKNOWN": """
❌ UNDETECTABLE: Headers classified as UNKNOWN
   Cannot determine correct extraction pattern

   Causes:
   - Headers don't match any classification patterns
   - Table has non-standard structure

   FIX NEEDED: Improve header classification regex patterns
""",
    }

    return explanations.get(pattern, "Unknown pattern - needs investigation")


def main():
    """Analyze table diversity across the full PDF."""
    pdf_path = Path("docs/sample pdf/2025-08 Performance Review CONSO_v2.pdf")

    logger.info("=" * 80)
    logger.info("COMPREHENSIVE TABLE STRUCTURE DIVERSITY ANALYSIS")
    logger.info("=" * 80)
    logger.info(f"PDF: {pdf_path}")
    logger.info(f"Size: {pdf_path.stat().st_size / 1024 / 1024:.1f} MB")
    logger.info("")

    logger.info("Goal: Categorize table patterns to understand NULL field root cause")
    logger.info("")

    # Convert PDF
    logger.info("Converting PDF with Docling...")
    converter = DocumentConverter(allowed_formats=[InputFormat.PDF])
    result = converter.convert(pdf_path)

    if not result.document:
        logger.error("PDF conversion failed!")
        return

    logger.info("✅ Conversion complete")
    logger.info("")

    # Analyze all tables
    logger.info("Analyzing table structures...")
    logger.info("")

    analyses = []
    pattern_counts = Counter()

    table_count = 0
    for element, _ in result.document.iterate_items():
        if isinstance(element, TableItem):
            # Get page number
            page_no = None
            if hasattr(element, "prov") and element.prov:
                for prov_item in element.prov:
                    if hasattr(prov_item, "page_no"):
                        page_no = prov_item.page_no
                        break

            if page_no is None:
                continue

            table_count += 1

            # Analyze structure
            analysis = analyze_table_orientation(element, page_no, table_count)
            analyses.append(analysis)
            pattern_counts[analysis["suggested_pattern"]] += 1

            # Log brief summary
            logger.info(
                f"Page {page_no}, Table {table_count}: {analysis['suggested_pattern']} "
                f"(Row={analysis['dominant_row_type']}, Col={analysis['dominant_col_type']}) "
                f"[{analysis['confidence']}]"
            )

    # Summary statistics
    logger.info("")
    logger.info("=" * 80)
    logger.info("PATTERN DISTRIBUTION")
    logger.info("=" * 80)

    total = len(analyses)
    for pattern, count in pattern_counts.most_common():
        percentage = (count / total * 100) if total > 0 else 0
        logger.info(f"  {pattern}: {count}/{total} ({percentage:.1f}%)")

    # Detailed analysis for each pattern
    logger.info("")
    logger.info("=" * 80)
    logger.info("NULL FIELD ROOT CAUSE BY PATTERN")
    logger.info("=" * 80)

    for pattern in pattern_counts.keys():
        pattern_tables = [a for a in analyses if a["suggested_pattern"] == pattern]

        logger.info("")
        logger.info(f"{'=' * 80}")
        logger.info(f"Pattern: {pattern} ({len(pattern_tables)} tables)")
        logger.info(f"{'=' * 80}")

        # Show first example
        example = pattern_tables[0]
        logger.info(f"\nExample: Page {example['page']}, Table {example['table']}")
        logger.info(f"Dimensions: {example['dimensions']}")
        logger.info(f"Column header rows: {example['col_header_rows']}")
        logger.info(f"Row headers: {example['num_row_headers']}")
        logger.info(f"Column headers: {example['num_col_headers']}")
        logger.info("\nRow header samples:")
        for text, htype in example["row_samples"][:5]:
            logger.info(f"  - {text} [{htype}]")
        logger.info("\nColumn header samples:")
        for text, htype in example["col_samples"][:5]:
            logger.info(f"  - {text} [{htype}]")

        logger.info(f"\n{explain_null_problem(example)}")

    # Overall conclusions
    logger.info("")
    logger.info("=" * 80)
    logger.info("CONCLUSIONS & FIXES NEEDED")
    logger.info("=" * 80)

    # Count tables with wrong assumptions
    temporal_rows = len([a for a in analyses if a["dominant_row_type"] == "TEMPORAL"])
    metric_rows = len([a for a in analyses if a["dominant_row_type"] == "METRIC"])
    unknown_rows = len([a for a in analyses if a["dominant_row_type"] == "UNKNOWN"])

    logger.info("")
    logger.info("Row Header Distribution:")
    logger.info(
        f"  TEMPORAL (dates/periods): {temporal_rows}/{total} ({temporal_rows / total * 100:.1f}%)"
    )
    logger.info(f"  METRIC (KPIs): {metric_rows}/{total} ({metric_rows / total * 100:.1f}%)")
    logger.info(
        f"  UNKNOWN (unclassified): {unknown_rows}/{total} ({unknown_rows / total * 100:.1f}%)"
    )

    logger.info("")
    logger.info("🔍 ROOT CAUSE IDENTIFIED:")
    logger.info("")

    if temporal_rows > metric_rows:
        logger.info(f"  ❌ {temporal_rows / total * 100:.1f}% of tables have TEMPORAL row headers")
        logger.info("     Current fallback assumes: row_header → metric")
        logger.info("     Reality: row_header → period")
        logger.info("")
        logger.info("  This explains the 77.5% NULL metric rate!")
        logger.info("")
        logger.info("  FIX: Implement orientation-aware extraction:")
        logger.info("       1. Detect table orientation FIRST")
        logger.info(
            "       2. If Row=TEMPORAL + Col=ENTITY → Extract entity from cols, period from rows"
        )
        logger.info(
            "       3. If Row=METRIC + Col=TEMPORAL → Extract metric from rows, period from cols"
        )

    if unknown_rows > total * 0.2:
        logger.info("")
        logger.info(f"  ❌ {unknown_rows / total * 100:.1f}% of headers are UNKNOWN")
        logger.info("     Need to improve header classification patterns")
        logger.info("")
        logger.info("  FIX: Expand classification regex patterns:")
        logger.info("       - Add more financial metric keywords")
        logger.info("       - Add more entity/geography patterns")
        logger.info("       - Add more temporal patterns (quarters, years, etc.)")

    logger.info("")
    logger.info("📊 RECOMMENDED SOLUTION (from research):")
    logger.info("")
    logger.info("  1. Orientation Detection:")
    logger.info("     - Classify ALL headers first")
    logger.info("     - Determine dominant row type and column type")
    logger.info("     - Select extraction strategy based on orientation")
    logger.info("")
    logger.info("  2. Pattern-Specific Extraction:")
    logger.info("     - temporal_rows_entity_cols: entity=col, period=row, metric=infer/null")
    logger.info("     - metric_rows_temporal_cols: metric=row, period=col, entity=infer/null")
    logger.info("     - metric_rows_entity_cols: metric=row, entity=col, period=infer/null")
    logger.info("     - multi_header_metric_rows: hierarchical header flattening")
    logger.info("")
    logger.info("  3. Enhanced Classification:")
    logger.info("     - Expand regex patterns for METRIC/ENTITY/TEMPORAL")
    logger.info("     - Use confidence thresholding (research recommendation)")
    logger.info("     - Consider LLM-assisted classification for ambiguous headers")
    logger.info("")
    logger.info("  4. Validation & Quality:")
    logger.info("     - Mark extraction method per table pattern")
    logger.info("     - Add confidence scores to each row")
    logger.info("     - Implement SQL constraints to catch anomalies")

    # Export analysis for reference
    import json

    output_path = Path("docs/validation/table-diversity-analysis.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(
            {
                "total_tables": total,
                "pattern_distribution": dict(pattern_counts),
                "row_type_distribution": {
                    "TEMPORAL": temporal_rows,
                    "METRIC": metric_rows,
                    "UNKNOWN": unknown_rows,
                },
                "sample_analyses": analyses[:20],  # First 20 for reference
            },
            f,
            indent=2,
            default=str,
        )

    logger.info("")
    logger.info(f"✅ Analysis exported to: {output_path}")


if __name__ == "__main__":
    main()
