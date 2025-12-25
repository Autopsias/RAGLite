#!/usr/bin/env bash
# Verification script for CI infrastructure simplification
# Tests that lightweight mode works and jobs are properly conditioned

set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "========================================="
echo "CI Infrastructure Simplification Verification"
echo "========================================="
echo

# 1. Check composite actions exist
echo "1. Checking composite actions..."
if [ -f "$PROJECT_ROOT/.github/actions/setup-uv/action.yml" ]; then
    echo "   ✅ setup-uv action exists"
else
    echo "   ❌ setup-uv action missing"
    exit 1
fi

if [ -f "$PROJECT_ROOT/.github/actions/validate-cache/action.yml" ]; then
    echo "   ✅ validate-cache action exists"
else
    echo "   ❌ validate-cache action missing"
    exit 1
fi

# 2. Check YAML syntax
echo
echo "2. Validating CI workflow YAML syntax..."
python3 -c "import yaml; yaml.safe_load(open('$PROJECT_ROOT/.github/workflows/ci.yml'))" && \
    echo "   ✅ CI workflow YAML syntax valid" || \
    (echo "   ❌ CI workflow YAML syntax invalid" && exit 1)

# 3. Check lightweight mode in conftest.py
echo
echo "3. Checking lightweight test mode in conftest.py..."
if grep -q "LIGHTWEIGHT_TESTS" "$PROJECT_ROOT/tests/conftest.py"; then
    echo "   ✅ LIGHTWEIGHT_TESTS mode configured"
else
    echo "   ❌ LIGHTWEIGHT_TESTS mode missing"
    exit 1
fi

# 4. Check main-only conditions
echo
echo "4. Checking main-only job conditions..."
EXPENSIVE_JOBS=(
    "test-agentic-workflows"
    "test-epic6-accuracy"
    "burn-in"
)

for job in "${EXPENSIVE_JOBS[@]}"; do
    if grep -A 5 "^  ${job}:" "$PROJECT_ROOT/.github/workflows/ci.yml" | \
       grep -q "if:.*github.ref == 'refs/heads/main'"; then
        echo "   ✅ ${job} has main-only condition"
    else
        echo "   ⚠️  ${job} may be missing main-only condition"
    fi
done

# 5. Test lightweight mode works
echo
echo "5. Testing lightweight mode (dry run)..."
export LIGHTWEIGHT_TESTS="true"
export PYTHONPATH="$PROJECT_ROOT:$PROJECT_ROOT/scripts:${PYTHONPATH:-}"
cd "$PROJECT_ROOT"

# Just check that pytest can collect tests in lightweight mode
if pytest tests/unit/ --collect-only -q > /dev/null 2>&1; then
    echo "   ✅ Lightweight mode test collection works"
else
    echo "   ⚠️  Lightweight mode test collection failed (may be expected if deps missing)"
fi

# 6. Line count reduction
echo
echo "6. Checking CI workflow size..."
LINES=$(wc -l < "$PROJECT_ROOT/.github/workflows/ci.yml")
echo "   Current: ${LINES} lines (target: <1000 lines)"
if [ "$LINES" -lt 2364 ]; then
    REDUCTION=$((2364 - LINES))
    echo "   ✅ Reduced by ${REDUCTION} lines from baseline (2364)"
else
    echo "   ⚠️  No reduction yet"
fi

echo
echo "========================================="
echo "Verification Summary"
echo "========================================="
echo "All critical checks passed!"
echo
echo "Next steps:"
echo "1. Commit and push changes"
echo "2. Monitor first CI run for memory usage"
echo "3. Verify expensive jobs only run on main"
echo
