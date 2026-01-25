#!/usr/bin/env python3
"""Extract test durations from JUnit XML for CI shard balancing analysis.

Phase 3: Resource-Based Scheduling
This script parses JUnit XML test reports and extracts duration data for:
1. Identifying slowest tests that may need optimization
2. Automated shard balancing across CI workers
3. Tracking test performance trends over time

Usage:
    python scripts/extract-test-durations.py test-results/junit.xml
    python scripts/extract-test-durations.py test-results/*.xml --output durations.json
    python scripts/extract-test-durations.py --analyze test-results/ --top 20

Output:
    JSON file with test names and durations for CI analysis pipeline
"""

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path


def parse_junit_xml(xml_path: Path) -> list[dict]:
    """Parse JUnit XML and extract test durations.

    Args:
        xml_path: Path to JUnit XML file

    Returns:
        List of dicts with test name, duration, and status
    """
    results = []

    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        # Handle both <testsuites> and <testsuite> root elements
        if root.tag == "testsuites":
            testsuites = root.findall("testsuite")
        else:
            testsuites = [root]

        for testsuite in testsuites:
            suite_name = testsuite.get("name", "unknown")

            for testcase in testsuite.findall("testcase"):
                test_name = testcase.get("name", "unknown")
                classname = testcase.get("classname", "")
                time_str = testcase.get("time", "0")

                try:
                    duration = float(time_str)
                except ValueError:
                    duration = 0.0

                # Determine status
                status = "passed"
                if testcase.find("failure") is not None:
                    status = "failed"
                elif testcase.find("error") is not None:
                    status = "error"
                elif testcase.find("skipped") is not None:
                    status = "skipped"

                results.append(
                    {
                        "name": test_name,
                        "classname": classname,
                        "suite": suite_name,
                        "duration": duration,
                        "status": status,
                        "file": str(xml_path),
                    }
                )

    except ET.ParseError as e:
        print(f"Warning: Failed to parse {xml_path}: {e}", file=sys.stderr)
    except FileNotFoundError:
        print(f"Warning: File not found: {xml_path}", file=sys.stderr)

    return results


def analyze_durations(results: list[dict], top_n: int = 10) -> dict:
    """Analyze test durations and generate statistics.

    Args:
        results: List of test results from parse_junit_xml
        top_n: Number of top slowest tests to include

    Returns:
        Analysis dict with statistics and recommendations
    """
    if not results:
        return {"error": "No test results to analyze"}

    # Filter to actual test runs (exclude skipped)
    run_tests = [r for r in results if r["status"] != "skipped"]

    if not run_tests:
        return {"error": "No executed tests found"}

    # Calculate statistics
    durations = [r["duration"] for r in run_tests]
    total_duration = sum(durations)
    avg_duration = total_duration / len(durations)
    max_duration = max(durations)
    min_duration = min(durations)

    # Find slowest tests
    sorted_by_duration = sorted(run_tests, key=lambda x: x["duration"], reverse=True)
    slowest = sorted_by_duration[:top_n]

    # Group by file/classname for shard analysis
    by_file = defaultdict(list)
    for r in run_tests:
        # Extract file from classname (e.g., "tests.integration.test_foo")
        file_key = r["classname"].rsplit(".", 1)[0] if r["classname"] else "unknown"
        by_file[file_key].append(r["duration"])

    file_totals = {k: sum(v) for k, v in by_file.items()}
    heaviest_files = sorted(file_totals.items(), key=lambda x: x[1], reverse=True)[:10]

    # Identify tests that might need optimization (>30s)
    needs_optimization = [r for r in run_tests if r["duration"] > 30]

    # Identify tests that might need @pytest.mark.slow (>5s without it)
    # This is a heuristic - actual marker detection would require AST parsing
    potentially_missing_slow = [
        r for r in run_tests if r["duration"] > 5 and r["status"] == "passed"
    ]

    return {
        "summary": {
            "total_tests": len(run_tests),
            "skipped_tests": len(results) - len(run_tests),
            "total_duration_seconds": round(total_duration, 2),
            "average_duration_seconds": round(avg_duration, 2),
            "max_duration_seconds": round(max_duration, 2),
            "min_duration_seconds": round(min_duration, 2),
        },
        "slowest_tests": [
            {
                "name": r["name"],
                "classname": r["classname"],
                "duration": round(r["duration"], 2),
            }
            for r in slowest
        ],
        "heaviest_files": [{"file": f, "total_duration": round(d, 2)} for f, d in heaviest_files],
        "needs_optimization_count": len(needs_optimization),
        "potentially_missing_slow_marker": len(potentially_missing_slow),
        "recommendations": generate_recommendations(run_tests, needs_optimization, total_duration),
    }


