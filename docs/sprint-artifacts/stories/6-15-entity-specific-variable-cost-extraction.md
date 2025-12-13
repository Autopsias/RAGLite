# Story 6.15: Entity-Specific Variable Cost Extraction

Status: ready-for-dev

## Story

As a **system**,
I want **to implement entity detection in Variable Cost extraction to filter Portugal-only data and normalize to EUR/ton**,
so that **forecasting accuracy improves by eliminating multi-entity data mixing**.

## Epic Reference

- **Epic:** 6 - Advanced Forecasting with External Data
- **Sprint Change Proposal:** SCP-2025-12-12-001
- **Priority:** P0 (Critical)
- **Estimated Effort:** 4 hours

## Problem Statement

Variable Cost MAPE is at **41.43%** (target <8%), making it the worst-performing metric in the forecasting system. Root cause analysis identified:

1. **Multi-Entity Data Mixing:** Variable Cost data mixes Portugal + Tunisia + Brazil values
2. **High Coefficient of Variation:** 33% CV due to currency/entity mixing (target: <15%)
3. **No Entity Detection:** Current extraction does not filter by geographic entity
4. **Unit Inconsistency:** Values in EUR/ton, BRL/ton, TND/ton mixed without normalization

## Acceptance Criteria

### AC1: Entity Detection Accuracy

**Given** a financial document chunk containing Variable Cost data with entity context
**When** the entity detection algorithm processes the chunk text
**Then** the algorithm correctly identifies Portugal/Tunisia/Brazil with >95% accuracy

**Verification:**
```python
# Test entity detection patterns
test_chunks = [
    ("Portugal | Variable Costs | (281,1) EUR/ton", "portugal"),
    ("Tunisia Variable Cost TND/ton", "tunisia"),
    ("Brazil Custos Variáveis BRL/ton", "brazil"),
    ("Custos Variáveis | EUR/ton | (260.5)", "portugal"),  # Portuguese text = Portugal
]
for chunk_text, expected_entity in test_chunks:
    detected = detect_entity(chunk_text)
    assert detected == expected_entity, f"Expected {expected_entity}, got {detected}"
```

### AC2: Portugal-Only Coefficient of Variation

**Given** the Variable Cost time series extracted from financial documents
**When** filtering to Portugal-only data with entity detection enabled
**Then** the coefficient of variation is <15% (vs 33% current mixed-entity)

**Verification:**
```python
# Extract Variable Cost with entity filter
data = await extract_variable_cost_from_qdrant_chunks(entity="portugal")
values = [p.value for p in data.points]
cv = (statistics.stdev(values) / statistics.mean(values)) * 100
assert cv < 15, f"CV {cv:.1f}% exceeds 15% target"
```

### AC3: EUR/ton Range Validation

**Given** a Variable Cost value extracted from a financial document
**When** the value is from Portugal-only data
**Then** the value falls within the valid EUR/ton range (-150 to -350)

**Verification:**
```python
# All Portugal Variable Cost values should be negative (outflows) in EUR/ton range
for point in data.points:
    assert -350 <= point.value <= -150, f"Value {point.value} outside EUR/ton range"
```

### AC4: Variable Cost MAPE Improvement

**Given** the Variable Cost forecasting with entity-specific extraction
**When** running MAPE validation with holdout test set
**Then** Variable Cost MAPE improves to <25% (from 41%)

**Verification:**
```bash
# Run validation script
uv run python scripts/validate-cement-forecasting-12vars.py --variable variable_cost
# Expected output: variable_cost MAPE < 25%
```

### AC5: No Regression in Other Metrics

**Given** the changes to entity detection in timeseries_extract.py
**When** running full forecasting validation suite
**Then** no regression occurs in other metric extraction (revenue, EBITDA, sales_volume, etc.)

**Verification:**
```bash
# Run full validation before and after
uv run python scripts/validate-cement-forecasting-12vars.py --full-ensemble --real-data
# Compare: Avg MAPE must remain <= baseline (currently ~2.05%)
```

## Tasks / Subtasks

### Task 1: Implement Entity Detection Patterns (AC: 1)

- [ ] **1.1** Define ENTITY_PATTERNS constant in `raglite/forecasting/timeseries_extract.py`:
  ```python
  ENTITY_PATTERNS = {
      "portugal": ["Portugal", "PT", "Custos Variáveis", "EUR/ton", "EUR/m³"],
      "tunisia": ["Tunisia", "TN", "TND", "Tunisie", "TND/ton"],
      "brazil": ["Brazil", "BR", "BRL", "Brasil", "BRL/ton"],
  }
  ```

