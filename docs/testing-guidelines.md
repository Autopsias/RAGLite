# RAGLite Testing Guidelines

**Version:** 1.0
**Last Updated:** 2025-11-05
**Owner:** Murat (Test Architect) + Development Team

---

## Overview

This document defines testing standards, conventions, and best practices for the RAGLite project. All developers must follow these guidelines when writing tests to ensure consistency, maintainability, and traceability.

---

## Test ID System

**Status:** ✅ Implemented (Story 3-0-6)

All tests MUST include a unique test ID using the `@pytest.mark.test_id()` marker.

### Format

```
{epic}.{story}-{type}-{seq}
```

**Components:**
- `{epic}.{story}`: Epic and story number (e.g., `2.10`, `3.1`, `0.1`)
- `{type}`: Test type - one of: `UNIT`, `INTEGRATION`, `E2E`, `PERF`
- `{seq}`: Three-digit sequential number (`001`, `002`, `003`, ...)

### Examples

```python
# Unit test example
@pytest.mark.test_id("2.10-UNIT-001")
def test_sql_only_classification() -> None:
    """Test SQL_ONLY query classification.

    Test ID: 2.10-UNIT-001
    Story: 2.10 (Query Classification Over-Routing Fix)
    Priority: P1 (High)
    """
    # Test logic...


# Integration test example
@pytest.mark.test_id("2.5-INTEGRATION-003")
@pytest.mark.asyncio
async def test_hybrid_search_integration() -> None:
    """Test hybrid search with BM25 + semantic search.

    Test ID: 2.5-INTEGRATION-003
    Story: 2.5 (AC3 Validation & Optimization)
    Priority: P1 (High)
    """
    # Test logic...


# End-to-end test example
@pytest.mark.test_id("2.5-E2E-001")
@pytest.mark.slow
@pytest.mark.asyncio
async def test_ac1_full_ground_truth_execution() -> AccuracyMetrics:
    """Execute all 50 ground truth queries (accuracy gate).

    Test ID: 2.5-E2E-001
    Story: 2.5 (AC3 Validation & Optimization)
    Priority: P0 (Critical) - Accuracy gate for Epic 2
    """
    # Test logic...


# Performance test example
@pytest.mark.test_id("2.1-PERF-001")
def test_classification_latency() -> None:
    """Test classification latency <50ms (AC1 requirement).

    Test ID: 2.1-PERF-001
    Story: 2.1 (pypdfium Backend Implementation)
    Priority: P2 (Medium)
    """
    # Test logic...
```

### Test Type Definitions

| Type | Description | Location | External Dependencies |
|------|-------------|----------|----------------------|
| **UNIT** | Tests single functions/classes in isolation | `tests/unit/` | None (mocks only) |
| **INTEGRATION** | Tests multiple modules working together | `tests/integration/` | Qdrant, PostgreSQL |
| **E2E** | Tests complete user workflows end-to-end | `tests/e2e/` | All services, real data |
| **PERF** | Performance benchmarks and latency tests | `tests/unit/` or `tests/integration/` | May require full data |

### Benefits

✅ **Instant Traceability**: CI failure "2.10-UNIT-001 failed" → Story 2.10
✅ **Automated Coverage**: Generate story→test mapping reports
✅ **Easy Navigation**: Jump directly to test from test ID
✅ **Clear Communication**: Bug reports reference specific test IDs

### Usage

**Writing a New Test:**

```python
# 1. Determine story (e.g., Story 3.1 - Agentic Framework Integration)
# 2. Determine type (e.g., UNIT test)
# 3. Find next sequence number (check existing 3.1-UNIT-* tests)
# 4. Add marker + update docstring

@pytest.mark.test_id("3.1-UNIT-004")
def test_agent_initialization() -> None:
    """Test agent initializes with correct configuration.

    Test ID: 3.1-UNIT-004
    Story: 3.1 (Agentic Framework Integration)
    Priority: P1 (High)
    """
    # Test logic...
```

**Finding Tests for a Story:**

```bash
# Search for all tests related to Story 2.10
grep -r "2.10-" tests/

# Generate coverage report
python scripts/generate-test-coverage-report.py
```

**Running Tests by ID Pattern:**

