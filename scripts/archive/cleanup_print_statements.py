#!/usr/bin/env python3
"""Script to replace print() statements with logger calls in test files.

This script:
1. Finds all .py files in tests/ with print() statements
2. Adds logging import if not present
3. Adds logger = logging.getLogger(__name__) if not present
4. Replaces print() with appropriate logger calls:
   - print("ERROR") or print("❌") → logger.error()
   - print("WARN") or print("⚠️") → logger.warning()
   - Everything else → logger.info()
"""

import re
import sys
from pathlib import Path


def has_print_statement(content: str) -> bool:
    """Check if file has print() statements."""
    return bool(re.search(r"\bprint\s*\(", content))


def has_logging_import(content: str) -> bool:
    """Check if file already imports logging."""
    return bool(re.search(r"^import logging$", content, re.MULTILINE))


def has_logger_instance(content: str) -> bool:
    """Check if file already has logger instance."""
    return bool(re.search(r"^logger\s*=\s*logging\.getLogger", content, re.MULTILINE))


def add_logging_import(content: str) -> str:
    """Add logging import after other imports."""
    # Find the last import statement
    import_match = list(re.finditer(r"^import\s+\w+|^from\s+\w+.*import", content, re.MULTILINE))
    if not import_match:
        # No imports found, add at top
        return "import logging\n\n" + content

    last_import = import_match[-1]
    insert_pos = content.find("\n", last_import.end()) + 1

    # Insert logging import
    return content[:insert_pos] + "import logging\n" + content[insert_pos:]


def add_logger_instance(content: str) -> str:
    """Add logger instance after imports."""
    # Find the end of import section (first non-import, non-blank line)
    lines = content.split("\n")
    insert_idx = 0

    for i, line in enumerate(lines):
        if line.strip() and not line.startswith("import ") and not line.startswith("from "):
            if (
                not line.startswith("#")
                and not line.startswith('"""')
                and not line.startswith("'''")
            ):
                insert_idx = i
                break

    # Insert logger instance
    lines.insert(insert_idx, "")
    lines.insert(insert_idx + 1, "logger = logging.getLogger(__name__)")
    lines.insert(insert_idx + 2, "")

    return "\n".join(lines)


def replace_print_with_logger(content: str) -> str:
    """Replace print() calls with appropriate logger calls."""

    def determine_log_level(print_args: str) -> str:
        """Determine appropriate log level based on content."""
        lower_args = print_args.lower()
        if "error" in lower_args or "❌" in print_args or "fail" in lower_args:
            return "error"
        elif "warn" in lower_args or "⚠️" in print_args:
            return "warning"
        else:
            return "info"

    def replace_match(match):
        """Replace a single print() match with logger call."""
        args = match.group(1)
        level = determine_log_level(args)
        return f"logger.{level}({args})"

    # Replace print(...) with logger.level(...)
    content = re.sub(r"\bprint\s*\(([^)]+)\)", replace_match, content)

    return content


def process_file(file_path: Path) -> bool:
    """Process a single test file. Returns True if modified."""
    print(f"Processing {file_path}...")

    content = file_path.read_text()

    # Skip if no print statements
    if not has_print_statement(content):
        print("  ✅ No print statements found")
        return False

    original_content = content

    # Add logging import if needed
    if not has_logging_import(content):
        print("  → Adding logging import")
        content = add_logging_import(content)

    # Add logger instance if needed
    if not has_logger_instance(content):
        print("  → Adding logger instance")
        content = add_logger_instance(content)

    # Replace print() with logger calls
    print("  → Replacing print() with logger calls")
    content = replace_print_with_logger(content)

    # Write back if modified
    if content != original_content:
        file_path.write_text(content)
        print("  ✅ File updated")
        return True
    else:
        print("  ⚠️  No changes made")
        return False


def main():
    """Main entry point."""
    tests_dir = Path("tests")

    if not tests_dir.exists():
        print(f"Error: {tests_dir} directory not found")
        sys.exit(1)

    # Find all Python test files (excluding .bak files)
    test_files = sorted([f for f in tests_dir.rglob("test_*.py") if not f.name.endswith(".bak")])

    print(f"Found {len(test_files)} test files\n")

    modified_count = 0
    for file_path in test_files:
        if process_file(file_path):
            modified_count += 1
        print()

    print(f"\n{'=' * 60}")
    print(f"Summary: Modified {modified_count} files out of {len(test_files)} total")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
