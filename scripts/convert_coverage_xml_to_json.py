#!/usr/bin/env python3
"""Convert coverage.xml to JSON format for CI diff/ratchet scripts."""

import json
import sys
import xml.etree.ElementTree as ET


def main() -> None:
    """Convert coverage.xml to .coverage.json format."""
    if len(sys.argv) < 2:
        input_file = "coverage.xml"
    else:
        input_file = sys.argv[1]

    output_file = ".coverage.json"
    if len(sys.argv) >= 3:
        output_file = sys.argv[2]

    tree = ET.parse(input_file)
    root = tree.getroot()

    # Extract coverage percentage from XML
    line_rate = float(root.get("line-rate", 0))
    coverage_pct = round(line_rate * 100, 2)

    # Build simplified JSON structure for scripts
    coverage_data = {
        "totals": {
            "percent_covered": coverage_pct,
            "covered_lines": int(root.get("lines-covered", 0)),
            "num_statements": int(root.get("lines-valid", 0)),
        },
        "files": {},
    }

    # Extract per-file coverage
    for package in root.findall(".//package"):
        for cls in package.findall(".//class"):
            filename = cls.get("filename", "")
            file_line_rate = float(cls.get("line-rate", 0))
            coverage_data["files"][filename] = {
                "summary": {"percent_covered": round(file_line_rate * 100, 2)}
            }

    with open(output_file, "w") as f:
        json.dump(coverage_data, f, indent=2)

    print(f"Converted to {output_file} (Total: {coverage_pct}%)")


if __name__ == "__main__":
    main()