```bash
# Run all Story 2.10 tests
pytest -k "2.10" -v

# Run all unit tests for Epic 3
pytest tests/unit/ -k "3." -v
```

### Validation

The pytest configuration validates:
- ✅ Format correctness (regex pattern)
- ✅ Uniqueness (no duplicate IDs)
- ✅ Required fields (test ID in docstring)

Invalid test IDs will cause pytest to fail during test collection.

---

## Priority Classification System

**Status:** 🔄 In Progress (Story 3-0-7)

All tests MUST include a priority marker indicating criticality.

### Priority Levels

| Priority | Definition | Execution | % of Suite | Examples |
|----------|-----------|-----------|------------|----------|
| **P0 (Critical)** | Accuracy gates, security, data corruption prevention | Every commit | 15-20% | Ground truth validation, SQL injection tests |
| **P1 (High)** | Core features, common user workflows | Pre-merge | 30-40% | Query classification, hybrid search, MCP server |
| **P2 (Medium)** | Edge cases, integrations, performance optimizations | Nightly | 30-40% | Transposed tables, fuzzy matching edge cases |
| **P3 (Low)** | Nice-to-have, rare scenarios, performance benchmarks | Weekly | 10-20% | Performance regression tests, rare errors |

### Classification Decision Tree

```
Q1: Does failure block Epic completion or corrupt user data?
    YES → P0 (Critical)
    NO → Continue

Q2: Is this a core feature used in >50% of user queries?
    YES → P1 (High)
    NO → Continue

Q3: Is this an edge case or integration with external system?
    YES → P2 (Medium)
    NO → P3 (Low)
```

### Usage

```python
@pytest.mark.test_id("2.10-UNIT-001")
@pytest.mark.priority("P1")  # Core feature
def test_sql_only_classification() -> None:
    """Test SQL_ONLY query classification.

    Test ID: 2.10-UNIT-001
    Story: 2.10 (Query Classification Over-Routing Fix)
    Priority: P1 (High) - Core feature, used in all queries
    """
    # Test logic...
```

### Running Tests by Priority

```bash
# Smoke tests (P0 only - 2 min)
pytest -m "priority('P0')"

# Pre-merge tests (P0+P1 - 10 min)
pytest -m "priority('P0') or priority('P1')"

# Full suite (all priorities - 30 min)
pytest tests/
```

**Note:** Full priority system implementation tracked in Story 3-0-7.

---

## Test Structure

### Required Elements

Every test MUST include:

1. **Test ID marker**: `@pytest.mark.test_id("{id}")`
2. **Priority marker**: `@pytest.mark.priority("{level}")`
3. **Docstring**: Including test ID, story, and priority
4. **Type hints**: All parameters and return values
5. **Assertions**: Explicit validation with clear messages

### Template

```python
@pytest.mark.test_id("{epic}.{story}-{type}-{seq}")
@pytest.mark.priority("{P0|P1|P2|P3}")
def test_something() -> None:
    """Brief description of what test validates.

    Test ID: {epic}.{story}-{type}-{seq}
    Story: {story_number} ({Story Name})
    Priority: {priority} ({Level Name}) - {Justification}

    Test Structure:
        - GIVEN: Initial conditions/setup
        - WHEN: Action being tested
        - THEN: Expected outcome

    Args:
        (if any)

    Returns:
        (if any)
    """
    # GIVEN: Initial conditions
    # Setup code...

    # WHEN: Action being tested
    # Action code...

    # THEN: Expected outcome
    # Assertions with clear messages
    assert result == expected, f"Expected {expected}, got {result}"
```

### BDD Structure (Recommended)

Use Given-When-Then comments for clarity:

```python
def test_query_classification() -> None:
    """Test query classification logic."""
    # GIVEN a query with metric + temporal indicators
    query = "What is the exact revenue in Q3 2024?"

    # WHEN classifying the query
    result = classify_query(query)

    # THEN it should be classified as SQL_ONLY
    assert result == QueryType.SQL_ONLY, (
        f"Expected SQL_ONLY for metric+temporal query, got {result.value}"
    )
```

---

## Test Organization

### Directory Structure