- [ ] **1.2** Create `detect_entity(text: str) -> str | None` function:
  - Scan chunk text for entity pattern matches
  - Return canonical entity name ("portugal", "tunisia", "brazil")
  - Return None if no entity detected (default to portugal)
  - Case-insensitive matching

- [ ] **1.3** Add unit tests for entity detection in `tests/unit/test_entity_detection.py`

### Task 2: Update Variable Cost Extraction with Entity Filter (AC: 2, 3)

- [ ] **2.1** Modify `extract_variable_cost_from_qdrant_chunks()` to accept `entity` parameter
- [ ] **2.2** Filter chunks by detected entity before value extraction
- [ ] **2.3** Add EUR/ton range validation (-150 to -350 for Portugal)
- [ ] **2.4** Skip chunks from non-matching entities (log warning)
- [ ] **2.5** Handle currency normalization hints (EUR vs BRL vs TND)

### Task 3: Integrate Entity Detection in SQL Extraction (AC: 1, 2)

- [ ] **3.1** Update `extract_timeseries_from_sql()` to filter by entity when available
- [ ] **3.2** Add entity column check in financial_tables query
- [ ] **3.3** Ensure fallback to Qdrant extraction uses entity filter

### Task 4: Create Integration Tests (AC: 4, 5)

- [ ] **4.1** Create `tests/integration/test_variable_cost_extraction.py`:
  - Test entity detection accuracy (>95%)
  - Test CV reduction (<15%)
  - Test EUR/ton range validation
  - Test MAPE improvement validation

- [ ] **4.2** Add regression test to ensure other metrics unaffected

### Task 5: Validation and Documentation (AC: 4)

- [ ] **5.1** Run full validation suite and document results
- [ ] **5.2** Update docstrings in modified functions
- [ ] **5.3** Add inline comments explaining entity detection logic

## Dev Notes

### Architecture Reference

**Source:** `docs/architecture/6-external-data-pipeline-epic-6.md#Entity Detection Architecture`

```
+-------------------+     +-------------------+     +-------------------+
|   Qdrant Chunks   |---->| Entity Detector   |---->| Portugal-Only     |
|   (mixed data)    |     | (PT/TN/BR)        |     | Time Series       |
+-------------------+     +-------------------+     +-------------------+
                                 |
                          +------+------+
                          v             v
                     +---------+   +---------+
                     |EUR/ton  |   |Validate |
                     |Normalize|   |Range    |
                     +---------+   +---------+
```

### Files to Modify

| File | Changes |
|------|---------|
| `raglite/forecasting/timeseries_extract.py` | Add ENTITY_PATTERNS, detect_entity(), update extraction functions |
| `tests/integration/test_variable_cost_extraction.py` | New file - validation tests |
| `tests/unit/test_entity_detection.py` | New file - unit tests for entity detection |

### Existing Code Patterns

The current `extract_variable_cost_from_qdrant_chunks()` function (lines 381-590 of timeseries_extract.py) already:
- Handles European decimal format (comma as decimal separator)
- Filters for EUR/ton range (-100 to -400)
- Extracts from markdown table rows

**Extend this function** to add entity detection filtering BEFORE value extraction.

### Entity Detection Implementation

```python
# Entity detection patterns (add near line 110 after existing patterns)
ENTITY_PATTERNS = {
    "portugal": ["Portugal", "PT", "Custos Variáveis", "EUR/ton", "EUR/m³"],
    "tunisia": ["Tunisia", "TN", "TND", "Tunisie", "TND/ton"],
    "brazil": ["Brazil", "BR", "BRL", "Brasil", "BRL/ton"],
}

def detect_entity(text: str) -> str | None:
    """Detect geographic entity from chunk text.

    Story 6.15: Identifies Portugal/Tunisia/Brazil from context patterns.

    Args:
        text: Chunk text to analyze

    Returns:
        Canonical entity name or None if undetectable
    """
    text_upper = text.upper()

    # Check each entity's patterns
    for entity, patterns in ENTITY_PATTERNS.items():
        for pattern in patterns:
            if pattern.upper() in text_upper:
                return entity

    return None  # Unknown entity
```

### Value Range Reference (from actual data)

| Entity | Currency | Typical Range | Unit |
|--------|----------|---------------|------|
| Portugal | EUR | -150 to -350 | EUR/ton |
| Tunisia | TND | -200 to -500 | TND/ton |
| Brazil | BRL | -400 to -800 | BRL/ton |

### Critical: Preserve Existing Functionality