def generate_recommendations(
    run_tests: list[dict],
    needs_optimization: list[dict],
    total_duration: float,
) -> list[str]:
    """Generate actionable recommendations based on analysis.

    Args:
        run_tests: All executed tests
        needs_optimization: Tests taking >30s
        total_duration: Total test suite duration

    Returns:
        List of recommendation strings
    """
    recommendations = []

    # Check if total duration is too long
    if total_duration > 1200:  # 20 minutes
        recommendations.append(
            f"Total test duration ({total_duration / 60:.1f} min) exceeds 20 min budget. "
            "Consider parallelizing or splitting heavy tests."
        )

    # Check for very slow individual tests
    very_slow = [t for t in run_tests if t["duration"] > 120]
    if very_slow:
        recommendations.append(
            f"{len(very_slow)} tests take >2 minutes each. "
            "Consider adding @pytest.mark.timeout() or optimizing fixtures."
        )

    # Check for tests that might be missing slow marker
    if needs_optimization:
        recommendations.append(
            f"{len(needs_optimization)} tests take >30 seconds. "
            "Ensure they have @pytest.mark.slow marker."
        )

    # Check for uneven distribution (potential for better sharding)
    if len(run_tests) > 50:
        top_10_pct_duration = sum(
            sorted([t["duration"] for t in run_tests], reverse=True)[: len(run_tests) // 10]
        )
        if top_10_pct_duration > total_duration * 0.5:
            recommendations.append(
                "Top 10% of tests account for >50% of duration. "
                "Consider isolating these into dedicated shard."
            )

    if not recommendations:
        recommendations.append(
            "Test suite duration is within acceptable bounds. No immediate action needed."
        )

    return recommendations


def main():
    """Main entry point for CLI usage."""
    parser = argparse.ArgumentParser(
        description="Extract and analyze test durations from JUnit XML"
    )
    parser.add_argument(
        "xml_files",
        nargs="*",
        help="JUnit XML file(s) to parse. Can use glob patterns.",
    )
    parser.add_argument(
        "--analyze",
        metavar="DIR",
        help="Analyze all JUnit XML files in directory",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output JSON file (default: stdout)",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=10,
        help="Number of slowest tests to show (default: 10)",
    )
    parser.add_argument(
        "--format",
        choices=["json", "summary", "csv"],
        default="json",
        help="Output format (default: json)",
    )

    args = parser.parse_args()

    # Collect XML files
    xml_files: list[Path] = []

    if args.analyze:
        analyze_dir = Path(args.analyze)
        if analyze_dir.is_dir():
            xml_files.extend(analyze_dir.rglob("*.xml"))
        else:
            print(f"Error: {args.analyze} is not a directory", file=sys.stderr)
            sys.exit(1)

    for pattern in args.xml_files or []:
        path = Path(pattern)
        if path.is_file():
            xml_files.append(path)
        else:
            # Try glob pattern
            xml_files.extend(Path(".").glob(pattern))

    if not xml_files:
        print("Error: No XML files specified. Use --help for usage.", file=sys.stderr)
        sys.exit(1)

    # Parse all XML files
    all_results = []
    for xml_file in xml_files:
        all_results.extend(parse_junit_xml(xml_file))

    if not all_results:
        print("Error: No test results found in XML files", file=sys.stderr)
        sys.exit(1)

    # Analyze
    analysis = analyze_durations(all_results, top_n=args.top)

    # Output
    if args.format == "json":
        output = {
            "raw_results": all_results,
            "analysis": analysis,
        }
        output_str = json.dumps(output, indent=2)
    elif args.format == "summary":
        output_str = format_summary(analysis)
    elif args.format == "csv":
        output_str = format_csv(all_results)
    else:
        output_str = json.dumps(analysis, indent=2)

    if args.output:
        Path(args.output).write_text(output_str)
        print(f"Output written to {args.output}")
    else:
        print(output_str)


def format_summary(analysis: dict) -> str:
    """Format analysis as human-readable summary."""
    lines = ["=" * 60, "Test Duration Analysis Summary", "=" * 60, ""]

    if "error" in analysis:
        return f"Error: {analysis['error']}"

    summary = analysis["summary"]
    lines.append(f"Total Tests: {summary['total_tests']}")
    lines.append(f"Skipped: {summary['skipped_tests']}")
    lines.append(f"Total Duration: {summary['total_duration_seconds']:.1f}s")
    lines.append(f"Average Duration: {summary['average_duration_seconds']:.2f}s")
    lines.append(
        f"Range: {summary['min_duration_seconds']:.2f}s - {summary['max_duration_seconds']:.2f}s"
    )
    lines.append("")

    lines.append("Top 10 Slowest Tests:")
    lines.append("-" * 40)
    for i, test in enumerate(analysis["slowest_tests"], 1):
        lines.append(f"  {i}. {test['duration']:.2f}s - {test['name']}")
    lines.append("")

    lines.append("Heaviest Files:")
    lines.append("-" * 40)
    for f in analysis["heaviest_files"][:5]:
        lines.append(f"  {f['total_duration']:.1f}s - {f['file']}")
    lines.append("")

    lines.append("Recommendations:")
    lines.append("-" * 40)
    for rec in analysis["recommendations"]:
        lines.append(f"  • {rec}")

    return "\n".join(lines)


def format_csv(results: list[dict]) -> str:
    """Format results as CSV."""
    lines = ["name,classname,suite,duration,status,file"]
    for r in results:
        lines.append(
            f"{r['name']},{r['classname']},{r['suite']},{r['duration']},{r['status']},{r['file']}"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    main()