```
tests/
├── unit/                 # Unit tests (no external dependencies)
│   ├── test_*.py
├── integration/          # Integration tests (Qdrant, PostgreSQL)
│   ├── test_*.py
│   └── conftest.py       # Integration-specific fixtures
├── e2e/                  # End-to-end tests
│   ├── test_*.py
├── fixtures/             # Test data and fixtures
│   ├── ground_truth.py
│   └── sample_data.py
└── conftest.py           # Shared fixtures and configuration
```

### File Naming

- Test files: `test_<module_name>.py`
- Fixture files: `<fixture_name>.py`
- Helper files: `<helper_name>.py`

### Test Naming

- Test functions: `test_<what_is_being_tested>`
- Be specific: `test_sql_only_classification` not `test_classify`
- Use snake_case consistently

---

## Fixtures and Test Data

### Fixture Scopes

Use appropriate fixture scopes for performance:

```python
# Session-scoped: Expensive operations (mock clients)
@pytest.fixture(scope="session")
def mock_qdrant_client() -> MagicMock:
    """Session-scoped mock to avoid recreation."""
    return MagicMock()

# Module-scoped: Shared immutable data
@pytest.fixture(scope="module")
def sample_document_metadata() -> DocumentMetadata:
    """Module-scoped for immutable metadata."""
    return DocumentMetadata(...)

# Function-scoped: Test isolation required
@pytest.fixture
def sample_chunk() -> Chunk:
    """Function-scoped when tests modify data."""
    return Chunk(...)
```

### Data Factories (Recommended)

Use factory functions instead of hardcoded data:

```python
# tests/factories/document_factory.py
def create_document_metadata(**overrides):
    """Factory for DocumentMetadata with sensible defaults."""
    defaults = {
        "filename": "test_report.pdf",
        "doc_type": "PDF",
        "page_count": 10,
    }
    return DocumentMetadata(**{**defaults, **overrides})

# Usage in tests
metadata = create_document_metadata(page_count=50)
```

---

## Assertions

### Best Practices

- ✅ Use explicit assertions with clear messages
- ✅ One logical assertion per test (focus)
- ✅ Include actual vs expected in failure messages
- ❌ Avoid bare `assert` without message
- ❌ Don't use try/except to control test flow

### Examples

```python
# ✅ Good: Clear message with context
assert result == QueryType.SQL_ONLY, (
    f"Expected SQL_ONLY for query with metric+temporal, "
    f"got {result.value}"
)

# ✅ Good: Threshold validation with context
assert accuracy >= 0.70, (
    f"Retrieval accuracy {accuracy:.1%} < 70% "
    f"(Story 2.5 AC2 requirement)"
)

# ❌ Bad: No message
assert result == expected

# ❌ Bad: Try-except for flow control
try:
    result = function_that_might_fail()
    assert result is not None
except Exception:
    pass  # Silently continues - hides real issues
```

---

## Test Markers

### Standard Markers

```python
# Slow tests (>10 min runtime, requires full data)
@pytest.mark.slow
@pytest.mark.skipif(not pytest.run_slow, reason="Run with: pytest --run-slow")

# Async tests
@pytest.mark.asyncio

# xdist worker grouping (prevent race conditions)
@pytest.mark.xdist_group(name="embedding_model")

# Test ID (required)
@pytest.mark.test_id("2.10-UNIT-001")

# Priority (required after Story 3-0-7)
@pytest.mark.priority("P1")
```

### Custom Markers

Register custom markers in `tests/conftest.py`:

```python
def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "custom_marker(param): Description of what it does"
    )
```

---

## Running Tests

### Basic Commands

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/unit/test_query_classifier.py

# Run specific test
pytest tests/unit/test_query_classifier.py::test_sql_only_classification

# Run with verbose output
pytest tests/ -v

# Run with coverage
pytest --cov=raglite --cov-report=html
```

### Priority-Based Execution

```bash
# P0 smoke tests (2 min)
pytest -m "priority('P0')"

# P0+P1 pre-merge (10 min)
pytest -m "priority('P0') or priority('P1')"

# Full suite (30 min)
pytest tests/
```

### Test Selection

```bash
# Run tests by keyword
pytest -k "classification" -v

# Run tests for specific story
pytest -k "2.10" -v

# Run unit tests only
pytest tests/unit/

# Run integration tests only
pytest tests/integration/

