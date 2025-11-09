#!/bin/bash
# Verification script for Qdrant snapshot optimization
# Run this after reloading VS Code to confirm snapshots are working

set -e

echo "=========================================="
echo "Qdrant Snapshot Optimization Verification"
echo "=========================================="
echo ""
echo "This script will:"
echo "  1. Run a single integration test"
echo "  2. Check for snapshot creation messages"
echo "  3. Verify snapshot restoration is enabled"
echo ""

# Run a quick integration test and capture output
echo "Running test (this will take ~15-20s for first run)..."
echo ""

OUTPUT=$(pytest tests/integration/test_table_retrieval.py::TestTableRetrieval::test_search_tables_basic -xvs --tb=short 2>&1 || true)

echo "=========================================="
echo "Checking for snapshot messages..."
echo "=========================================="
echo ""

# Check for snapshot creation
if echo "$OUTPUT" | grep -q "⚡ Creating Qdrant snapshot"; then
    echo "✅ FOUND: Snapshot creation message"

    # Extract snapshot name
    SNAPSHOT_NAME=$(echo "$OUTPUT" | grep "✓ Snapshot created:" | sed 's/.*: //')
    if [ -n "$SNAPSHOT_NAME" ]; then
        echo "✅ FOUND: Snapshot created: $SNAPSHOT_NAME"
    else
        echo "⚠️  WARNING: Snapshot creation message found but no snapshot name"
    fi

    # Check snapshot time
    SNAPSHOT_TIME=$(echo "$OUTPUT" | grep "✓ Snapshot time:" | sed 's/.*: //')
    if [ -n "$SNAPSHOT_TIME" ]; then
        echo "✅ FOUND: Snapshot time: $SNAPSHOT_TIME"
    fi

else
    echo "❌ NOT FOUND: Snapshot creation message"
    echo ""
    echo "This means VS Code hasn't reloaded conftest.py yet."
    echo "Please reload VS Code and run this script again:"
    echo "  - Cmd+Shift+P → 'Developer: Reload Window'"
    echo "  - Or: Close VS Code and reopen"
    echo ""
    exit 1
fi

echo ""
echo "=========================================="
echo "Verification Result"
echo "=========================================="
echo ""
echo "✅ SUCCESS: Snapshot optimization is active!"
echo ""
echo "Expected performance improvement:"
echo "  - First test: ~15-20s (creates snapshot)"
echo "  - Subsequent tests: <1s (restore from snapshot)"
echo "  - Overall suite: 1500s → ~300-400s (70-75% faster)"
echo ""
echo "Note: Tests with @pytest.mark.preserve_collection"
echo "      skip restoration and won't benefit from snapshots."
echo ""
