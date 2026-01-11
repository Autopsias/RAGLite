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
    "type"
    "object"
    "datetime"
    "date"
    "time"
    "timedelta"
)

# Safe standard library and third-party classes
SAFE_STDLIB=(
    "Exception"
    "BaseException"
    "ValueError"
    "TypeError"
    "KeyError"
    "IndexError"
    "RuntimeError"
    "AttributeError"
    "ImportError"
    "FileNotFoundError"
    "OSError"
    "IOError"
    "MagicMock"
    "Mock"
    "AsyncMock"
)

# Safe external library patterns (pandas, numpy, etc.)
SAFE_EXTERNAL_PATTERNS=(
    "pd\\."
    "np\\."
    "ast\\."
    "Decimal"
    "Path"
    "Numeric"
    "Column"
    "Table"
    "Integer"
    "String"
    "Float"
    "Boolean"
)

# Convert to grep patterns
SAFE_PATTERN=$(IFS='|'; echo "${SAFE_BUILTINS[*]}")
SAFE_STDLIB_PATTERN=$(IFS='|'; echo "${SAFE_STDLIB[*]}")
SAFE_EXTERNAL_REGEX=$(IFS='|'; echo "${SAFE_EXTERNAL_PATTERNS[*]}")

# Find all isinstance calls in tests
while IFS= read -r file; do
    # Extract isinstance calls
    if grep -n "isinstance(" "$file" > /dev/null 2>&1; then
        # Check each isinstance line
        while IFS=: read -r lineno line; do
            # Skip comments
            if echo "$line" | grep -q "^\s*#"; then
                continue
            fi

            # Skip if it's a safe built-in type (single or in tuple)
            if echo "$line" | grep -qE "isinstance\([^,]+,\s*(${SAFE_PATTERN})\)"; then
                continue
            fi

            # Skip if it's a tuple of safe built-in types like (list, dict), (str, int), etc.
            if echo "$line" | grep -qE "isinstance\([^,]+,\s*\((${SAFE_PATTERN})(,\s*(${SAFE_PATTERN}))*\)\)"; then
                continue
            fi

            # Skip if it's checking against exception/error classes (single or tuple)
            if echo "$line" | grep -qE "isinstance\([^,]+,\s*(${SAFE_STDLIB_PATTERN})"; then
                continue
            fi

            # Skip tuple of exception types like (ValueError, RuntimeError)
            if echo "$line" | grep -qE "isinstance\([^,]+,\s*\((${SAFE_STDLIB_PATTERN})(,\s*(${SAFE_STDLIB_PATTERN}))*\)\)"; then
                continue
            fi

            # Skip if it's checking against external library classes (pandas, numpy, ast, etc.)
            if echo "$line" | grep -qE "isinstance\([^,]+,\s*(${SAFE_EXTERNAL_REGEX})"; then
                continue
            fi

            # Skip tuple of ast types like (ast.FunctionDef, ast.AsyncFunctionDef)
            if echo "$line" | grep -qE "isinstance\([^,]+,\s*\(ast\."; then
                continue
            fi

            # Skip Python 3.10+ union type syntax: isinstance(x, int | float)
            if echo "$line" | grep -qE "isinstance\([^,]+,\s*(${SAFE_PATTERN})\s*\|"; then
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

# Known safe constants (all caps) that are not enums
SAFE_CONSTANTS=(
    "STOPWORDS"
    "CANDIDATE_MODELS"
    "KNOWN_METRICS"
    "VALID_MODELS"
    "SUPPORTED_FORMATS"
    "DEFAULT_CONFIG"
    "API_ENDPOINTS"
    "HTTP_METHODS"
    "TEST_DATA"
    "SAMPLE_DATA"
    "MOCK_DATA"
)
SAFE_CONSTANTS_PATTERN=$(IFS='|'; echo "${SAFE_CONSTANTS[*]}")

while IFS= read -r file; do
    # Look for pattern: "(assert|if).*in SomeEnum" where SomeEnum is CamelCase
    # This targets actual enum class membership checks like:
    #   - assert value in TrendDirection
    #   - if severity in AnomalySeverity:
    # Must be actual Python code (assert or if), not docstrings/comments
    if grep -nE "(assert|if)\s+\S+\s+in\s+[A-Z][a-z][a-zA-Z]+\s*(:|$)" "$file" > /dev/null 2>&1; then
        while IFS=: read -r lineno line; do
            # Skip comments
            if echo "$line" | grep -q "^\s*#"; then
                continue
            fi

            # Skip docstrings (lines that are just strings)
            if echo "$line" | grep -qE '^\s*"""' || echo "$line" | grep -qE "^\s*'''"; then
                continue
            fi

            # Skip if it's checking membership in a list/dict/set
            if echo "$line" | grep -qE "in\s+\[|in\s+\{|in\s+\("; then
                continue
            fi

            # Skip known safe constants
            if echo "$line" | grep -qE "in\s+(${SAFE_CONSTANTS_PATTERN})"; then
                continue
            fi

            # Skip if it's an ALL_CAPS constant (not an enum class)
            if echo "$line" | grep -qE "in\s+[A-Z_]+\s*(:|$)"; then
                continue
            fi

            # Found a potential enum membership check
            echo "VIOLATION: $file:$lineno"
            echo "  $line"
            echo "  Suggested fix: Use .name or .value for enum checks"
            echo ""
            VIOLATIONS_FOUND=$((VIOLATIONS_FOUND + 1))
            EXIT_CODE=1
        done < <(grep -nE "(assert|if)\s+\S+\s+in\s+[A-Z][a-z][a-zA-Z]+\s*(:|$)" "$file")
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