# Skip slow tests
pytest -m "not slow"
```

### Parallel Execution

```bash
# Run tests in parallel (4 workers)
pytest tests/ -n 4

# Auto-detect worker count
pytest tests/ -n auto
```

---

## Coverage Requirements

### Targets

- **Unit tests**: 80%+ line coverage
- **Integration tests**: Cover all major workflows
- **E2E tests**: Cover critical user journeys

### Measuring Coverage

```bash
# Generate coverage report
pytest --cov=raglite --cov-report=html

# View report
open htmlcov/index.html

# Coverage with branch analysis
pytest --cov=raglite --cov-branch --cov-report=term-missing
```

---

## CI Integration

### GitHub Actions Workflows

RAGLite uses priority-based CI workflows to optimize test execution time and cost.

**Smoke Tests (P0 - 6 min):**
- Runs on every push to main, epic branches, and story branches
- Critical path validation only (30 tests)
- Fastest feedback for breaking changes
- Command: `pytest -k "priority and P0"`

**Pre-Merge Tests (P0+P1 - 20 min):**
- Runs after smoke tests pass
- Required for PR merge (90 tests)
- Core features + critical path
- Command: `pytest -k "priority and (P0 or P1)"`
- Includes code coverage reporting

**Full Test Suite (All priorities - 40 min):**
- Runs nightly at 2 AM UTC
- Includes all 184 tests + slow tests
- Comprehensive validation with coverage
- Trigger: Nightly schedule, `[full-tests]` in commit message, or manual dispatch
- Command: `pytest tests/ --run-slow -m ""`

**Manual Workflow Dispatch:**
- GitHub UI: Actions → Priority-Based Test Execution → Run workflow
- Choose: smoke, pre-merge, or full test suite

### CI Cost Optimization

**Before priority system:**
- Full suite every commit: ~40 min × 50 commits/day = 33.2 hours/day

**After priority system:**
- Pre-merge (P0+P1): ~20 min × 50 commits/day = 16.7 hours/day
- **Savings: 50% reduction in CI time**

### Branch Protection Rules

Recommended settings for main branch:
- Require "Pre-Merge (P0+P1)" workflow to pass
- Require code coverage ≥80%
- Require up-to-date branches before merge

### CI Configuration

See `.github/workflows/test-priority-based.yml` for complete workflow definition.

---

## Test Quality Standards

### Definition of Done (per TEA review)

✅ **Deterministic**: No hard waits, conditionals, or random data
✅ **Isolated**: Tests clean up resources, no shared state
✅ **Fast**: Unit tests <1s, integration tests <1.5min per test
✅ **Focused**: ≤300 lines per test file
✅ **Explicit**: Clear assertions with messages
✅ **Traceable**: Test ID links to story
✅ **Prioritized**: P0/P1/P2/P3 classification

### Code Review Checklist

Before submitting tests for review:

- [ ] All tests have test IDs
- [ ] All tests have priorities
- [ ] Docstrings include test ID, story, priority
- [ ] Given-When-Then structure present
- [ ] No hard waits (`sleep`, `waitForTimeout`)
- [ ] No conditionals controlling test flow
- [ ] Explicit assertions with clear messages
- [ ] Fixtures use appropriate scopes
- [ ] All tests pass locally

---

## Troubleshooting

### Common Issues

**Issue: "Invalid test_id format"**
- **Solution**: Use format `{epic}.{story}-{type}-{seq}` (e.g., `2.10-UNIT-001`)

**Issue: "Duplicate test_id"**
- **Solution**: Check for existing test with same ID, increment sequence number

**Issue: "Test fails only in CI"**
- **Solution**: Check for race conditions, ensure proper xdist grouping

**Issue: "Slow test timeout"**
- **Solution**: Add `@pytest.mark.slow` and increase timeout

---

## References

- **Test Quality Review**: `docs/test-review.md`
- **Story 3-0-6**: `docs/stories/3-0-6-test-id-traceability-system.md`
- **Story 3-0-7**: `docs/stories/3-0-7-priority-classification-system.md`
- **Knowledge Base**: `bmad/bmm/testarch/knowledge/`

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-05 | Initial version with test ID system (Story 3-0-6) |

---

**Questions or Feedback?**

Contact Murat (Test Architect) or raise in team standup.
