#!/usr/bin/env python3
"""Data Quality Audit CLI.

Runs data quality checks across forecasting variables and reports findings.

Usage:
    # Single variable
    uv run python scripts/audit_data_quality.py --variable ebitda

    # All variables
    uv run python scripts/audit_data_quality.py --all

    # SECIL variables only (from financial_tables)
    uv run python scripts/audit_data_quality.py --secil-only

    # External variables only (from APIs)
    uv run python scripts/audit_data_quality.py --external-only

    # Export JSON report
    uv run python scripts/audit_data_quality.py --all --export-json

    # Export Markdown report
    uv run python scripts/audit_data_quality.py --all --export-markdown

    # CI mode (exit 1 on failures)
    uv run python scripts/audit_data_quality.py --all --ci

    # Verbose output (show all checks)
    uv run python scripts/audit_data_quality.py --all --verbose

Examples:
    # Quick EBITDA entity contamination check
    uv run python scripts/audit_data_quality.py -v ebitda

    # Full audit with JSON export for CI
    uv run python scripts/audit_data_quality.py --all --export-json --ci

    # Check only internal SECIL data quality
    uv run python scripts/audit_data_quality.py --secil-only -v
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from raglite.forecasting.data_quality import (
    DataQualityOrchestrator,
    export_json,
    format_markdown,
    get_external_variables,
    get_secil_variables,
    list_configured_variables,
    print_console_report,
)
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run data quality audit on forecasting variables",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Variable selection (mutually exclusive group)
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument(
        "-v",
        "--variable",
        type=str,
        help="Single variable to audit",
    )
    selection.add_argument(
        "--all",
        action="store_true",
        help="Audit all configured variables",
    )
    selection.add_argument(
        "--secil-only",
        action="store_true",
        help="Audit only SECIL internal variables (from financial_tables)",
    )
    selection.add_argument(
        "--external-only",
        action="store_true",
        help="Audit only external variables (from APIs)",
    )

    # Output options
    parser.add_argument(
        "--export-json",
        action="store_true",
        help="Export results to JSON file",
    )
    parser.add_argument(
        "--export-markdown",
        action="store_true",
        help="Export results to Markdown file",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="docs/qa",
        help="Output directory for exports (default: docs/qa)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show all checks, not just failures",
    )

    # CI mode
    parser.add_argument(
        "--ci",
        action="store_true",
        help="CI mode: exit 1 if any checks fail",
    )

    # List available variables
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all configured variables and exit",
    )

    return parser.parse_args()


async def main() -> int:
    """Main entry point."""
    args = parse_args()

    # List mode
    if args.list:
        print("Configured Variables:")
        print()
        print("SECIL Internal (from financial_tables):")
        for var in get_secil_variables():
            print(f"  - {var}")
        print()
        print("External (from APIs):")
        for var in get_external_variables():
            print(f"  - {var}")
        return 0

    # Determine variables to audit
    if args.variable:
        variables = [args.variable]
    elif args.secil_only:
        variables = get_secil_variables()
    elif args.external_only:
        variables = get_external_variables()
    elif args.all:
        variables = list_configured_variables()
    else:
        # Default: audit all if no selection made
        variables = list_configured_variables()

    print(f"Auditing {len(variables)} variables...")
    print()

    # Run audit
    orchestrator = DataQualityOrchestrator()
    audit = await orchestrator.run_audit(variables)

    # Print console report
    print_console_report(audit, verbose=args.verbose)

    # Export JSON if requested
    if args.export_json:
        output_dir = Path(args.output_dir)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_path = output_dir / f"data_quality_audit_{timestamp}.json"
        export_json(audit, json_path)
        print(f"JSON report exported to: {json_path}")

    # Export Markdown if requested
    if args.export_markdown:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        md_path = output_dir / f"data_quality_audit_{timestamp}.md"
        md_content = format_markdown(audit)
        md_path.write_text(md_content)
        print(f"Markdown report exported to: {md_path}")

    # CI mode: exit 1 if any failures
    if args.ci:
        if audit.total_failed > 0:
            print(f"\nCI FAILURE: {audit.total_failed} checks failed")
            return 1
        print("\nCI PASSED: No failures detected")

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