The `extract_variable_cost_from_qdrant_chunks()` function is already called as a fallback from `extract_timeseries_from_sql()` (lines 1641-1650). Changes MUST:
- Maintain backward compatibility with existing callers
- Not break the fallback chain (SQL -> Qdrant)
- Preserve European decimal handling
- Keep existing logging patterns

### Testing Strategy

1. **Unit Tests:** Entity detection patterns (test_entity_detection.py)
2. **Integration Tests:** Full extraction with entity filter (test_variable_cost_extraction.py)
3. **Regression Tests:** Verify other metrics unaffected
4. **Validation Script:** `scripts/validate-cement-forecasting-12vars.py`

### Performance Considerations

- Entity detection adds minimal overhead (simple string matching)
- No new API calls or database queries
- No model loading required
- Expected latency impact: <10ms per extraction

## Project Structure Notes

### Alignment with Repository Structure

- New test files go in `tests/integration/` and `tests/unit/`
- Production code changes in `raglite/forecasting/timeseries_extract.py`
- No new dependencies required (uses existing stdlib)

### Detected Conflicts

None - this story adds new functionality without conflicting with existing patterns.

## Testing Requirements

### Unit Tests (tests/unit/test_entity_detection.py)

```python
import pytest
from raglite.forecasting.timeseries_extract import detect_entity, ENTITY_PATTERNS

class TestEntityDetection:
    """Test entity detection for Variable Cost extraction."""

    def test_detect_portugal_explicit(self):
        """Portugal keyword detected."""
        assert detect_entity("Portugal Variable Cost") == "portugal"

    def test_detect_portugal_currency(self):
        """EUR/ton implies Portugal."""
        assert detect_entity("Variable Cost | EUR/ton | (281.1)") == "portugal"

    def test_detect_portugal_portuguese_text(self):
        """Portuguese text implies Portugal."""
        assert detect_entity("Custos Variáveis | (260.5)") == "portugal"

    def test_detect_tunisia(self):
        """Tunisia detected from TN or TND."""
        assert detect_entity("Tunisia TND/ton Variable Cost") == "tunisia"

    def test_detect_brazil(self):
        """Brazil detected from BRL."""
        assert detect_entity("Brazil BRL/ton Custos") == "brazil"

    def test_detect_unknown_returns_none(self):
        """Unknown entity returns None."""
        assert detect_entity("Some random text without entity") is None

    def test_case_insensitive(self):
        """Detection is case-insensitive."""
        assert detect_entity("PORTUGAL variable cost") == "portugal"
        assert detect_entity("portugal variable cost") == "portugal"
```

### Integration Tests (tests/integration/test_variable_cost_extraction.py)

```python
import pytest
import statistics
from raglite.forecasting.timeseries_extract import extract_variable_cost_from_qdrant_chunks

@pytest.mark.integration
class TestVariableCostExtraction:
    """Integration tests for entity-specific Variable Cost extraction."""

    @pytest.mark.asyncio
    async def test_portugal_only_cv_under_15_percent(self):
        """AC2: Portugal-only CV < 15%."""
        data = await extract_variable_cost_from_qdrant_chunks(entity="portugal")
        values = [abs(p.value) for p in data.points]
        cv = (statistics.stdev(values) / statistics.mean(values)) * 100
        assert cv < 15, f"CV {cv:.1f}% exceeds 15% target"

    @pytest.mark.asyncio
    async def test_values_in_eur_ton_range(self):
        """AC3: All values in EUR/ton range (-150 to -350)."""
        data = await extract_variable_cost_from_qdrant_chunks(entity="portugal")
        for point in data.points:
            assert -350 <= point.value <= -150, (
                f"Value {point.value} outside EUR/ton range"
            )

    @pytest.mark.asyncio
    async def test_sufficient_data_points(self):
        """Extraction returns at least 6 data points."""
        data = await extract_variable_cost_from_qdrant_chunks(entity="portugal")
        assert len(data.points) >= 6, f"Only {len(data.points)} points extracted"
```

## References

- [Source: docs/prd/epic-6-advanced-forecasting-external-data.md#Story 6.15]
- [Source: docs/sprint-change-proposals/2025-12-12-epic-6-forecasting-accuracy-extension.md]
- [Source: docs/architecture/6-external-data-pipeline-epic-6.md#Entity Detection Architecture]
- [Source: raglite/forecasting/timeseries_extract.py - lines 381-590]

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

### File List

- `raglite/forecasting/timeseries_extract.py` - Modified (entity detection + filtering)
- `tests/unit/test_entity_detection.py` - New (unit tests)
- `tests/integration/test_variable_cost_extraction.py` - New (integration tests)
