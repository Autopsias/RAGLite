#!/usr/bin/env python3
"""Fix pytestmark E402 violations by moving pytestmark after all imports.

This script addresses the #1 root cause of E402 violations in RAGLite test files.
It detects and fixes cases where pytestmark is placed before or between imports.

Usage:
    python scripts/fix-pytestmark-e402.py --dry-run  # Preview changes
    python scripts/fix-pytestmark-e402.py            # Apply fixes
    python scripts/fix-pytestmark-e402.py --check     # Check for violations

Root Cause: pytestmark is module-level code that violates ruff E402 when placed
            before or between import statements.
"""

import argparse
import re
from pathlib import Path


def find_pytestmark_violations(file_path: Path) -> dict | None:
    """Check if file has pytestmark placed before/between imports.

    Returns:
        dict with 'pytestmark_line', 'first_import', 'last_import', 'all_imports'
        None if no violations or file doesn't exist
    """
    try:
        content = file_path.read_text()
        lines = content.split("\n")
    except Exception:
        return None

    # Find pytestmark line
    pytestmark_line = None
    pytestmark_content = None
    for i, line in enumerate(lines, 1):
        if re.match(r"^pytestmark\s*=", line):
            pytestmark_line = i
            pytestmark_content = line
            break

    if not pytestmark_line:
        return None  # No pytestmark found

    # Find all import lines
    import_lines = []
    for i, line in enumerate(lines, 1):
        if re.match(r"^(import|from)\s+", line):
            import_lines.append((i, line))

    if not import_lines:
        return None  # No imports found

    first_import_line = min(line[0] for line in import_lines)
    last_import_line = max(line[0] for line in import_lines)

    # Check if pytestmark is before first import OR between imports
    if pytestmark_line < first_import_line:
        return {
            "type": "before_imports",
            "pytestmark_line": pytestmark_line,
            "pytestmark_content": pytestmark_content,
            "first_import": first_import_line,
            "last_import": last_import_line,
            "all_imports": import_lines,
        }
    elif pytestmark_line > first_import_line and pytestmark_line < last_import_line:
        return {
            "type": "between_imports",
            "pytestmark_line": pytestmark_line,
            "pytestmark_content": pytestmark_content,
            "first_import": first_import_line,
            "last_import": last_import_line,
            "all_imports": import_lines,
        }

    return None


def fix_pytestmark_placement(file_path: Path, dry_run: bool = False) -> bool:
    """Move pytestmark to after all imports.

    Returns:
        True if file was modified, False otherwise
    """
    violation = find_pytestmark_violations(file_path)
    if not violation:
        return False

    content = file_path.read_text()
    lines = content.split("\n")

    # Extract pytestmark line and blank lines around it
    pytestmark_idx = violation["pytestmark_line"] - 1
    pytestmark_line = lines[pytestmark_idx]

    # Remove pytestmark and surrounding blank lines
    start_idx = pytestmark_idx
    while start_idx > 0 and lines[start_idx - 1].strip() == "":
        start_idx -= 1

    end_idx = pytestmark_idx
    while end_idx < len(lines) - 1 and lines[end_idx + 1].strip() == "":
        end_idx += 1

    # Remove pytestmark block
    del lines[start_idx : end_idx + 1]

    # Find position after last import (maintain blank line after imports)
    insert_idx = violation["last_import"]
    while insert_idx < len(lines) and lines[insert_idx].strip() != "":
        insert_idx += 1

    # Insert pytestmark after imports with blank line before
    if insert_idx >= len(lines) or lines[insert_idx].strip() != "":
        lines.insert(insert_idx, "")
        lines.insert(insert_idx + 1, pytestmark_line)
    else:
        lines.insert(insert_idx, pytestmark_line)

    # Write back
    new_content = "\n".join(lines)

    if dry_run:
        print(f"Would fix: {file_path}")
        print(
            f"  pytestmark moved from line {violation['pytestmark_line']} to after line {insert_idx}"
        )
        return False  # Don't count as modified in dry-run

    file_path.write_text(new_content)
    print(f"Fixed: {file_path}")
    return True


def main():
    parser = argparse.ArgumentParser(description="Fix pytestmark E402 violations in test files")
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview changes without modifying files"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check for violations and exit with error code if found",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Show detailed violation information"
    )
    args = parser.parse_args()

    # Find all test files
    project_root = Path(__file__).parent.parent
    test_files = []
    test_files.extend(project_root.glob("tests/integration/*.py"))
    test_files.extend(project_root.glob("tests/unit/*.py"))
    test_files.extend(project_root.glob("tests/e2e/*.py"))

    # Check for violations
    violations = []
    for file_path in test_files:
        violation = find_pytestmark_violations(file_path)
        if violation:
            violations.append((file_path, violation))

    if args.check:
        if violations:
            print(f"E402 violations found in {len(violations)} files:")
            for file_path, v in violations:
                print(
                    f"  {file_path.relative_to(project_root)}: {v['type']} (line {v['pytestmark_line']})"
                )
            exit(1)
        else:
            print("No E402 violations found.")
            exit(0)

    if args.verbose:
        print(f"Found {len(violations)} files with pytestmark E402 violations:")
        for file_path, v in violations:
            print(f"\n{file_path.relative_to(project_root)}:")
            print(f"  Type: {v['type']}")
            print(f"  pytestmark line: {v['pytestmark_line']}")
            print(f"  Import range: {v['first_import']} - {v['last_import']}")

    # Fix violations
    if args.dry_run:
        print(f"\nDry-run mode: would fix {len(violations)} files")
    else:
        print(f"\nFixing {len(violations)} files...")

    modified_count = 0
    for file_path, _ in violations:
        if fix_pytestmark_placement(file_path, dry_run=args.dry_run):
            modified_count += 1

    if not args.dry_run:
        print(f"\nModified {modified_count} files")
        print("\nNext steps:")
        print("  1. Review changes: git diff")
        print("  2. Run linting: ruff check tests/ --fix")
        print("  3. Run tests: pytest tests/")


if __name__ == "__main__":
    main()
