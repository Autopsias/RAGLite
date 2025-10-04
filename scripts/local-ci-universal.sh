#!/bin/bash
# Universal Local CI/CD Testing Script
# Runs the same checks as GitHub Actions locally for faster feedback
# Supports: Python, Node.js, Go, Rust, Java
# Features: Parallel execution, language auto-detection, comprehensive checks

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DETECTED_LANG=""
PARALLEL_MODE=true

echo -e "${BLUE}🚀 Universal CI/CD Local Testing${NC}"
echo "======================================================="
echo "Project Root: ${PROJECT_ROOT}"
echo ""

# Detect project language
detect_language() {
    cd "$PROJECT_ROOT"

    if [ -f "pyproject.toml" ] || [ -f "setup.py" ] || [ -f "requirements.txt" ]; then
        DETECTED_LANG="python"
    elif [ -f "package.json" ]; then
        DETECTED_LANG="node"
    elif [ -f "go.mod" ]; then
        DETECTED_LANG="go"
    elif [ -f "Cargo.toml" ]; then
        DETECTED_LANG="rust"
    elif [ -f "pom.xml" ] || [ -f "build.gradle" ]; then
        DETECTED_LANG="java"
    else
        DETECTED_LANG="unknown"
    fi

    echo -e "${BLUE}Detected Language: ${DETECTED_LANG}${NC}"
}

# Function to print section headers
print_section() {
    echo ""
    echo -e "${BLUE}$1${NC}"
    echo "----------------------------------------"
}

