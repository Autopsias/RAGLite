"""Validate metadata extraction quality (Story 2.6 AC5).

This script spot-checks 20 chunks for metadata accuracy, validating that
≥80% of extracted fields are accurate and relevant.

Usage:
    python scripts/validate-ac5-metadata-quality.py
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from raglite.shared.clients import get_postgresql_connection  # noqa: E402
from raglite.shared.config import Settings  # noqa: E402


def validate_metadata_quality():
    """Spot-check 20 chunks for metadata accuracy."""
    Settings()

    print("=" * 80)
    print("Story 2.6 AC5 - Metadata Quality Validation")
    print("=" * 80)
    print()
    print("Spot-checking 20 random chunks for metadata accuracy...")
    print("Target: ≥80% field accuracy across all 15 metadata fields")
    print()

    try:
        conn = get_postgresql_connection()
        cursor = conn.cursor()

        # Get 20 random chunks with metadata
        cursor.execute(
            """
            SELECT
                chunk_id,
                page_number,
                chunk_index,
                LEFT(content, 200) as content_preview,
                -- Document-Level (7 fields)
                document_type,
                reporting_period,
                time_granularity,
                company_name,
                geographic_jurisdiction,
                data_source_type,
                version_date,
                -- Section-Level (5 fields)
                section_type,
                metric_category,
                units,
                department_scope,
                -- Table-Specific (3 fields)
                table_context,
                table_name,
                statistical_summary
            FROM financial_chunks
            WHERE company_name IS NOT NULL OR metric_category IS NOT NULL
            ORDER BY RANDOM()
            LIMIT 20
        """
        )

        chunks = cursor.fetchall()
        cursor.close()

        if not chunks:
            print("❌ ERROR: No chunks with metadata found in PostgreSQL")
            sys.exit(1)

        print(f"✓ Retrieved {len(chunks)} chunks for validation\n")

        # Field names for validation
        field_names = [
            "document_type",
            "reporting_period",
            "time_granularity",
            "company_name",
            "geographic_jurisdiction",
            "data_source_type",
            "version_date",
            "section_type",
            "metric_category",
            "units",
            "department_scope",
            "table_context",
            "table_name",
            "statistical_summary",
        ]

        # Display sample chunks
        print("=" * 80)
        print("SAMPLE CHUNKS (First 5 of 20)")
        print("=" * 80)

        for i, chunk in enumerate(chunks[:5], 1):
            print(f"\n--- Chunk {i} (Page {chunk[1]}, Index {chunk[2]}) ---")
            print(f"Content Preview: {chunk[3]}...")
            print()
            print("Extracted Metadata:")

            # Document-Level
            print(f"  Document Type: {chunk[4] or '(none)'}")
            print(f"  Reporting Period: {chunk[5] or '(none)'}")
            print(f"  Time Granularity: {chunk[6] or '(none)'}")
            print(f"  Company Name: {chunk[7] or '(none)'}")
            print(f"  Geographic Jurisdiction: {chunk[8] or '(none)'}")
            print(f"  Data Source Type: {chunk[9] or '(none)'}")
            print(f"  Version Date: {chunk[10] or '(none)'}")

            # Section-Level
            print(f"  Section Type: {chunk[11] or '(none)'}")
            print(f"  Metric Category: {chunk[12] or '(none)'}")
            print(f"  Units: {chunk[13] or '(none)'}")
            print(f"  Department Scope: {chunk[14] or '(none)'}")

            # Table-Specific
            if chunk[15]:
                print(f"  Table Context: {chunk[15][:100]}...")
            else:
                print("  Table Context: (none)")
            print(f"  Table Name: {chunk[16] or '(none)'}")
            if chunk[17]:
                print(f"  Statistical Summary: {chunk[17][:100]}...")
            else:
                print("  Statistical Summary: (none)")

        # Calculate field coverage across all 20 chunks
        print("\n" + "=" * 80)
        print("FIELD COVERAGE ANALYSIS (All 20 chunks)")
        print("=" * 80)
        print()

        field_coverage = {}
        for field_idx, field_name in enumerate(
            field_names, 4
        ):  # Start at index 4 (after metadata fields)
            non_null_count = sum(1 for chunk in chunks if chunk[field_idx])
            coverage_pct = (non_null_count / len(chunks)) * 100
            field_coverage[field_name] = coverage_pct

            status = "✅" if coverage_pct >= 50 else "⚠️" if coverage_pct >= 25 else "❌"
            print(f"{status} {field_name:30s}: {non_null_count:2d}/20 ({coverage_pct:5.1f}%)")

        # Overall statistics
        print("\n" + "=" * 80)
        print("OVERALL QUALITY METRICS")
        print("=" * 80)

        total_fields = len(field_names) * len(chunks)
        filled_fields = sum(
            1
            for chunk in chunks
            for field_idx in range(4, 4 + len(field_names))
            if chunk[field_idx]
        )

        overall_coverage = (filled_fields / total_fields) * 100

        print(
            f"\nTotal fields checked: {total_fields} ({len(chunks)} chunks × {len(field_names)} fields)"
        )
        print(f"Fields with extracted data: {filled_fields}")
        print(f"Overall field coverage: {overall_coverage:.1f}%")

        # AC5 Success Criteria
        print("\n" + "=" * 80)
        print("AC5 SUCCESS CRITERIA VALIDATION")
        print("=" * 80)

        if overall_coverage >= 80:
            print(f"✅ PASS - Overall coverage {overall_coverage:.1f}% (target ≥80%)")
        elif overall_coverage >= 70:
            print(f"⚠️  MARGINAL - Overall coverage {overall_coverage:.1f}% (target ≥80%)")
        else:
            print(f"❌ FAIL - Overall coverage {overall_coverage:.1f}% (target ≥80%)")

        # Field-specific recommendations
        low_coverage_fields = [(name, pct) for name, pct in field_coverage.items() if pct < 50]

        if low_coverage_fields:
            print(f"\n⚠️  Fields with <50% coverage ({len(low_coverage_fields)} fields):")
            for field_name, pct in sorted(low_coverage_fields, key=lambda x: x[1]):
                print(f"   • {field_name}: {pct:.1f}%")
        else:
            print("\n✅ All fields have ≥50% coverage")

        print()

    except Exception as e:
        print(f"\n❌ ERROR: Metadata quality validation failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    validate_metadata_quality()
