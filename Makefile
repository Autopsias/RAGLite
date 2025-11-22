# RAGLite Test Performance Makefile
# Quick commands for running tests with various performance configurations

.PHONY: help test test-fast test-unit test-integration test-slow test-parallel test-sequential test-watch test-failed test-coverage clean-test install-dev

help: ## Show this help message
	@echo "RAGLite Test Commands"
	@echo "====================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install-dev: ## Install development dependencies with performance plugins
	uv sync --group dev --group test

test: test-optimized ## Run optimized test suite (default) - FASTEST

test-optimized: ## Run tests with optimal parallelization strategy (<12 min target)
	@echo "🚀 RAGLite Optimized Test Suite"
	@echo "================================"
	@echo "Phase 1: Unit tests (483 tests, parallel -n auto)"
	@time uv run pytest tests/unit -n auto --dist loadfile --tb=line
	@echo ""
	@echo "Phase 2: Integration tests (220 tests, single worker for shared fixture)"
	@time uv run pytest tests/integration -n 1 --dist loadfile --tb=line
	@echo ""
	@echo "✅ Test suite complete!"

test-fast: ## Run unit tests only (fastest feedback <2 min)
	@echo "⚡ Running unit tests in parallel..."
	uv run pytest tests/unit -n auto --dist loadfile -x --tb=short

test-unit: ## Run unit tests with coverage
	@echo "📊 Running unit tests with coverage..."
	uv run pytest tests/unit -n auto --dist loadfile --cov=raglite --cov-report=term-missing

test-integration: ## Run integration tests with optimal settings (requires Qdrant)
	@echo "🔗 Running integration tests (single worker for session fixture)..."
	uv run pytest tests/integration -n 1 --dist loadfile --tb=short

test-slow: ## Run slow/e2e tests only
	uv run pytest -n auto --dist loadfile -m "slow or e2e"

test-parallel: ## Run all tests in parallel (explicit)
	uv run pytest -n auto --dist loadfile --durations=20

test-sequential: ## Run tests sequentially (useful for debugging)
	uv run pytest -n 0 -v

test-watch: ## Watch mode - rerun tests on file changes (requires pytest-watch)
	uv run pytest-watch -- -n auto --dist loadfile -m unit

test-failed: ## Rerun only failed tests from last run
	uv run pytest --lf -n auto --dist loadfile

test-coverage: ## Run full test suite with coverage report
	uv run pytest -n auto --dist loadfile --cov=raglite --cov-report=html --cov-report=term-missing
	@echo "Coverage report: htmlcov/index.html"

test-profile: ## Profile test performance and show slowest tests
	uv run pytest -n 0 --durations=50 --durations-min=0.5

test-nocov: ## Run tests without coverage (fastest)
	uv run pytest -n auto --dist loadfile --no-cov

test-benchmark: ## Run performance benchmarks only
	uv run pytest -n 0 --benchmark-only

test-debug: ## Run tests with verbose output and no parallelization
	uv run pytest -n 0 -vv --tb=long --showlocals

test-smoke: ## Run smoke tests only (quick validation)
	uv run pytest -n auto --dist loadfile -m smoke -x

test-p0: ## Run priority 0 (critical) tests only
	uv run pytest -n auto --dist loadfile -m p0

# VS Code Test Explorer Performance Optimization Commands
test-ingest-data: ## Ingest test data for skip-ingestion mode (enables 98% speedup)
	@echo "📥 Ingesting test data for rapid iteration..."
	@echo "This enables --skip-ingestion mode in VS Code Test Explorer"
	@echo ""
	uv run python scripts/ingest-test-data.py
	@echo ""
	@echo "✅ Test data ingested! Next steps:"
	@echo "1. Uncomment '--skip-ingestion' in .vscode/settings.json"
	@echo "2. Reload VS Code window: Cmd+Shift+P → 'Developer: Reload Window'"
	@echo "3. Run tests via Test Explorer → completes in ~1 minute!"

test-skip-ingestion: ## Run tests with skip-ingestion mode (requires test-ingest-data first)
	@echo "⚡ Running tests with skip-ingestion (98% faster)..."
	uv run pytest tests/integration --skip-ingestion -n 1 --dist loadfile

test-vscode: ## Simulate VS Code Test Explorer batch execution (Fix #1)
	@echo "🖥️  Simulating VS Code Test Explorer with batch optimization..."
	@echo "Expected runtime: ~12 minutes (vs 44 minutes unoptimized)"
	@time uv run pytest tests/ -v -n 1 --dist loadfile

clean-test: ## Clean test artifacts and cache
	rm -rf .pytest_cache htmlcov .coverage coverage.xml
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

# Quick development workflows
dev-test: clean-test test-fast ## Clean and run fast unit tests (ideal for TDD)

ci-test: ## Run tests as CI would (with coverage and reports)
	uv run pytest -n auto --dist loadfile --cov=raglite --cov-report=xml --cov-report=term --junitxml=test-results.xml

# Performance analysis
perf-report: ## Generate performance report for all tests
	@echo "Running performance analysis..."
	@uv run pytest -n 0 --durations=0 > test_performance.txt 2>&1
	@echo "Top 20 slowest tests:"
	@grep -E "PASSED|FAILED" test_performance.txt | sort -k2 -rn | head -20
	@echo "\nFull report: test_performance.txt"
