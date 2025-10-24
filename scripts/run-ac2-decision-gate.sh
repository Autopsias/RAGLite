#!/bin/bash
# Story 2.5 AC2 DECISION GATE - Run this script to execute the final validation
#
# This script:
# 1. Verifies the full 160-page PDF is ingested (176 chunks expected)
# 2. Runs the AC2 DECISION GATE test (retrieval accuracy ≥70%)
# 3. Runs the AC3 attribution validation (attribution accuracy ≥95%)
# 4. Outputs results to both console and log file
#
# Usage: bash scripts/run-ac2-decision-gate.sh

set -e  # Exit on error

echo "================================================================================"
echo "STORY 2.5 AC2: DECISION GATE VALIDATION"
echo "================================================================================"
echo ""

# Step 1: Verify Qdrant collection has full PDF
echo "Step 1: Verifying Qdrant collection state..."
echo ""

CHUNK_COUNT=$(python -c "from raglite.shared.clients import get_qdrant_client; from raglite.shared.config import settings; q = get_qdrant_client(); info = q.get_collection(settings.qdrant_collection_name); print(info.points_count)")

echo "Current Qdrant collection: $CHUNK_COUNT chunks"
echo "Expected: 176 chunks (from 160-page PDF with fixed 512-token chunking)"
echo ""

if [ "$CHUNK_COUNT" -ne 176 ]; then
    echo "❌ ERROR: Qdrant collection does NOT have the full 160-page PDF!"
    echo "   Current: $CHUNK_COUNT chunks"
    echo "   Expected: 176 chunks"
    echo ""
    echo "You must run the full PDF ingestion first:"
    echo "   python tests/integration/setup_test_data.py"
    echo ""
    echo "This will take ~13-15 minutes to complete."
    exit 1
fi

echo "✅ Qdrant collection verified - proceeding with DECISION GATE test"
echo ""
echo "================================================================================"
echo "Step 2: Running AC2 DECISION GATE Test (retrieval accuracy ≥70%)"
echo "================================================================================"
echo ""

# Run the DECISION GATE test
pytest tests/integration/test_ac3_ground_truth.py::test_ac2_decision_gate_validation -v -s 2>&1 | tee /tmp/ac2_decision_gate_final.log

# Check exit code
if [ ${PIPESTATUS[0]} -eq 0 ]; then
    echo ""
    echo "================================================================================"
    echo "✅ DECISION GATE PASSED - Epic 2 Phase 2A COMPLETE"
    echo "================================================================================"
    echo ""
    echo "Next steps:"
    echo "  1. Review AC1 results in docs/stories/AC1-ground-truth-results.json"
    echo "  2. Update Story 2.5 status to 'Complete'"
    echo "  3. Proceed to Epic 3 planning"
else
    echo ""
    echo "================================================================================"
    echo "❌ DECISION GATE FAILED - Escalate to Phase 2B"
    echo "================================================================================"
    echo ""
    echo "Next steps:"
    echo "  1. Review failure analysis in docs/stories/AC4-failure-mode-analysis.json"
    echo "  2. Update Story 2.5 status with failure details"
    echo "  3. Initiate Phase 2B (Structured Multi-Index)"
    echo "  4. Requires PM approval for Phase 2B"
fi

echo ""
echo "Full log available at: /tmp/ac2_decision_gate_final.log"
