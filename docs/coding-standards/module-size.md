# Module Size Guidelines

**Version:** 1.0
**Status:** Definitive
**Purpose:** Maintain codebase readability and maintainability through file size limits
**Epic:** Epic 3 Prep (Story 3.0.1)

---

## Overview

RAGLite enforces strict module size limits to ensure code remains maintainable, testable, and debuggable. These guidelines prevent monolithic files that complicate refactoring, debugging, and collaborative development.

**Primary Rule:** **No Python file should exceed 1000 lines of code.**

**Rationale:**
- Files >1000 lines are difficult to navigate and understand
- Large files often violate Single Responsibility Principle
- Debugging and testing become exponentially harder with file size
- Code review quality decreases with file size
- Merge conflicts increase with larger files

---

## Size Limits by File Type

| File Type | Maximum Lines | Rationale |
|-----------|--------------|-----------|
| Python modules (`.py`) | **1000 lines** | Primary maintainability threshold |
| Test files (`test_*.py`) | **1500 lines** | Tests can be verbose but should still split by domain |
| Configuration files (`.yaml`, `.json`) | **500 lines** | Config should be focused and modular |
| Documentation (`.md`) | **1000 lines** | Long docs should be sharded into sections |
| Scripts (`scripts/*.py`) | **500 lines** | Scripts should be single-purpose |

---

## Identification Process

### Step 1: Identify Oversized Files

**Command:**
```bash
find raglite -name "*.py" -exec wc -l {} \; | sort -rn | head -20
```

**Output Interpretation:**
- Files >1000 lines: **MUST refactor**
- Files 800-1000 lines: **Monitor** (refactor before adding features)
- Files <800 lines: **Acceptable**

### Step 2: Analyze File Responsibilities

For each oversized file, identify:
1. **Primary domain** (e.g., SQL generation, document ingestion, search)
2. **Distinct responsibilities** (e.g., entity matching, period mapping, metric calculation)
3. **Natural split points** (classes, major function groups, logical sections)
4. **Dependencies** (what imports this file, what it imports)

### Step 3: Plan Refactoring Strategy

Choose refactoring approach based on file structure:

---

## Refactoring Strategies

### Strategy 1: Split by Domain/Responsibility

**When to use:** File contains multiple distinct domains or responsibilities

**Example:**
```
sql_generation.py (1200 lines)
→ sql_generation/
  ├── entity_matching.py (350 lines)
  ├── period_mapping.py (280 lines)
  ├── metric_calculation.py (320 lines)
  └── query_builder.py (250 lines)
```

**Steps:**
1. Create subdirectory for the domain
2. Extract each responsibility into focused module
3. Create `__init__.py` to expose public interface
4. Update imports across codebase
5. Run tests after each extraction

### Strategy 2: Extract Utilities

**When to use:** File has helper functions used by multiple sections

**Example:**
```
pipeline.py (1100 lines)
→ pipeline.py (600 lines - core logic)
→ pipeline_utils.py (500 lines - helpers)
```

**Steps:**
1. Identify pure utility functions (no side effects)
2. Extract to `{module}_utils.py`
3. Update imports
4. Run tests

### Strategy 3: Separate Data Models

**When to use:** File mixes logic and Pydantic models

**Example:**
```
search.py (1050 lines)
→ search.py (650 lines - search logic)
→ search_models.py (400 lines - Pydantic models)
```

**Steps:**
1. Extract all Pydantic models to `{module}_models.py`
2. Update imports
3. Run tests

### Strategy 4: Split by Feature

**When to use:** File implements multiple features for same domain

**Example:**
```
retrieval.py (1200 lines)
→ retrieval/
  ├── vector_search.py (400 lines)
  ├── hybrid_search.py (350 lines)
  ├── reranking.py (300 lines)
  └── attribution.py (150 lines)
```

---

## Refactoring Checklist

**Before Refactoring:**
- [ ] All tests passing (baseline)
- [ ] Git branch created for refactoring
- [ ] File dependencies documented
- [ ] Backup created (commit current state)

**During Refactoring:**
- [ ] Extract one responsibility at a time
- [ ] Run tests after EACH extraction
- [ ] Update imports immediately
- [ ] Maintain 100% test coverage
- [ ] Preserve public API (no breaking changes)

**After Refactoring:**
- [ ] All tests passing (validation)
- [ ] No files >1000 lines remaining
- [ ] Module boundaries documented
- [ ] Code review approved
- [ ] Git commit with clear message

---

## Module Organization Patterns

### Pattern 1: Flat Structure (Simple Modules)

```
raglite/
├── ingestion.py (800 lines) ✅
├── retrieval.py (650 lines) ✅
└── search.py (450 lines) ✅
```

**Use when:** Modules are well-focused and under limit

### Pattern 2: Subdirectory (Domain Split)

```
raglite/
└── ingestion/
    ├── __init__.py (public API exports)
    ├── pipeline.py (400 lines)
    ├── contextual.py (300 lines)
    └── validation.py (200 lines)
```

**Use when:** Domain requires multiple focused modules

### Pattern 3: Layered (Feature + Utilities)

```
raglite/
└── retrieval/
    ├── __init__.py
    ├── search.py (500 lines - core logic)
    ├── search_models.py (300 lines - Pydantic)
    └── search_utils.py (200 lines - helpers)
```

