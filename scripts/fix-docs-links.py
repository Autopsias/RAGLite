#!/usr/bin/env python3
"""
Script to fix broken markdown links in documentation.
"""

import re
from pathlib import Path


def fix_links_in_file(file_path: Path):
    """Fix broken links in a markdown file."""
    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    # Fix links missing .md extension
    # Pattern for links without .md extension (and not http/https)
    patterns_to_fix = [
        # Relative links without .md
        (r"\[([^\]]+)\]\(([^h)]+)(?<!\.md)\)", r"[\1](\2.md)"),
        # Links to docs/ folders
        (r"\[([^\]]+)\]\(\.\/(docs\/[^)]+)(?<!\.md)\)", r"[\1](\2.md)"),
        # Links to architecture/index
        (r"\[([^\]]+)\]\(\.\/architecture\/index\)(?<!\.md)", r"[\1](./architecture/index.md)"),
    ]

    changes_made = 0
    for pattern, replacement in patterns_to_fix:
        matches = re.findall(pattern, content)
        if matches:
            content = re.sub(pattern, replacement, content)
            changes_made += len(matches)

    # Fix trailing whitespace
    lines = content.split("\n")
    fixed_lines = [line.rstrip() for line in lines]
    content = "\n".join(fixed_lines)

    # Remove tab characters (replace with 2 spaces)
    content = content.replace("\t", "  ")

    # Write back if changes were made
    if changes_made or content != open(file_path).read():
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return changes_made

    return 0


def main():
    """Fix all documentation links."""
    docs_dir = Path("docs")
    total_fixes = 0

    # Fix all markdown files in docs directory
    for md_file in docs_dir.rglob("*.md"):
        fixes = fix_links_in_file(md_file)
        if fixes > 0:
            print(f"Fixed {fixes} links in {md_file}")
            total_fixes += fixes

    print(f"\nTotal fixes: {total_fixes}")


if __name__ == "__main__":
    main()
