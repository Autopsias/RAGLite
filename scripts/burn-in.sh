#!/bin/bash
# burn-in.sh - Standalone burn-in loop for flaky test detection
# Part of RAGLite CI/CD quality pipeline
# Usage: ./scripts/burn-in.sh [iterations] [test_path]
#
# Examples:
#   ./scripts/burn-in.sh                      # 10 iterations, full suite
#   ./scripts/burn-in.sh 20                   # 20 iterations, full suite
#   ./scripts/burn-in.sh 10 tests/unit        # 10 iterations, unit tests only
#   ./scripts/burn-in.sh 100 tests/integration/test_retrieval_integration.py  # 100 iterations, single file

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
ITERATIONS="${1:-10}"
TEST_PATH="${2:-tests/}"

# Validate iterations is a number
if ! [[ "$ITERATIONS" =~ ^[0-9]+$ ]]; then
  echo "Error: Iterations must be a number"
  echo "Usage: $0 [iterations] [test_path]"
  exit 1
fi

# Validate test path exists
if [ ! -e "$TEST_PATH" ]; then
  echo "Error: Test path does not exist: $TEST_PATH"
  exit 1
fi

echo "============================================================"
echo "🔥 BURN-IN LOOP - Flaky Test Detection"
echo "============================================================"
echo ""
echo "Configuration:"
echo "  - Iterations: $ITERATIONS"
echo "  - Test path: $TEST_PATH"
echo "  - Failure policy: ANY failure = FLAKY"
echo ""
echo "Purpose: Run tests multiple times to detect non-deterministic"
echo "         behavior (race conditions, timing issues, etc.)"
echo ""
echo "============================================================"
echo ""

# Verify services are running
echo "Verifying services..."

# Check Qdrant
if curl -sf http://localhost:6333/collections > /dev/null 2>&1; then
  echo -e "${GREEN}✅ Qdrant available at localhost:6333${NC}"
else
  echo -e "${RED}❌ Qdrant not available${NC}"
  echo ""
  echo "Please start Qdrant before running burn-in:"
  echo "  docker run -d -p 6333:6333 --name raglite-qdrant qdrant/qdrant:v1.15.0"
  echo ""
  exit 1
fi

# Check PostgreSQL (optional - warn but don't block)
if docker ps --filter name=raglite-postgresql --format '{{.Names}}' | grep -q raglite-postgresql; then
  echo -e "${GREEN}✅ PostgreSQL available${NC}"
else
  echo -e "${YELLOW}⚠️  PostgreSQL not running${NC}"
  echo "Some integration tests may fail or be skipped."
  echo ""
  echo "To start PostgreSQL:"
  echo "  docker run -d -p 5432:5432 -e POSTGRES_DB=raglite \\"
  echo "    -e POSTGRES_USER=raglite -e POSTGRES_PASSWORD=raglite \\"
  echo "    --name raglite-postgresql postgres:16"
fi

echo ""
echo "Starting burn-in loop..."
echo ""

# Create results directory
RESULTS_DIR=".burn-in-results-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$RESULTS_DIR"

echo "Results will be saved to: $RESULTS_DIR"
echo ""

# Track failures
FAILED_ITERATIONS=0
FAILED_ITERATION_NUMBERS=()

# Run burn-in loop
for i in $(seq 1 $ITERATIONS); do
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "🔥 Iteration $i/$ITERATIONS"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""

  # Run tests and capture output
  LOG_FILE="$RESULTS_DIR/iteration-$i.log"
  XML_FILE="$RESULTS_DIR/iteration-$i.xml"

  if pytest "$TEST_PATH" \
    -n 1 \
    -m "not slow" \
    -v \
    --junitxml="$XML_FILE" \
    2>&1 | tee "$LOG_FILE"; then
    echo -e "${GREEN}✅ Iteration $i PASSED${NC}"
  else
    echo -e "${RED}❌ Iteration $i FAILED${NC}"
    FAILED_ITERATIONS=$((FAILED_ITERATIONS + 1))
    FAILED_ITERATION_NUMBERS+=($i)
  fi

  # Show progress
  PASSED=$((i - FAILED_ITERATIONS))
  echo ""
  echo "Progress: $PASSED/$i passed, $FAILED_ITERATIONS/$i failed"
done

echo ""
echo "============================================================"
echo "🔥 BURN-IN RESULTS"
echo "============================================================"
echo ""
echo "Total iterations: $ITERATIONS"
echo "Passed iterations: $((ITERATIONS - FAILED_ITERATIONS))"
echo "Failed iterations: $FAILED_ITERATIONS"
echo ""

if [ $FAILED_ITERATIONS -gt 0 ]; then
  echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo -e "${RED}❌ FLAKY TESTS DETECTED!${NC}"
  echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo ""
  echo "⚠️  $FAILED_ITERATIONS out of $ITERATIONS iterations failed."
  echo ""
  echo "Failed iterations: ${FAILED_ITERATION_NUMBERS[*]}"
  echo ""
  echo "This indicates non-deterministic test behavior, likely caused by:"
  echo "  - Race conditions in async code"
  echo "  - Timing dependencies (sleeps, timeouts)"
  echo "  - Shared mutable state between tests"
  echo "  - External service flakiness"
  echo "  - Non-deterministic data generation"
  echo ""
  echo "Next steps:"
  echo "  1. Review failure logs in: $RESULTS_DIR"
  echo "  2. Compare failed iterations to identify patterns"
  echo "  3. Add proper test isolation and cleanup"
  echo "  4. Use pytest fixtures for deterministic data"
  echo "  5. Add retries only for known external flakiness"
  echo ""
  echo "Failure rate: $(echo "scale=2; $FAILED_ITERATIONS * 100 / $ITERATIONS" | bc)%"
  echo ""

  # Suggest confidence level based on failure rate
  FAILURE_RATE=$(echo "scale=2; $FAILED_ITERATIONS * 100 / $ITERATIONS" | bc)
  if (( $(echo "$FAILURE_RATE > 10" | bc -l) )); then
    echo -e "${RED}⚠️  HIGH FLAKINESS (>10% failure rate)${NC}"
    echo "These tests are NOT production-ready. Fix immediately."
  elif (( $(echo "$FAILURE_RATE > 5" | bc -l) )); then
    echo -e "${YELLOW}⚠️  MODERATE FLAKINESS (5-10% failure rate)${NC}"
    echo "Tests should be improved before merging."
  else
    echo -e "${YELLOW}⚠️  LOW FLAKINESS (<5% failure rate)${NC}"
    echo "Minor flakiness detected. Consider fixing for long-term reliability."
  fi
  echo ""

  exit 1
else
  echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo -e "${GREEN}✅ ALL ITERATIONS PASSED!${NC}"
  echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo ""
  echo "No flaky tests detected across $ITERATIONS iterations."
  echo ""

  # Provide confidence level
  if [ $ITERATIONS -ge 100 ]; then
    echo "✨ VERY HIGH CONFIDENCE - 100+ iterations passed"
    echo "These tests are production-grade stable."
  elif [ $ITERATIONS -ge 20 ]; then
    echo "✨ HIGH CONFIDENCE - 20+ iterations passed"
    echo "Tests are reliable for production use."
  elif [ $ITERATIONS -ge 10 ]; then
    echo "✨ GOOD CONFIDENCE - 10+ iterations passed"
    echo "Standard burn-in threshold met."
  else
    echo "✨ BASIC CONFIDENCE - $ITERATIONS iterations passed"
    echo "Consider running more iterations for higher confidence."
  fi
  echo ""
  echo "Results saved to: $RESULTS_DIR"
  echo ""

  exit 0
fi
