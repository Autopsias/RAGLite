#!/usr/bin/env python3
"""Verify that the virtual environment has all required dependencies."""

import sys
from pathlib import Path


def main():
    print("=" * 80)
    print("VIRTUAL ENVIRONMENT VERIFICATION")
    print("=" * 80)
    print(f"\nPython executable: {sys.executable}")
    print(f"Python version: {sys.version}")
    print(f"Python prefix: {sys.prefix}")

    # Check if running from venv
    venv_path = Path(".venv/bin/python").resolve()
    current_path = Path(sys.executable).resolve()

    print(
        f"\n{'✅' if current_path == venv_path else '❌'} Running from venv: {current_path == venv_path}"
    )
    print(f"   Expected: {venv_path}")
    print(f"   Actual:   {current_path}")

    # Check required dependencies
    print("\n" + "=" * 80)
    print("DEPENDENCY CHECK")
    print("=" * 80)

    dependencies = [
        "mistralai",
        "fastmcp",
        "qdrant_client",
        "tiktoken",
        "docling",
        "sentence_transformers",
        "anthropic",
        "pytest",
    ]

    all_present = True
    for dep in dependencies:
        try:
            __import__(dep)
            print(f"✅ {dep:25} - installed")
        except ImportError:
            print(f"❌ {dep:25} - MISSING")
            all_present = False

    print("\n" + "=" * 80)
    if all_present and current_path == venv_path:
        print("✅ SUCCESS: Virtual environment is correctly configured!")
        print("\nTo use this in VS Code Test Explorer:")
        print("1. Press Cmd+Shift+P (macOS) or Ctrl+Shift+P (Windows/Linux)")
        print("2. Type: 'Python: Select Interpreter'")
        print("3. Choose: './.venv/bin/python' (Python 3.13.3)")
        print("4. Reload VS Code window: Cmd+Shift+P → 'Developer: Reload Window'")
        return 0
    else:
        print("❌ FAILURE: Environment issues detected!")
        print("\nRun: uv sync --all-groups")
        return 1


if __name__ == "__main__":
    sys.exit(main())
