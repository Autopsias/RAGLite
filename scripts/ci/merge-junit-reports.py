#!/usr/bin/env python3
"""Merge JUnit XML reports from parallel test shards.

This script aggregates JUnit XML test reports from multiple shards into
a single report for unified CI reporting.
"""

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def merge_junit_reports(input_files: list[Path], output_file: Path) -> dict:
    """Merge multiple JUnit XML files into one.

    Args:
        input_files: List of paths to JUnit XML files
        output_file: Path to write merged XML

    Returns:
        Statistics dict with totals
    """
    # Create root testsuite element
    merged = ET.Element("testsuites")

    totals = {"tests": 0, "errors": 0, "failures": 0, "skipped": 0, "time": 0.0}

    for input_path in input_files:
        if not input_path.exists():
            print(f"Warning: {input_path} not found, skipping", file=sys.stderr)
            continue

        try:
            tree = ET.parse(input_path)
            root = tree.getroot()

            # Handle both <testsuite> and <testsuites> roots
            if root.tag == "testsuites":
                for testsuite in root.findall("testsuite"):
                    _add_testsuite(merged, testsuite, totals)
            elif root.tag == "testsuite":
                _add_testsuite(merged, root, totals)
            else:
                print(f"Warning: Unknown root element {root.tag} in {input_path}")

        except ET.ParseError as e:
            print(f"Error parsing {input_path}: {e}", file=sys.stderr)
            continue

    # Update merged root attributes
    merged.set("tests", str(totals["tests"]))
    merged.set("errors", str(totals["errors"]))
    merged.set("failures", str(totals["failures"]))
    merged.set("skipped", str(totals["skipped"]))
    merged.set("time", f"{totals['time']:.3f}")

    # Write merged file
    tree = ET.ElementTree(merged)
    ET.indent(tree, space="  ")
    tree.write(output_file, encoding="unicode", xml_declaration=True)

    return totals


def _add_testsuite(parent: ET.Element, testsuite: ET.Element, totals: dict) -> None:
    """Add a testsuite element and update totals."""
    parent.append(testsuite)

    totals["tests"] += int(testsuite.get("tests", 0))
    totals["errors"] += int(testsuite.get("errors", 0))
    totals["failures"] += int(testsuite.get("failures", 0))
    totals["skipped"] += int(testsuite.get("skipped", 0))

    time_str = testsuite.get("time", "0")
    try:
        totals["time"] += float(time_str)
    except ValueError:
        pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge JUnit XML test reports")
    parser.add_argument(
        "input_files",
        nargs="+",
        type=Path,
        help="JUnit XML files to merge",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("merged-junit.xml"),
        help="Output file path (default: merged-junit.xml)",
    )
    parser.add_argument(
        "--fail-on-missing",
        action="store_true",
        help="Exit with error if any input file is missing",
    )
    args = parser.parse_args()

    # Check for missing files
    missing = [f for f in args.input_files if not f.exists()]
    if missing:
        print(f"Missing files: {', '.join(str(f) for f in missing)}", file=sys.stderr)
        if args.fail_on_missing:
            return 1

    # Merge reports
    totals = merge_junit_reports(args.input_files, args.output)

    # Summary
    print(f"Merged {len(args.input_files)} reports -> {args.output}")
    print(f"  Tests:    {totals['tests']}")
    print(f"  Failures: {totals['failures']}")
    print(f"  Errors:   {totals['errors']}")
    print(f"  Skipped:  {totals['skipped']}")
    print(f"  Time:     {totals['time']:.2f}s")

    # Return non-zero if there were failures/errors
    if totals["failures"] > 0 or totals["errors"] > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
