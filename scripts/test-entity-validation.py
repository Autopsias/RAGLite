#!/usr/bin/env python3
"""Test script to validate entity validation patterns work correctly.

This script tests the _validate_entity() function to ensure:
1. All bad patterns identified in data quality audit are REJECTED
2. Legitimate entity names are ACCEPTED
3. Edge cases are handled correctly

Run before full database re-ingestion to ensure fixes work.
"""

import sys
from pathlib import Path

# Add raglite to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from raglite.ingestion.adaptive_table.core import _validate_entity


def test_validation():
    """Test entity validation with all patterns."""

    print("=" * 80)
    print("ENTITY VALIDATION PATTERN TEST")
    print("=" * 80)
    print()

    # Test cases that should be REJECTED (return False)
    reject_cases = [
        # CRITICAL: Currency descriptors (30,208 rows affected)
        ("Currency (1000 EUR)", "Currency with parenthetical EUR"),
        ("Currency (1000 USD)", "Currency with parenthetical USD"),
        ("Others (1000 BRL)", "Parenthetical currency anywhere"),
        ("Group (1000 EUR)", "Group with parenthetical EUR"),
        ("1000 EUR", "Standalone currency amount"),
        ("EUR/ton", "Currency ratio"),
        ("EUR", "Standalone currency code"),
        ("USD", "Standalone USD"),
        ("BRL", "Standalone BRL"),
        ("AKZ", "Standalone Angolan Kwanza"),
        ("Meur", "Million EUR"),
        ("Musd", "Million USD"),
        # CRITICAL: Unknown placeholder (1,308 rows affected)
        ("Unknown", "Unknown placeholder"),
        ("unknown", "Lowercase unknown"),
        ("  Unknown  ", "Unknown with whitespace"),
        # CRITICAL: Temporal descriptors (2,100+ rows affected)
        ("YTD", "Year-to-date"),
        ("MTD", "Month-to-date"),
        ("QTD", "Quarter-to-date"),
        ("% LY", "Percentage last year"),
        ("% PY", "Percentage previous year"),
        ("% B", "Percentage budget"),
        ("Oct-25", "Month-year format"),
        ("Mar-24", "Month-year format 2"),
        ("Jan 2025", "Month year with space"),
        ("B Oct-25", "Budget month-year"),
        ("B Jan-24", "Budget month-year 2"),
        # HIGH: Common units and null values
        ("Unit", "Unit descriptor"),
        ("kton", "Kilotonne"),
        ("GWh", "Gigawatt-hour"),
        ("%", "Percentage symbol"),
        ("day", "Day unit"),
        ("days", "Days unit"),
        ("FTE", "Full-time equivalent"),
        ("N/A", "Not applicable"),
        ("n/a", "Lowercase N/A"),
        ("NA", "NA variant"),
        ("null", "Null value"),
        ("-", "Dash placeholder"),
        ("#", "Hash placeholder"),
        # MEDIUM: Numeric values
        ("123", "Pure numeric"),
        ("45.67", "Decimal numeric"),
        ("1,234", "Comma-separated numeric"),
        # LOW: Other patterns
        ("Measurement", "Measurement descriptor"),
        ("UOM", "Unit of measure"),
    ]

    # Test cases that should be ACCEPTED (return True)
    accept_cases = [
        ("Portugal", "Country name"),
        ("Angola", "Country name 2"),
        ("Group", "Group entity (without currency)"),
        ("Portugal Cement", "Division name"),
        ("Ready-mix and Aggregates", "Business unit"),
        ("Others", "Others without currency"),
        ("CIMPOR", "Company name"),
        ("Group IFRS", "Group with descriptor"),
        ("Mozambique Operations", "Country operations"),
        ("Brazil Cement Division", "Country division"),
        ("South Africa Ready-mix", "Country business"),
    ]

    print("TESTING REJECTION PATTERNS (should all return False)")
    print("-" * 80)

    reject_failures = []
    for test_value, description in reject_cases:
        result = _validate_entity(test_value)
        status = "✅ PASS" if not result else "❌ FAIL"
        print(f"{status} | {test_value:30s} | {description}")

        if result:  # Should have been rejected but was accepted
            reject_failures.append((test_value, description))

    print()
    print("TESTING ACCEPTANCE PATTERNS (should all return True)")
    print("-" * 80)

    accept_failures = []
    for test_value, description in accept_cases:
        result = _validate_entity(test_value)
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} | {test_value:30s} | {description}")

        if not result:  # Should have been accepted but was rejected
            accept_failures.append((test_value, description))

    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)

    total_reject = len(reject_cases)
    total_accept = len(accept_cases)
    reject_passed = total_reject - len(reject_failures)
    accept_passed = total_accept - len(accept_failures)

    print(f"Rejection Tests: {reject_passed}/{total_reject} passed")
    print(f"Acceptance Tests: {accept_passed}/{total_accept} passed")
    print(f"Total: {reject_passed + accept_passed}/{total_reject + total_accept} passed")

    if reject_failures:
        print()
        print("❌ REJECTION FAILURES (incorrectly accepted):")
        for value, desc in reject_failures:
            print(f"   - {value} ({desc})")

    if accept_failures:
        print()
        print("❌ ACCEPTANCE FAILURES (incorrectly rejected):")
        for value, desc in accept_failures:
            print(f"   - {value} ({desc})")

    print()

    if not reject_failures and not accept_failures:
        print("✅ ALL TESTS PASSED - Safe to proceed with re-ingestion")
        return 0
    else:
        print("❌ SOME TESTS FAILED - Fix patterns before re-ingestion")
        return 1


if __name__ == "__main__":
    sys.exit(test_validation())
