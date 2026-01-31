#!/usr/bin/env python3
"""Script to fix deferred imports across all test files."""

import ast
import re
from pathlib import Path


def extract_imports_from_file(file_path: Path) -> list[str]:
    """Extract all import statements from a file."""
    imports = []
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        # Find all import statements
        import_pattern = r"^(from\s+[^\s]+\s+import\s+[^\n]+|import\s+[^\n]+)"
        imports = re.findall(import_pattern, content, re.MULTILINE)

        return imports
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return []


def find_deferred_imports(file_path: Path) -> list[dict]:
    """Find deferred imports in a file."""
    deferred = []
    try:
        with open(file_path, encoding="utf-8") as f:
            lines = f.readlines()

        content = "".join(lines)
        tree = ast.parse(content)

        # Track imports and their positions
        imports = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
                imports[node.lineno] = ast.unparse(node)

        # Find the first non-import, non-comment line
        first_non_import = None
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if (
                not stripped.startswith("#")
                and not stripped.startswith('"""')
                and not stripped.startswith("'''")
            ):
                # Check if it's an import-related line
                if not re.match(r"^(from\s+|import\s+)", line, re.MULTILINE):
                    first_non_import = i
                    break

        # Find all imports after the first non-import line
        if first_non_import:
            for line_num, import_stmt in imports.items():
                if line_num >= first_non_import:
                    deferred.append(
                        {"line": line_num, "import": import_stmt, "file": str(file_path)}
                    )

        return deferred
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        return []


def fix_deferred_imports(file_path: Path, deferred_imports: list[dict]) -> bool:
    """Fix deferred imports by moving them to the top."""
    if not deferred_imports:
        return False

    try:
        with open(file_path, encoding="utf-8") as f:
            lines = f.readlines()

        # Extract unique import statements
        unique_imports = set()
        for imp in deferred_imports:
            unique_imports.add(imp["import"])

        # Create import section to add
        imports_to_add = []
        for imp in sorted(unique_imports):
            imports_to_add.append(f"{imp}\n")

        # Find where to insert imports (after the initial imports section)
        insert_pos = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if (
                stripped
                and not stripped.startswith("#")
                and not stripped.startswith('"""')
                and not stripped.startswith("'''")
            ):
                if not re.match(r"^(from\s+|import\s+)", line, re.MULTILINE):
                    insert_pos = i
                    break
            elif stripped.startswith("import ") or stripped.startswith("from "):
                insert_pos = i + 1

        # Insert imports
        if insert_pos == 0:
            insert_pos = 1  # Insert after first line (docstring)

        updated_lines = lines[:insert_pos] + imports_to_add + lines[insert_pos:]

        # Remove duplicate imports that are now at the top
        existing_imports = set()
        new_lines = []

        for line in updated_lines:
            stripped = line.strip()
            if re.match(r"^(from\s+|import\s+)", line, re.MULTILINE):
                # Check if this import is already in the set
                if stripped in existing_imports:
                    continue
                existing_imports.add(stripped)
                new_lines.append(line)
            else:
                # Skip empty lines before imports
                if stripped or new_lines:
                    new_lines.append(line)

        # Write the fixed content
        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

        return True
    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False


def main():
    """Main function to fix all deferred imports."""
    test_dir = Path("tests")
    total_fixed = 0
    files_fixed = []

    print("Finding files with deferred imports...")

    # Find all Python files
    py_files = list(test_dir.rglob("*.py"))

    # Count total files with deferred imports
    files_with_deferred = []
    for py_file in py_files:
        deferred = find_deferred_imports(py_file)
        if deferred:
            files_with_deferred.append((py_file, deferred))

    print(f"Found {len(files_with_deferred)} files with deferred imports")

    # Fix each file
    for py_file, deferred in files_with_deferred:
        print(f"Fixing {py_file} ({len(deferred)} deferred imports)...")
        if fix_deferred_imports(py_file, deferred):
            total_fixed += len(deferred)
            files_fixed.append(str(py_file))

    print(f"\nFixed {total_fixed} deferred imports across {len(files_fixed)} files")
    print("\nFixed files:")
    for file in sorted(files_fixed):
        print(f"  {file}")

    # Run the deferred import check to verify
    print("\nRunning verification...")
    import subprocess

    result = subprocess.run(
        ["python", "-m", "pre_commit", "run", "check-deferred-imports", "--all-files"],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print("✅ All deferred imports fixed!")
    else:
        print("❌ Some deferred imports remain:")
        print(result.stdout[:2000])  # Show first 2000 chars
        if len(result.stdout) > 2000:
            print("... (output truncated)")


if __name__ == "__main__":
    main()
