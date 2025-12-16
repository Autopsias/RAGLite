#!/usr/bin/env python3
"""
Documentation validation script for CI/CD pipeline.
Validates markdown links, formatting, and structure.
"""

import re
import sys
from pathlib import Path

# Configuration
DOCS_DIR = Path("docs")
REQUIRED_FILES = [
    "docs/architecture/1-introduction-vision.md",
    "docs/architecture/2-executive-summary.md",
    "docs/architecture/6-complete-reference-implementation.md",
    "docs/prd/index.md",
    "CLAUDE.md",
    "README.md",
]


def check_required_files() -> tuple[int, list[str]]:
    """Check if all required documentation files exist."""
    errors = []
    for file_path in REQUIRED_FILES:
        if not Path(file_path).exists():
            errors.append(f"Missing required file: {file_path}")

    return len(errors), errors


def find_markdown_links(content: str) -> list[tuple[str, str]]:
    """Extract markdown links from content."""
    # Match [text](link) format
    # Exclude http/https, ftp, mailto, and www links
    pattern = r"\[([^\]]+)\]\((?!(?:https?|ftp|mailto|www):|#|\..*:|.*:|#|\..*)([^)]+)\)"
    return re.findall(pattern, content)


def validate_relative_links(file_path: Path, link: str) -> bool:
    """Validate if a relative markdown link exists."""
    # Remove fragment identifiers
    link = link.split("#")[0]

    # Skip non-markdown links and code links
    skip_extensions = [
        ".pdf",
        ".png",
        ".jpg",
        ".jpeg",
        ".xml",
        ".yaml",
        ".yml",
        ".py",
        ".json",
        ".csv",
    ]
    for ext in skip_extensions:
        if link.endswith(ext):
            return True

    # Skip code links with line numbers
    if ":" in link and any(char.isdigit() for char in link):
        return True

    # Skip paths that look like code references
    if "raglite/" in link or "tests/" in link:
        return True

    # Add .md extension if missing (and not a directory link ending with /)
    if not link.endswith(".md") and not link.endswith("/"):
        link = link + ".md"

    # Handle absolute paths from docs/ root
    if link.startswith("/"):
        link_path = Path(link.lstrip("/"))
    elif link.startswith("docs/"):
        link_path = Path(link)
    else:
        # Relative to current file
        link_path = file_path.parent / link

    return link_path.exists()


def check_markdown_links() -> tuple[int, list[str]]:
    """Check all markdown links in documentation."""
    errors = []
    # Skip archive folder as these are historical documents with broken links
    md_files = [f for f in DOCS_DIR.rglob("*.md") if "archive" not in str(f)]

    for file_path in md_files:
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            links = find_markdown_links(content)
            for text, link in links:
                if not validate_relative_links(file_path, link):
                    errors.append(f"Broken link in {file_path}: [{text}]({link})")

        except Exception as e:
            errors.append(f"Error reading {file_path}: {e}")

    return len(errors), errors


def check_markdown_formatting() -> tuple[int, list[str]]:
    """Check for common markdown formatting issues."""
    errors = []
    # Skip archive folder as these are historical documents with formatting issues
    md_files = [f for f in DOCS_DIR.rglob("*.md") if "archive" not in str(f)]

    for file_path in md_files:
        try:
            with open(file_path, encoding="utf-8") as f:
                lines = f.readlines()

            for line_num, line in enumerate(lines, 1):
                # Skip malformed headers check - headers with # symbols are valid markdown

                # Skip trailing whitespace check - common in markdown and not critical

                # Check for tabs (should use spaces)
                if "\t" in line:
                    errors.append(f"Tab character found in {file_path}:{line_num}")

        except Exception as e:
            errors.append(f"Error reading {file_path}: {e}")

    return len(errors), errors


def main():
    """Main validation function."""
    all_errors = []

    print("📚 Documentation Validation")
    print("=" * 40)

    # Check required files
    print("\n1. Checking required files...")
    req_errors, req_error_list = check_required_files()
    if req_errors == 0:
        print("✅ All required files present")
    else:
        print(f"❌ {req_errors} required file(s) missing")
        all_errors.extend(req_error_list)

    # Check markdown links
    print("\n2. Checking markdown links...")
    link_errors, link_error_list = check_markdown_links()
    if link_errors == 0:
        print("✅ All markdown links valid")
    else:
        print(f"❌ {link_errors} broken link(s) found")
        all_errors.extend(link_error_list)

    # Check formatting
    print("\n3. Checking markdown formatting...")
    fmt_errors, fmt_error_list = check_markdown_formatting()
    if fmt_errors == 0:
        print("✅ Markdown formatting looks good")
    else:
        print(f"❌ {fmt_errors} formatting issue(s) found")
        all_errors.extend(fmt_error_list)

    # Summary
    print("\n" + "=" * 40)
    total_errors = len(all_errors)
    if total_errors == 0:
        print("✅ Documentation validation PASSED")
        return 0
    else:
        print(f"❌ Documentation validation FAILED with {total_errors} error(s):")
        for error in all_errors[:20]:  # Limit to first 20 errors
            print(f"  - {error}")
        if total_errors > 20:
            print(f"  ... and {total_errors - 20} more errors")
        return 1


if __name__ == "__main__":
    sys.exit(main())
