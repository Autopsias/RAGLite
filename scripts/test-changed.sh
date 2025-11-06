#!/bin/bash
# test-changed.sh - Run only tests affected by changed files
# Part of RAGLite CI/CD quality pipeline
# Usage: ./scripts/test-changed.sh [base_branch]
#
# Examples:
#   ./scripts/test-changed.sh          # Compare against HEAD~1
#   ./scripts/test-changed.sh main     # Compare against main branch
#   ./scripts/test-changed.sh develop  # Compare against develop branch

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================="
echo "🔍 SELECTIVE TESTING - Changed Files Only"
echo "========================================="
echo ""

# Determine comparison base
BASE="${1:-HEAD~1}"
echo "Comparing against: $BASE"
echo ""

# Get changed files
echo "Detecting changed files..."
CHANGED_FILES=$(git diff --name-only "$BASE" 2>/dev/null || echo "")

if [ -z "$CHANGED_FILES" ]; then
  echo -e "${YELLOW}⚠️  No changed files detected${NC}"
  echo "Running full test suite as fallback..."
  echo ""
  pytest tests/ -v
  exit 0
fi

echo -e "${GREEN}Changed files:${NC}"
echo "$CHANGED_FILES" | sed 's/^/  - /'
echo ""

# Analyze changes and determine test strategy
RUN_ALL_TESTS=false
TEST_PATTERNS=()

# Check for critical file changes that require full test run
if echo "$CHANGED_FILES" | grep -qE "(pyproject.toml|pytest.ini|conftest.py|\.github/workflows/)"; then
  echo -e "${YELLOW}⚠️  Critical infrastructure files changed${NC}"
  echo "Running FULL test suite for safety..."
  RUN_ALL_TESTS=true
fi

# Map changed source files to test files
if [ "$RUN_ALL_TESTS" = false ]; then
  echo "Mapping changed files to test modules..."
  echo ""

  # Process each changed file
  while IFS= read -r file; do
    case "$file" in
      raglite/ingestion/*)
        echo "  📁 raglite/ingestion/ → tests/unit/test_ingestion.py, tests/integration/test_ingestion_integration.py"
        TEST_PATTERNS+=("tests/unit/test_ingestion.py" "tests/integration/test_ingestion_integration.py")
        ;;
      raglite/retrieval/*)
        echo "  📁 raglite/retrieval/ → tests/unit/test_retrieval.py, tests/integration/test_retrieval_integration.py"
        TEST_PATTERNS+=("tests/unit/test_retrieval.py" "tests/integration/test_retrieval_integration.py")
        ;;
      raglite/shared/*)
        echo "  📁 raglite/shared/ → tests/unit/test_shared_*.py"
        TEST_PATTERNS+=("tests/unit/test_shared_config.py" "tests/unit/test_shared_models.py" "tests/unit/test_shared_clients.py")
        ;;
      raglite/main.py)
        echo "  📄 raglite/main.py → tests/integration/test_mcp_server.py, tests/e2e/"
        TEST_PATTERNS+=("tests/integration/test_mcp_server.py" "tests/e2e/")
        ;;
      tests/*)
        echo "  🧪 Test file changed → $file"
        TEST_PATTERNS+=("$file")
        ;;
      *.md|docs/*)
        echo "  📚 Documentation only → skipping tests"
        ;;
      *)
        echo "  ❓ Unknown file pattern → $file (running full suite for safety)"
        RUN_ALL_TESTS=true
        break
        ;;
    esac
  done <<< "$CHANGED_FILES"
fi

echo ""
echo "========================================="
echo "🧪 RUNNING TESTS"
echo "========================================="
echo ""

if [ "$RUN_ALL_TESTS" = true ]; then
  echo -e "${YELLOW}Running FULL test suite${NC}"
  echo ""
  pytest tests/ -v -m "not slow"
else
  # Remove duplicates and run selected tests
  UNIQUE_PATTERNS=($(printf '%s\n' "${TEST_PATTERNS[@]}" | sort -u))

  if [ ${#UNIQUE_PATTERNS[@]} -eq 0 ]; then
    echo -e "${GREEN}✅ No test execution needed (documentation changes only)${NC}"
    exit 0
  fi

  echo -e "${GREEN}Running selective tests:${NC}"
  for pattern in "${UNIQUE_PATTERNS[@]}"; do
    echo "  - $pattern"
  done
  echo ""

  # Run pytest with selected test patterns
  pytest "${UNIQUE_PATTERNS[@]}" -v -m "not slow"
fi

echo ""
echo -e "${GREEN}✅ Selective testing complete!${NC}"
echo ""
echo "💡 TIP: To run full suite, use: pytest tests/ -m \"not slow\""
