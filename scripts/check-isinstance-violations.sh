#!/usr/bin/env bash
# Check for isinstance() violations with custom classes in tests
# These patterns fail when using pytest-xdist parallel execution
# CRITICAL: Part of P0-2 fix for isinstance() xdist compatibility

set -euo pipefail

VIOLATIONS_FOUND=0
EXIT_CODE=0

echo "=== Checking for isinstance() violations in tests/ ==="
echo "Pattern: isinstance(obj, CustomClass) fails with pytest-xdist"
echo ""

# Find isinstance checks on custom classes (not built-ins)
# Built-ins are safe: str, int, dict, list, tuple, etc.
# Custom classes fail: TrendAnalysisResult, ModelSelectionResult, etc.

SAFE_BUILTINS=(
    "str"
    "int"
    "float"
    "bool"
    "dict"
    "list"
    "tuple"
    "set"
    "frozenset"
    "bytes"
    "bytearray"
)

# Convert to grep pattern
SAFE_PATTERN=$(IFS='|'; echo "${SAFE_BUILTINS[*]}")

# Find all isinstance calls in tests
while IFS= read -r file; do
    # Extract isinstance calls
    if grep -n "isinstance(" "$file" > /dev/null 2>&1; then
        # Check each isinstance line
        while IFS=: read -r lineno line; do
            # Skip if it's a safe built-in type
            if echo "$line" | grep -qE "isinstance\([^,]+,\s*(${SAFE_PATTERN})\)"; then
                continue
            fi

            # Skip if it's checking against external library classes (they're stable)
            if echo "$line" | grep -qE "isinstance\([^,]+,\s*(Exception|BaseException|ValueError|TypeError)"; then
                continue
            fi

            # Skip comments
            if echo "$line" | grep -q "^\s*#"; then
                continue
            fi

            # Found a potential violation
            echo "VIOLATION: $file:$lineno"
            echo "  $line"
            echo "  Suggested fix: Use __class__.__name__ or hasattr() instead"
            echo ""
            VIOLATIONS_FOUND=$((VIOLATIONS_FOUND + 1))
            EXIT_CODE=1
        done < <(grep -n "isinstance(" "$file")
    fi
done < <(find tests -name "test_*.py" -type f)

# Check for enum membership tests (also fails with xdist)
echo "=== Checking for 'in Enum' violations in tests/ ==="
echo "Pattern: value in SomeEnum fails with pytest-xdist"
echo ""

while IFS= read -r file; do
    # Look for pattern: " in SomeEnum" or " in TrendDirection"
    if grep -nE "\s+in\s+[A-Z][a-zA-Z]+\s*$" "$file" > /dev/null 2>&1; then
        while IFS=: read -r lineno line; do
            # Skip comments
            if echo "$line" | grep -q "^\s*#"; then
                continue
            fi

            # Skip if it's checking membership in a list/dict/set
            if echo "$line" | grep -qE "in\s+\[|in\s+\{|in\s+\("; then
                continue
            fi

            # Found a potential enum membership check
            echo "VIOLATION: $file:$lineno"
            echo "  $line"
            echo "  Suggested fix: Use .name or .value for enum checks"
            echo ""
            VIOLATIONS_FOUND=$((VIOLATIONS_FOUND + 1))
            EXIT_CODE=1
        done < <(grep -nE "\s+in\s+[A-Z][a-zA-Z]+\s*$" "$file")
    fi
done < <(find tests -name "test_*.py" -type f)

if [ $VIOLATIONS_FOUND -eq 0 ]; then
    echo "✓ No isinstance() or enum membership violations found"
    exit 0
else
    echo ""
    echo "=== Summary ==="
    echo "Found $VIOLATIONS_FOUND violation(s)"
    echo ""
    echo "How to fix:"
    echo "  1. isinstance(obj, CustomClass) → obj.__class__.__name__ == 'CustomClass'"
    echo "  2. value in SomeEnum → value.name in ['OPTION1', 'OPTION2']"
    echo "  3. Add hasattr() checks for duck-typing validation"
    echo ""
    echo "See: .claude/rules/testing.md → 'isinstance Checks with pytest-xdist'"
    exit $EXIT_CODE
fi