**Use when:** Clear separation between logic, models, and utilities

---

## Testing During Refactoring

**Test Execution Strategy:**
1. **Run full test suite before starting** (establish baseline)
2. **Run relevant tests after each extraction** (quick feedback)
3. **Run full test suite after complete refactoring** (validation)
4. **Monitor test coverage** (should remain 80%+)

**Command:**
```bash
# Quick test during refactoring (specific module)
uv run pytest tests/unit/test_ingestion.py -v

# Full validation after refactoring
uv run pytest --cov=raglite --cov-report=html
```

**Coverage Requirements:**
- Maintain minimum 80% coverage
- No decrease in coverage after refactoring
- Add tests if coverage drops

---

## Import Management

### Pattern: Absolute Imports (Preferred)

```python
# Good - explicit and clear
from raglite.ingestion.pipeline import process_document
from raglite.retrieval.search import search_documents
```

### Pattern: Relative Imports (Within Package)

```python
# Acceptable within same package
from .pipeline import process_document
from ..shared.models import DocumentMetadata
```

### Anti-Pattern: Wildcard Imports

```python
# Bad - unclear dependencies
from raglite.ingestion import *
```

---

## Architecture Review

**Review Criteria:**
- [ ] Module cohesion: Each module has single, clear responsibility
- [ ] Low coupling: Minimal dependencies between modules
- [ ] Clear boundaries: Public APIs well-defined
- [ ] No circular dependencies
- [ ] Logical naming: Module names reflect content

**Review Process:**
1. Developer completes refactoring
2. All tests passing
3. Architecture review by Winston/PM
4. Approval required before merging

---

## Monitoring & Enforcement

### CI/CD Integration

Add to CI pipeline:

```yaml
# .github/workflows/quality.yml
- name: Check module sizes
  run: |
    MAX_LINES=1000
    oversized=$(find raglite -name "*.py" -exec wc -l {} \; | \
                awk -v max=$MAX_LINES '$1 > max {print $2, $1}')
    if [ ! -z "$oversized" ]; then
      echo "Files exceeding $MAX_LINES lines:"
      echo "$oversized"
      exit 1
    fi
```

### Regular Audits

**Quarterly Review:**
- Run file size audit
- Identify files approaching limit (>800 lines)
- Plan proactive refactoring

**Command:**
```bash
# Quarterly audit script
./scripts/audit-module-sizes.sh
```

---

## Exceptions

**Rare exceptions may be granted for:**
- Generated code (migrations, protobuf)
- Legacy code being incrementally refactored
- Complex algorithms requiring cohesion

**Exception Process:**
1. Document justification in code comments
2. Architecture review required
3. Time-bound exception with refactoring plan
4. Track in technical debt register

---

## Examples

### Example 1: SQL Generation Refactoring (Story 3.0.1)

**Before:** `sql_generation.py` (1200 lines)

**After:**
```
sql_generation/
├── __init__.py (50 lines - public API)
├── entity_matching.py (350 lines)
├── period_mapping.py (280 lines)
├── metric_calculation.py (320 lines)
└── query_builder.py (250 lines)
```

**Outcome:**
- 4 focused modules
- Each <400 lines
- Clear responsibilities
- Easier testing and debugging

### Example 2: Ingestion Pipeline (Hypothetical)

**Before:** `pipeline.py` (1100 lines)

**After:**
```
ingestion/
├── pipeline.py (600 lines - orchestration)
├── pipeline_utils.py (300 lines - helpers)
└── pipeline_models.py (200 lines - Pydantic)
```

**Outcome:**
- Logic separated from utilities and models
- Core pipeline easier to understand
- Models reusable across modules

---

## Tools & Scripts

### Size Audit Script

Location: `scripts/audit-module-sizes.sh`

```bash
#!/bin/bash
# Audit module sizes and report oversized files

MAX_LINES=1000
WARN_LINES=800

echo "=== Module Size Audit ==="
echo "Max allowed: $MAX_LINES lines"
echo "Warning threshold: $WARN_LINES lines"
echo

oversized=$(find raglite -name "*.py" -exec wc -l {} \; | \
            awk -v max=$MAX_LINES '$1 > max {print $2, $1}' | \
            sort -k2 -rn)

warnings=$(find raglite -name "*.py" -exec wc -l {} \; | \
           awk -v warn=$WARN_LINES -v max=$MAX_LINES \
           '$1 > warn && $1 <= max {print $2, $1}' | \
           sort -k2 -rn)

if [ ! -z "$oversized" ]; then
  echo "🚨 OVERSIZED FILES (>$MAX_LINES lines):"
  echo "$oversized"
  echo
fi

if [ ! -z "$warnings" ]; then
  echo "⚠️  WARNING: Approaching limit ($WARN_LINES-$MAX_LINES lines):"
  echo "$warnings"
  echo
fi

if [ -z "$oversized" ] && [ -z "$warnings" ]; then
  echo "✅ All modules within size limits"
fi
```

---

**Last Updated:** 2025-11-07
**Maintained By:** Architecture Team (Winston)
**Review Frequency:** Quarterly + Epic kickoffs
