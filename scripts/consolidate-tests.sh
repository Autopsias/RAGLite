#!/bin/bash
# Test Consolidation Script
# Consolidates raglite/tests/ into tests/ to fix test discovery gap
# Date: 2025-10-28
# Resolves: 89 missing tests (26% of suite) not discovered by VS Code or CI

set -e  # Exit on error

echo "=========================================="
echo "RAGLite Test Suite Consolidation"
echo "=========================================="
echo ""
echo "This script will:"
echo "  1. Backup raglite/tests/ directory"
echo "  2. Resolve naming collision (test_hybrid_search.py)"
echo "  3. Move all tests to tests/ directory"
echo "  4. Clean up empty directories"
echo "  5. Verify test count"
echo ""

# Step 1: Create backup
echo "Step 1: Creating backup..."
BACKUP_DIR="raglite/tests.backup.$(date +%Y%m%d_%H%M%S)"
cp -r raglite/tests "$BACKUP_DIR"
echo "✅ Backup created: $BACKUP_DIR"
echo ""

# Step 2: Resolve naming collision - rename raglite version to test_sql_hybrid_search.py
echo "Step 2: Resolving naming collision..."
if [ -f "raglite/tests/unit/test_hybrid_search.py" ]; then
    echo "  Renaming raglite/tests/unit/test_hybrid_search.py → test_sql_hybrid_search.py"
    echo "  (This version tests Story 2.14 SQL retrieval, not Story 2.1 BM25)"
    mv raglite/tests/unit/test_hybrid_search.py raglite/tests/unit/test_sql_hybrid_search.py
    echo "✅ Naming collision resolved"
else
    echo "⚠️  test_hybrid_search.py not found in raglite/tests/unit/"
fi
echo ""

# Step 3: Move unit tests
echo "Step 3: Moving unit tests..."
if [ -d "raglite/tests/unit" ]; then
    for file in raglite/tests/unit/*.py; do
        if [ -f "$file" ] && [ "$(basename "$file")" != "__init__.py" ]; then
            filename=$(basename "$file")
            echo "  Moving: $filename"
            mv "$file" "tests/unit/"
        fi
    done
    echo "✅ Unit tests moved"
else
    echo "⚠️  No raglite/tests/unit/ directory"
fi
echo ""

# Step 4: Move integration tests
echo "Step 4: Moving integration tests..."
if [ -d "raglite/tests/integration" ]; then
    for file in raglite/tests/integration/*.py; do
        if [ -f "$file" ] && [ "$(basename "$file")" != "__init__.py" ]; then
            filename=$(basename "$file")
            echo "  Moving: $filename"
            mv "$file" "tests/integration/"
        fi
    done
    echo "✅ Integration tests moved"
else
    echo "⚠️  No raglite/tests/integration/ directory"
fi
echo ""

# Step 5: Move root-level tests
echo "Step 5: Moving root-level tests..."
if [ -d "raglite/tests" ]; then
    for file in raglite/tests/test_*.py; do
        if [ -f "$file" ]; then
            filename=$(basename "$file")
            echo "  Moving: $filename"
            mv "$file" "tests/"
        fi
    done
    echo "✅ Root-level tests moved"
fi
echo ""

# Step 6: Clean up empty directories
echo "Step 6: Cleaning up empty directories..."
if [ -d "raglite/tests/unit" ]; then
    # Remove __pycache__ if exists
    rm -rf raglite/tests/unit/__pycache__
    # Try to remove unit directory (will fail if not empty - that's okay)
    rmdir raglite/tests/unit 2>/dev/null && echo "  Removed: raglite/tests/unit/" || echo "  Kept: raglite/tests/unit/ (not empty)"
fi

if [ -d "raglite/tests/integration" ]; then
    rm -rf raglite/tests/integration/__pycache__
    rmdir raglite/tests/integration 2>/dev/null && echo "  Removed: raglite/tests/integration/" || echo "  Kept: raglite/tests/integration/ (not empty)"
fi

if [ -d "raglite/tests/performance" ]; then
    rm -rf raglite/tests/performance/__pycache__
    rmdir raglite/tests/performance 2>/dev/null && echo "  Removed: raglite/tests/performance/" || echo "  Kept: raglite/tests/performance/ (not empty)"
fi

if [ -d "raglite/tests" ]; then
    rm -rf raglite/tests/__pycache__
    # Try to remove main tests directory
    rmdir raglite/tests 2>/dev/null && echo "  Removed: raglite/tests/" || echo "  ℹ️  raglite/tests/ directory kept (contains files/subdirs)"
fi
echo ""

# Step 7: Verify test count
echo "Step 7: Verifying test count..."
echo "  Collecting tests from consolidated tests/ directory..."
TEST_COUNT=$(python -m pytest --collect-only -q tests/ 2>/dev/null | grep -c "test_" || echo "0")
echo "  Tests discovered: $TEST_COUNT"

if [ "$TEST_COUNT" -ge 340 ]; then
    echo "✅ Test consolidation successful! ($TEST_COUNT tests found, expected ~343)"
elif [ "$TEST_COUNT" -ge 250 ]; then
    echo "⚠️  Consolidation may be incomplete ($TEST_COUNT tests, expected ~343)"
    echo "    Check if raglite/tests/ still contains test files"
else
    echo "❌ Test discovery issue ($TEST_COUNT tests, expected ~343)"
    echo "    Run: pytest --collect-only -q tests/"
fi
echo ""

# Step 8: Summary
echo "=========================================="
echo "CONSOLIDATION COMPLETE"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Review changes: git status"
echo "  2. Run tests: pytest tests/ -v"
echo "  3. Check VS Code Test Explorer (should show ~343 tests)"
echo "  4. Commit changes: git add . && git commit -m 'fix: consolidate test suite'"
echo ""
echo "Backup location: $BACKUP_DIR"
echo "To restore: rm -rf raglite/tests && mv $BACKUP_DIR raglite/tests"
echo ""
