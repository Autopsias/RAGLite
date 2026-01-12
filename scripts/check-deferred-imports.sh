#!/usr/bin/env bash
# check-deferred-imports.sh - Detect deferred imports causing test performance issues
#
# Strategic Context:
# - Tests importing heavy modules inside functions cause 5-15s overhead per test
# - Pattern: `from raglite.main import` inside test_* functions
# - Impact: 120s timeout insufficient, mysterious CI hangs
# - Prevention: Catch pattern before commit
#
# Related Issues:
# - Strategic Analysis: Tests import heavy modules inside async functions
# - Root Cause: raglite.main triggers full module graph load (statsmodels, pmdarima, etc.)
# - Fix: Move imports to module level or use lazy-load wrappers

set -euo pipefail

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "🔍 Checking for deferred imports in test functions..."

# Pattern to detect: import statements inside test functions
# This catches:
#   def test_something():
#       from raglite.main import ...
#   async def test_something():
#       from raglite.main import ...

violations=0

# If files are passed as arguments (from pre-commit), check only those
# Otherwise, check all test files (for manual runs)
if [[ $# -gt 0 ]]; then
    FILES=("$@")
else
    # Manual run - check all test files
    mapfile -t FILES < <(find "$PROJECT_ROOT/tests" -name "test_*.py" -type f)
fi

for test_file in "${FILES[@]}"; do
    # Skip empty results or non-test files
    [[ -z "$test_file" ]] && continue
    [[ ! "$test_file" =~ test_.*\.py$ ]] && continue
    [[ ! -f "$test_file" ]] && continue

    # Extract line numbers of test function definitions
    test_func_lines=$(grep -n "^\s*\(async \)\?def test_" "$test_file" | cut -d: -f1 || true)

    # For each test function, check if there are imports inside
    while IFS= read -r func_line; do
        [[ -z "$func_line" ]] && continue

        # Get next test function or end of file
        next_func_line=$(grep -n "^\s*\(async \)\?def test_" "$test_file" | \
                        awk -F: -v line="$func_line" '$1 > line {print $1; exit}')

        if [[ -z "$next_func_line" ]]; then
            # Last function - check to end of file
            next_func_line=$(wc -l < "$test_file")
        fi

        # Check for imports between func_line and next_func_line
        deferred_imports=$(sed -n "${func_line},${next_func_line}p" "$test_file" | \
                          grep -n "^\s\+from raglite" || true)

        if [[ -n "$deferred_imports" ]]; then
            func_name=$(sed -n "${func_line}p" "$test_file" | sed 's/.*def \([^(]*\).*/\1/')
            echo -e "${RED}❌ Deferred import detected:${NC}"
            echo "   File: $test_file"
            echo "   Function: $func_name (line $func_line)"
            echo "   Import: $(echo "$deferred_imports" | head -1 | sed 's/^[0-9]*://')"
            echo ""
            echo -e "${YELLOW}Fix: Move import to module level (top of file)${NC}"
            echo ""
            violations=$((violations + 1))
        fi
    done <<< "$test_func_lines"
done

if [[ $violations -gt 0 ]]; then
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}Found $violations deferred import(s) in test functions${NC}"
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "Why this matters:"
    echo "  • raglite.main imports trigger full module graph load"
    echo "  • Heavy dependencies: statsmodels, pmdarima, docling, etc."
    echo "  • Each deferred import adds 5-15s overhead per test"
    echo "  • Causes 120s timeout failures in CI"
    echo ""
    echo "Fix patterns:"
    echo "  1. Module-level import (preferred):"
    echo "     # At top of file:"
    echo "     from raglite.main import _perform_forecast_refresh"
    echo ""
    echo "  2. Lazy-load wrapper (for circular imports):"
    echo "     def get_main_module():"
    echo '         """Lazy-load main module to avoid circular imports."""'
    echo "         import raglite.main"
    echo "         return raglite.main"
    echo ""
    exit 1
else
    echo -e "${GREEN}✓ No deferred imports detected${NC}"
    exit 0
fi
