#!/bin/bash
# ci-local.sh - Mirror CI pipeline execution locally for debugging
# Part of RAGLite CI/CD quality pipeline
# Usage: ./scripts/ci-local.sh [--full] [--skip-lint] [--skip-burn-in]
#
# Examples:
#   ./scripts/ci-local.sh                 # Standard run (3-iteration burn-in)
#   ./scripts/ci-local.sh --full          # Full run (10-iteration burn-in)
#   ./scripts/ci-local.sh --skip-burn-in  # Skip burn-in loop
#   ./scripts/ci-local.sh --skip-lint     # Skip linting checks

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
BURN_IN_ITERATIONS=3
SKIP_LINT=false
SKIP_BURN_IN=false

while [[ $# -gt 0 ]]; do
  case $1 in
    --full)
      BURN_IN_ITERATIONS=10
      shift
      ;;
    --skip-lint)
      SKIP_LINT=true
      shift
      ;;
    --skip-burn-in)
      SKIP_BURN_IN=true
      shift
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--full] [--skip-lint] [--skip-burn-in]"
      exit 1
      ;;
  esac
done

echo "============================================================"
echo "🔍 CI PIPELINE - LOCAL MIRROR"
echo "============================================================"
echo ""
echo "This script mirrors the CI pipeline execution locally."
echo "Perfect for debugging CI failures before pushing."
echo ""
echo "Configuration:"
echo "  - Burn-in iterations: $BURN_IN_ITERATIONS"
echo "  - Skip linting: $SKIP_LINT"
echo "  - Skip burn-in: $SKIP_BURN_IN"
echo ""
echo "============================================================"
echo ""

# Track overall success
ALL_PASSED=true

# ============================================================================
# STAGE 1: Code Quality
# ============================================================================
if [ "$SKIP_LINT" = false ]; then
  echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo -e "${BLUE}📝 STAGE 1: Code Quality${NC}"
  echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo ""

  echo "Running Ruff linter..."
  if ruff check . --output-format=github 2>&1; then
    echo -e "${GREEN}✅ Ruff linting passed${NC}"
  else
    echo -e "${RED}❌ Ruff linting failed${NC}"
    ALL_PASSED=false
  fi
  echo ""

  echo "Running Black formatter check..."
  if black --check --diff raglite/ tests/ scripts/ 2>&1; then
    echo -e "${GREEN}✅ Black formatting passed${NC}"
  else
    echo -e "${RED}❌ Black formatting failed${NC}"
    ALL_PASSED=false
  fi
  echo ""

  echo "Running isort import check..."
  if isort --check-only --diff raglite/ tests/ scripts/ 2>&1; then
    echo -e "${GREEN}✅ isort import sorting passed${NC}"
  else
    echo -e "${RED}❌ isort import sorting failed${NC}"
    ALL_PASSED=false
  fi
  echo ""
else
  echo -e "${YELLOW}⏭️  Skipping linting checks${NC}"
  echo ""
fi

# ============================================================================
# STAGE 2: Test Execution
# ============================================================================
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}🧪 STAGE 2: Test Execution${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Verify services are running
echo "Verifying services..."

# Check Qdrant
if curl -sf http://localhost:6333/collections > /dev/null 2>&1; then
  echo -e "${GREEN}✅ Qdrant available at localhost:6333${NC}"
else
  echo -e "${RED}❌ Qdrant not available${NC}"
  echo "Please start Qdrant: docker run -d -p 6333:6333 --name raglite-qdrant qdrant/qdrant:v1.15.0"
  exit 1
fi

# Check PostgreSQL (optional - only for integration tests)
if docker ps --filter name=raglite-postgresql --format '{{.Names}}' | grep -q raglite-postgresql; then
  echo -e "${GREEN}✅ PostgreSQL available${NC}"
else
  echo -e "${YELLOW}⚠️  PostgreSQL not running (required for integration tests)${NC}"
  echo "To start: docker run -d -p 5432:5432 -e POSTGRES_DB=raglite -e POSTGRES_USER=raglite -e POSTGRES_PASSWORD=raglite --name raglite-postgresql postgres:16"
fi
echo ""

# Unit tests
echo "Running unit tests..."
if pytest tests/unit/ -n 4 --dist loadfile -m "not slow" -v 2>&1; then
  echo -e "${GREEN}✅ Unit tests passed${NC}"
else
  echo -e "${RED}❌ Unit tests failed${NC}"
  ALL_PASSED=false
fi
echo ""

# Integration tests
echo "Running integration tests..."
if pytest tests/integration/ -n 1 -m "not slow" -v 2>&1; then
  echo -e "${GREEN}✅ Integration tests passed${NC}"
else
  echo -e "${RED}❌ Integration tests failed${NC}"
  ALL_PASSED=false
fi
echo ""

# E2E tests
echo "Running E2E tests..."
if pytest tests/e2e/ -n 0 -m "not slow" -v 2>&1; then
  echo -e "${GREEN}✅ E2E tests passed${NC}"
else
  echo -e "${RED}❌ E2E tests failed${NC}"
  ALL_PASSED=false
fi
echo ""

# ============================================================================
# STAGE 3: Burn-In Loop (Flaky Test Detection)
# ============================================================================
if [ "$SKIP_BURN_IN" = false ]; then
  echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo -e "${BLUE}🔥 STAGE 3: Burn-In Loop${NC}"
  echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo ""
  echo "Running burn-in loop ($BURN_IN_ITERATIONS iterations)..."
  echo "This detects flaky tests by running the suite multiple times."
  echo ""

  FAILED_ITERATIONS=0

  for i in $(seq 1 $BURN_IN_ITERATIONS); do
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🔥 Burn-in iteration $i/$BURN_IN_ITERATIONS"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    if pytest tests/ -n 1 -m "not slow" -q 2>&1; then
      echo -e "${GREEN}✅ Iteration $i PASSED${NC}"
    else
      echo -e "${RED}❌ Iteration $i FAILED${NC}"
      FAILED_ITERATIONS=$((FAILED_ITERATIONS + 1))
    fi
  done

  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "🔥 Burn-In Results"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "Total iterations: $BURN_IN_ITERATIONS"
  echo "Failed iterations: $FAILED_ITERATIONS"
  echo ""

  if [ $FAILED_ITERATIONS -gt 0 ]; then
    echo -e "${RED}❌ FLAKY TESTS DETECTED!${NC}"
    echo ""
    echo "⚠️  $FAILED_ITERATIONS out of $BURN_IN_ITERATIONS iterations failed."
    echo "This indicates non-deterministic test behavior."
    echo ""
    ALL_PASSED=false
  else
    echo -e "${GREEN}✅ ALL ITERATIONS PASSED${NC}"
    echo "No flaky tests detected!"
  fi
  echo ""
else
  echo -e "${YELLOW}⏭️  Skipping burn-in loop${NC}"
  echo ""
fi

# ============================================================================
# SUMMARY
# ============================================================================
echo "============================================================"
echo "📊 CI PIPELINE SUMMARY"
echo "============================================================"
echo ""

if [ "$ALL_PASSED" = true ]; then
  echo -e "${GREEN}✅ ALL STAGES PASSED${NC}"
  echo ""
  echo "Your changes are ready for CI/CD!"
  echo "Safe to push to remote."
  echo ""
  exit 0
else
  echo -e "${RED}❌ SOME STAGES FAILED${NC}"
  echo ""
  echo "Please fix the issues above before pushing."
  echo ""
  exit 1
fi