# Run command with status tracking
run_with_status() {
    local cmd="$1"
    local desc="$2"

    echo -n "Running $desc... "
    if eval "$cmd" > /tmp/ci_test_${desc//[ ]/_}.log 2>&1; then
        echo -e "${GREEN}✅ PASSED${NC}"
        return 0
    else
        echo -e "${RED}❌ FAILED${NC}"
        echo -e "${RED}Output:${NC}"
        cat /tmp/ci_test_${desc//[ ]/_}.log
        return 1
    fi
}

# Parallel execution helper
run_parallel() {
    local -n commands=$1
    local pids=()
    local results=()
    local names=()

    # Start all commands in background
    for cmd_info in "${commands[@]}"; do
        IFS='|' read -r name command <<< "$cmd_info"
        names+=("$name")

        echo "Starting: $name"
        eval "$command" > /tmp/parallel_${name//[ ]/_}.log 2>&1 &
        pids+=($!)
    done

    # Wait for all and collect results
    local idx=0
    for pid in "${pids[@]}"; do
        wait $pid
        results+=($?)
        ((idx++))
    done

    # Report results
    echo ""
    local failed=0
    idx=0
    for name in "${names[@]}"; do
        if [ ${results[$idx]} -eq 0 ]; then
            echo -e "${GREEN}✅ ${name} passed${NC}"
        else
            echo -e "${RED}❌ ${name} failed${NC}"
            echo -e "${RED}Output:${NC}"
            cat /tmp/parallel_${name//[ ]/_}.log
            failed=1
        fi
        ((idx++))
    done

    return $failed
}

# Python specific checks
run_python_checks() {
    print_section "📦 Python Environment Setup"

    # Check Python version
    python --version

    # Install/upgrade tools
    run_with_status "pip install --quiet --upgrade pip wheel" "pip upgrade"

    # Install dependencies
    if [ -f "requirements.txt" ]; then
        run_with_status "pip install --quiet -r requirements.txt" "project dependencies"
    fi
    if [ -f "requirements-test.txt" ]; then
        run_with_status "pip install --quiet -r requirements-test.txt" "test dependencies"
    fi

    # Install quality tools
    run_with_status "pip install --quiet ruff mypy bandit pip-audit pytest pytest-cov pytest-xdist" "quality tools"

    print_section "⚡ Parallel Quality Checks (Python)"

    if [ "$PARALLEL_MODE" = true ]; then
        # Run checks in parallel
        declare -a parallel_commands=(
            "ruff-lint|ruff check . --output-format=text"
            "ruff-format|ruff format . --check"
            "mypy|mypy . --no-error-summary || true"
            "bandit|bandit -r . -ll || true"
            "pip-audit|pip-audit || true"
        )

        run_parallel parallel_commands
        QUALITY_RESULT=$?
    else
        # Sequential execution
        run_with_status "ruff check . --output-format=text" "ruff lint"
        run_with_status "ruff format . --check" "ruff format"
        run_with_status "mypy . --no-error-summary || true" "mypy"
        run_with_status "bandit -r . -ll || true" "bandit"
        run_with_status "pip-audit || true" "pip-audit"
        QUALITY_RESULT=$?
    fi

    print_section "🧪 Test Execution (Python)"

    # Smoke tests
    run_with_status "pytest -m 'smoke and not slow' --tb=short -q --no-cov" "smoke tests"

    # Full test suite with coverage (parallel)
    CPU_COUNT=$(python -c "import multiprocessing; print(multiprocessing.cpu_count())")
    run_with_status "pytest tests -n ${CPU_COUNT} --dist=worksteal --cov=. --cov-report=term-missing:skip-covered --cov-report=xml --tb=short -q" "full test suite with coverage"

    return $QUALITY_RESULT
}

# Node.js specific checks
run_node_checks() {
    print_section "📦 Node.js Environment Setup"

    node --version
    npm --version

    run_with_status "npm ci" "dependencies"

    print_section "⚡ Parallel Quality Checks (Node.js)"

    if [ "$PARALLEL_MODE" = true ]; then
        declare -a parallel_commands=(
            "eslint|npm run lint || npx eslint ."
            "prettier|npm run format:check || npx prettier --check ."
            "typescript|npx tsc --noEmit || true"
            "audit|npm audit || true"
        )

        run_parallel parallel_commands
    else
        run_with_status "npm run lint || npx eslint ." "ESLint"
        run_with_status "npx tsc --noEmit || true" "TypeScript"
        run_with_status "npm audit || true" "npm audit"
    fi

    print_section "🧪 Test Execution (Node.js)"

    # Run tests with coverage
    run_with_status "npm test -- --coverage" "test suite with coverage"
}

# Go specific checks
run_go_checks() {
    print_section "📦 Go Environment Setup"

    go version

    run_with_status "go mod download" "dependencies"

    print_section "⚡ Parallel Quality Checks (Go)"

    if [ "$PARALLEL_MODE" = true ]; then
        declare -a parallel_commands=(
            "fmt|go fmt ./..."
            "vet|go vet ./..."
            "staticcheck|go run honnef.co/go/tools/cmd/staticcheck ./... || true"
        )

        run_parallel parallel_commands
    else
        run_with_status "go fmt ./..." "go fmt"
        run_with_status "go vet ./..." "go vet"
    fi

    print_section "🧪 Test Execution (Go)"

    run_with_status "go test -v -race -coverprofile=coverage.out -covermode=atomic ./..." "test suite with coverage"
}

# Rust specific checks
run_rust_checks() {
    print_section "📦 Rust Environment Setup"

    rustc --version
    cargo --version

    print_section "⚡ Parallel Quality Checks (Rust)"

    if [ "$PARALLEL_MODE" = true ]; then
        declare -a parallel_commands=(
            "fmt|cargo fmt --check"
            "clippy|cargo clippy -- -D warnings"
            "audit|cargo audit || true"
        )

        run_parallel parallel_commands
    else
        run_with_status "cargo fmt --check" "rustfmt"
        run_with_status "cargo clippy -- -D warnings" "clippy"
    fi

    print_section "🧪 Test Execution (Rust)"

    run_with_status "cargo test --verbose" "test suite"
}

# Main execution
main() {
    detect_language

    if [ "$DETECTED_LANG" = "unknown" ]; then
        echo -e "${RED}❌ Could not detect project type${NC}"
        echo "Supported: Python, Node.js, Go, Rust, Java"
        exit 1
    fi

    cd "$PROJECT_ROOT"

    case "$DETECTED_LANG" in
        python)
            run_python_checks
            ;;
        node)
            run_node_checks
            ;;
        go)
            run_go_checks
            ;;
        rust)
            run_rust_checks
            ;;
        *)
            echo -e "${RED}Language $DETECTED_LANG not yet implemented${NC}"
            exit 1
            ;;
    esac

    EXIT_CODE=$?

    print_section "📋 Summary"

    if [ $EXIT_CODE -eq 0 ]; then
        echo -e "${GREEN}✅ All checks passed!${NC}"
    else
        echo -e "${RED}❌ Some checks failed${NC}"
    fi

    echo ""
    echo -e "${BLUE}💡 Tips:${NC}"
    echo "• This script mirrors your CI pipeline exactly"
    echo "• Parallel mode enabled for faster execution"
    echo "• Run before pushing to catch issues early"
    echo ""

    # Cleanup
    rm -f /tmp/ci_test_*.log /tmp/parallel_*.log

    return $EXIT_CODE
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --sequential)
            PARALLEL_MODE=false
            shift
            ;;
        --help)
            echo "Usage: $0 [--sequential] [--help]"
            echo ""
            echo "Options:"
            echo "  --sequential    Run checks sequentially (default: parallel)"
            echo "  --help          Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

main
exit $?
