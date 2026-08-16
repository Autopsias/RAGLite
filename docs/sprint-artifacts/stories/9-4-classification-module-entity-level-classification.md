# Story 9.4: Classification Module - Entity Level Classification

**Epic:** 9 - Data Quality at Ingestion
**Status:** done
**Estimate:** 0.5 days
**Dependencies:** Story 9.1 (Schema Migration) - DONE, Story 9.2 (Period Type Classification) - DONE, Story 9.3 (Value Type Classification) - DONE

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

---

## Prerequisites

- **Story 9.1 (Schema Migration):** DONE. Classification columns exist in PostgreSQL (period_type, value_type, entity_level).
- **Story 9.2 (Period Type Classification):** DONE. Period classifier module with regex patterns and LLM fallback.
- **Story 9.3 (Value Type Classification):** DONE. Value type classifier module with regex patterns and hierarchy-based classification.

---

## Story

As a data engineer,
I want to classify financial entities into entity levels (consolidated, company_only, segment, geographic, unknown) using regex patterns with table context integration,
so that the ingestion pipeline can store semantically-classified entity data that enables simplified forecasting queries to distinguish between group-level consolidated data and entity-specific data.

---

## Context

### Problem Statement

Financial tables contain data at different entity levels (consolidated group, individual companies, geographic segments, business segments). The forecasting module (Epic 4) requires filtering to appropriate entity levels, but currently has no reliable way to identify them. Without classification at ingestion:
- Consolidated and company-specific data are mixed in forecasting models
- Geographic segment data contaminates company-level forecasts
- GROUP EBITDA queries return inconsistent results due to entity level ambiguity

### Entity Level Classification Types

The entity_level field supports the following values:
- **CONSOLIDATED**: Group-level aggregated data (e.g., "GROUP", "Consolidated", "Total")
- **COMPANY_ONLY**: Individual company data without consolidation (e.g., "SECIL Portugal", "Company XYZ")
- **SEGMENT**: Business segment data (e.g., "Cement Division", "Ready-Mix Segment")
- **GEOGRAPHIC**: Geographic region data (e.g., "Portugal", "Iberia", "Europe")
- **UNKNOWN**: Cannot determine entity level

### Classification Hierarchy

The entity level classifier uses a priority hierarchy:
0. Empty/whitespace/unknown patterns -> UNKNOWN
1. Table title/caption (highest priority): "GROUP", "Consolidated", geographic names
2. Entity name patterns: Country names, segment keywords, company indicators
3. Row context (secondary): Entity name in first column
4. Default: UNKNOWN (conservative approach - don't assume)

### Ground Truth Dataset

`tests/fixtures/entity_level_ground_truth.json` needs to be created with 50+ test cases covering:
- Consolidated entities (10+ samples): "GROUP", "Consolidated", "Total Group", "Group Total"
- Company entities (10+ samples): "SECIL", "Company name", "[Entity] SA", "[Entity] Ltd"
- Segment entities (10+ samples): "Cement", "Ready-Mix", "Division", "Segment", "Business Unit"
- Geographic entities (10+ samples): "Portugal", "Iberia", "Europe", "Tunisia", "Brazil"
- Unknown entities (10+ samples): Empty, ambiguous, mixed

### Risk Mitigation

Per Test Design (`docs/test-design-epic-9.md`):
- **R-001 (Score: 6):** LLM classification accuracy <95% on edge cases
  - Mitigation: Ground truth validation, regex-only classification (no LLM needed for entity_level)

---

## Acceptance Criteria

### AC1: Entity Level Classification with 90%+ Accuracy

**Given** a list of entity strings and optional table context from financial tables
**When** classifying entity levels using `classify_entity_level()` or `classify_entity_levels_batch()`
**Then**:
- [ ] AC1.1: Returns correct EntityLevel for 90%+ of ground truth samples (50+ samples, need 45+)
- [ ] AC1.2: Classifies consolidated patterns correctly (GROUP, Consolidated, Total)
- [ ] AC1.3: Classifies company patterns correctly (SECIL, SA, Ltd, company names)
- [ ] AC1.4: Classifies segment patterns correctly (Division, Segment, business unit names)
- [ ] AC1.5: Classifies geographic patterns correctly (country names, region names)
- [ ] AC1.6: Defaults to UNKNOWN for ambiguous entities (conservative approach)

**BDD Scenarios:**

```gherkin
Scenario: Classify consolidated entity
  Given the entity string "GROUP"
  When classify_entity_level() is called
  Then entity_level is CONSOLIDATED
  And source is "entity_pattern"

Scenario: Classify consolidated with "Total" keyword
  Given the entity string "Total Group"
  When classify_entity_level() is called
  Then entity_level is CONSOLIDATED
  And source is "entity_pattern"

Scenario: Classify company entity with SA suffix
  Given the entity string "SECIL SA"
  When classify_entity_level() is called
  Then entity_level is COMPANY_ONLY
  And source is "entity_pattern"

Scenario: Classify geographic entity (country)
  Given the entity string "Portugal"
  When classify_entity_level() is called
  Then entity_level is GEOGRAPHIC
  And source is "entity_pattern"

Scenario: Classify segment entity
  Given the entity string "Cement Division"
  When classify_entity_level() is called
  Then entity_level is SEGMENT
  And source is "entity_pattern"

Scenario: Ground truth validation passes at 90%+
  Given the ground truth dataset with 50+ samples
  When validating classification accuracy
  Then at least 45 samples are correctly classified (90%+)
```

### AC2: Table Context Integration

**Given** an entity string with a table title/caption for context
**When** classifying entity levels with table_title parameter
**Then**:
- [ ] AC2.1: Table title "GROUP Financial Statements" classifies entities as CONSOLIDATED
- [ ] AC2.2: Table title "Portugal Operations" classifies entities as GEOGRAPHIC
- [ ] AC2.3: Table title "Cement Division Results" classifies entities as SEGMENT
- [ ] AC2.4: Entity pattern overrides conflicting table title when entity is more specific

**BDD Scenarios:**

```gherkin
Scenario: Table title provides consolidated context
  Given the entity string "Revenue"
  And table_title is "GROUP Financial Statements"
  When classify_entity_level() is called
  Then entity_level is CONSOLIDATED
  And source is "table_title"

Scenario: Entity pattern overrides table title
  Given the entity string "SECIL Portugal SA"
  And table_title is "GROUP Financial Statements"
  When classify_entity_level() is called
  Then entity_level is COMPANY_ONLY
  And source is "entity_pattern"
```

### AC3: Geographic Entity Recognition

**Given** entity strings containing geographic names
**When** classifying entity levels
**Then**:
- [ ] AC3.1: Country names recognized (Portugal, Tunisia, Brazil, Lebanon, etc.)
- [ ] AC3.2: Region names recognized (Iberia, Europe, MENA, etc.)
- [ ] AC3.3: Portuguese geographic keywords work (Pais, Regiao)
- [ ] AC3.4: Geographic takes precedence over generic names

**BDD Scenarios:**

```gherkin
Scenario: Classify country name
  Given the entity string "Tunisia"
  When classify_entity_level() is called
  Then entity_level is GEOGRAPHIC
  And source is "entity_pattern"

Scenario: Classify region name
  Given the entity string "Iberia"
  When classify_entity_level() is called
  Then entity_level is GEOGRAPHIC
  And source is "entity_pattern"

Scenario: Classify Portuguese geographic term
  Given the entity string "Pais: Portugal"
  When classify_entity_level() is called
  Then entity_level is GEOGRAPHIC
  And source is "entity_pattern"
```

### AC4: Unknown Entity Handling

**Given** entity strings that cannot be classified
**When** classifying invalid or ambiguous inputs
**Then**:
- [ ] AC4.1: Empty strings return UNKNOWN with source "empty"
- [ ] AC4.2: "N/A", "None", "null" markers return UNKNOWN with source "unknown_marker"
- [ ] AC4.3: Ambiguous patterns (numbers only, generic text) return UNKNOWN
- [ ] AC4.4: Classification never raises exceptions for malformed inputs

**BDD Scenarios:**

```gherkin
Scenario: Empty string returns unknown
  Given the entity string ""
  When classify_entity_level() is called
  Then entity_level is UNKNOWN
  And source is "empty"

Scenario: N/A marker returns unknown
  Given the entity string "N/A"
  When classify_entity_level() is called
  Then entity_level is UNKNOWN
  And source is "unknown_marker"

Scenario: Ambiguous numeric returns unknown
  Given the entity string "12345"
  When classify_entity_level() is called
  Then entity_level is UNKNOWN
  And source is "ambiguous"
```

### AC5: Batch Processing Performance

**Given** a batch of entity strings to classify
**When** using classify_entity_levels_batch()
**Then**:
- [ ] AC5.1: Returns list of ClassifiedEntityLevel matching input order
- [ ] AC5.2: Returns EntityLevelReport with accurate counts
- [ ] AC5.3: LRU cache provides <100ms for 1000 duplicate entities
- [ ] AC5.4: Handles None table_titles gracefully

**BDD Scenarios:**

```gherkin
Scenario: Batch classification with report
  Given a list of 100 entities ["GROUP", "Portugal", "SECIL", ...]
  When classify_entity_levels_batch() is called
  Then results list has 100 ClassifiedEntityLevel entries
  And report.total_records equals 100
  And report.entity_level_breakdown sums to 100

Scenario: Cached batch performance
  Given a list of 1000 identical entities ["GROUP", "GROUP", ...]
  When classify_entity_levels_batch() is called
  Then classification completes in <100ms

Scenario: Batch classification with None table_titles
  Given a list of entities ["GROUP", "Portugal"]
  And table_titles is None
  When classify_entity_levels_batch() is called
  Then classification succeeds without errors
  And results contain valid ClassifiedEntityLevel entries
```

---

## Tasks / Subtasks

### Task 1: Create EntityLevel Models (AC1) - 0.1 day

- [ ] 1.1: Add EntityLevel enum to `raglite/ingestion/classification/models.py`
- [ ] 1.2: Add ClassifiedEntityLevel dataclass with original, entity_level, source fields
- [ ] 1.3: Add EntityLevelReport dataclass with counts and breakdown
- [ ] 1.4: Update `__init__.py` exports for new models

### Task 2: Implement Entity Level Classifier (AC1, AC2, AC3, AC4) - 0.2 day

- [ ] 2.1: Create `raglite/ingestion/classification/entity_level_classifier.py`
- [ ] 2.2: Implement classify_entity_level() with regex patterns
- [ ] 2.3: Add consolidated patterns: "GROUP", "Consolidated", "Total"
- [ ] 2.4: Add company patterns: "SA", "Ltd", "Company", known company names
- [ ] 2.5: Add segment patterns: "Division", "Segment", "Unit"
- [ ] 2.6: Add geographic patterns: Country/region dictionary lookup (uses GEOGRAPHIC_ENTITIES set defined in entity_level_classifier.py)
- [ ] 2.7: Implement table_title context integration
- [ ] 2.8: Implement classify_entity_levels_batch() with LRU caching

### Task 3: Create Ground Truth Dataset (AC1) - 0.05 day

- [ ] 3.1: Create `tests/fixtures/entity_level_ground_truth.json`
- [ ] 3.2: Add 10+ consolidated samples
- [ ] 3.3: Add 10+ company samples
- [ ] 3.4: Add 10+ segment samples
- [ ] 3.5: Add 10+ geographic samples
- [ ] 3.6: Add 10+ unknown/edge case samples
- [ ] 3.7: Ensure dataset has 50+ total samples

### Task 4: Add Unit Tests (AC1, AC2, AC3, AC4) - 0.1 day

- [ ] 4.1: Create `tests/unit/ingestion/classification/test_entity_level_classifier.py`
- [ ] 4.2: Test consolidated patterns (GROUP, Consolidated, Total)
- [ ] 4.3: Test company patterns (SA, Ltd, company names)
- [ ] 4.4: Test segment patterns (Division, Segment)
- [ ] 4.5: Test geographic patterns (countries, regions)
- [ ] 4.6: Test table_title context integration (AC2)
- [ ] 4.7: Test unknown handling (AC4)
- [ ] 4.8: Ensure 80%+ test coverage for entity_level_classifier.py

### Task 5: Add Integration Tests / Ground Truth Validation (AC1, AC5) - 0.05 day

- [ ] 5.1: Create `tests/integration/test_entity_level_classification_accuracy.py`
- [ ] 5.2: Load ground truth from `tests/fixtures/entity_level_ground_truth.json`
- [ ] 5.3: Run classification on all 50+ samples
- [ ] 5.4: Assert 90%+ accuracy (45+ correct)
- [ ] 5.5: Output detailed failure report for any misclassifications
- [ ] 5.6: Mark as P0 test (critical path per test design)
- [ ] 5.7: Test batch classification correctness (AC5.1)
- [ ] 5.8: Test EntityLevelReport accuracy (AC5.2)

### Task 6: Documentation and Finalization - 0.05 day

- [ ] 6.1: Add docstrings with examples for public functions
- [ ] 6.2: Update `raglite/ingestion/classification/__init__.py` exports
- [ ] 6.3: Run full test suite: `pytest tests/ -v --tb=short`
- [ ] 6.4: Verify all acceptance criteria are met
- [ ] 6.5: Update story status to "done" in sprint-status.yaml

---

## Technical Design

### File Structure

```
raglite/ingestion/classification/
  __init__.py                     # Exports (update)
  models.py                       # EntityLevel, ClassifiedEntityLevel, etc. (update)
  period_classifier.py            # Story 9.2 (existing)
  value_type_classifier.py        # Story 9.3 (existing)
  entity_level_classifier.py      # Story 9.4 (create)

tests/unit/ingestion/classification/
  test_entity_level_classifier.py # Unit tests (create)

tests/integration/
  test_entity_level_classification_accuracy.py  # Ground truth validation (create)

tests/fixtures/
  entity_level_ground_truth.json  # 50+ samples (create)
```

### EntityLevel Enum and Models

```python
# raglite/ingestion/classification/models.py (additions)

class EntityLevel(Enum):
    """Classification of entity levels in financial data.

    Used to filter consolidated vs company vs segment data for analysis.
    """

    CONSOLIDATED = "consolidated"  # Group-level aggregated data
    COMPANY_ONLY = "company_only"  # Individual company data
    SEGMENT = "segment"  # Business segment data
    GEOGRAPHIC = "geographic"  # Geographic region data
    UNKNOWN = "unknown"  # Cannot determine level


@dataclass
class ClassifiedEntityLevel:
    """Result of entity level classification with source attribution."""

    original: str  # Original entity string
    entity_level: EntityLevel  # Classification result
    source: str  # Where classification came from: "table_title", "entity_pattern", "default", "empty", "unknown_marker", "ambiguous"


@dataclass
class EntityLevelReport:
    """Summary of entity level classification results."""

    total_records: int
    consolidated_count: int
    company_only_count: int
    segment_count: int
    geographic_count: int
    unknown_count: int

    @property
    def entity_level_breakdown(self) -> dict[str, int]:
        """Breakdown of records by entity level."""
        return {
            "consolidated": self.consolidated_count,
            "company_only": self.company_only_count,
            "segment": self.segment_count,
            "geographic": self.geographic_count,
            "unknown": self.unknown_count,
        }
```

### Entity Level Classifier Implementation

```python
# raglite/ingestion/classification/entity_level_classifier.py

import re
from functools import lru_cache

from raglite.ingestion.classification.models import (
    ClassifiedEntityLevel,
    EntityLevel,
    EntityLevelReport,
)

# Geographic entity dictionary
GEOGRAPHIC_ENTITIES: set[str] = {
    # Countries (common in financial reports)
    "portugal", "spain", "tunisia", "brazil", "lebanon", "angola",
    "mozambique", "cape verde", "france", "germany", "uk", "italy",
    # Regions
    "iberia", "europe", "mena", "latam", "americas", "asia", "africa",
    # Portuguese geographic keywords
    "pais", "regiao", "continente",
}

# Consolidated keywords
CONSOLIDATED_PATTERNS = [
    r"\bgroup\b", r"\bconsolidated\b", r"\btotal\s*group\b",
    r"\bgroup\s*total\b", r"\bholding\b", r"\bcorporate\b",
]

# Company patterns
COMPANY_PATTERNS = [
    r"\bsa\b", r"\bltd\b", r"\blda\b", r"\bs\.a\.\b", r"\bltda\b",
    r"\binc\b", r"\bcorp\b", r"\bcompany\b", r"\bempresa\b",
]

# Segment patterns
SEGMENT_PATTERNS = [
    r"\bdivision\b", r"\bsegment\b", r"\bunit\b", r"\bsector\b",
    r"\boperations\b", r"\bbusiness\b", r"\bready[- ]?mix\b",
    r"\bcement\b", r"\bconcrete\b", r"\baggregates\b",
]


def classify_entity_level(
    entity: str,
    table_title: str | None = None,
) -> ClassifiedEntityLevel:
    """Classify an entity string into its entity level.

    Classification hierarchy (checked first to last):
    0. Empty/whitespace/unknown patterns -> UNKNOWN
    1. Entity pattern (consolidated, company, segment, geographic)
    2. Table title context (secondary signal)
    3. Default: UNKNOWN (conservative approach)

    Args:
        entity: Entity string to classify
        table_title: Optional table title for context

    Returns:
        ClassifiedEntityLevel with entity level and source attribution
    """
    # Implementation follows same pattern as value_type_classifier.py
    ...
```

### Ground Truth Validation Test

```python
# tests/integration/test_entity_level_classification_accuracy.py
import json
import pytest
from raglite.ingestion.classification import classify_entity_level

GROUND_TRUTH_PATH = "tests/fixtures/entity_level_ground_truth.json"
ACCURACY_THRESHOLD = 0.90

@pytest.mark.integration
def test_entity_level_classification_accuracy():
    """Validate entity level classification against ground truth (AC1, P0)."""
    with open(GROUND_TRUTH_PATH) as f:
        ground_truth = json.load(f)

    correct = 0
    failures = []

    for sample in ground_truth:
        entity = sample["entity"]
        table_title = sample.get("table_title")
        expected_level = sample["expected_entity_level"]

        result = classify_entity_level(entity, table_title=table_title)

        if result.entity_level.value == expected_level:
            correct += 1
        else:
            failures.append({
                "entity": entity,
                "table_title": table_title,
                "expected": expected_level,
                "actual": result.entity_level.value,
                "source": result.source,
            })

    accuracy = correct / len(ground_truth)

    # Log failures for debugging
    if failures:
        for f in failures:
            print(f"FAIL: {f}")

    assert accuracy >= ACCURACY_THRESHOLD, (
        f"Accuracy {accuracy:.2%} below threshold {ACCURACY_THRESHOLD:.0%}. "
        f"Failures: {len(failures)}/{len(ground_truth)}"
    )
```

---

## Dev Notes

### Pattern Reference

The entity level classifier follows the same implementation pattern as:
- `period_classifier.py` (314 LOC) - Regex patterns with LLM fallback
- `value_type_classifier.py` (329 LOC) - Regex patterns with hierarchy

### Known Entity Names

Common entity names in the financial data:
- **Consolidated:** "GROUP", "GROUP EBITDA", "Consolidated", "Total Group"
- **Company:** "SECIL", "SECIL Portugal", "SECIL SA", company names with legal suffixes
- **Segment:** "Cement", "Ready-Mix", "Concrete", "Aggregates", business divisions
- **Geographic:** Portugal, Tunisia, Brazil, Lebanon, Iberia, Europe, MENA

### Test Design Reference

From `docs/test-design-epic-9.md`:
- **P0 Test:** Entity level classification >=90% accuracy (Integration, 1min)
- **P2 Test:** Consolidated entity level detection (Unit)

### Architecture Reference

Per `docs/architecture/6-complete-reference-implementation.md`:
- Use direct SDK calls (no wrappers)
- Structured logging with `extra={}` for context
- Pydantic models for data validation (using dataclasses, acceptable)

### Testing Guidelines Reference

Per `tests/CLAUDE.md`:
- Tests >1s should have `@pytest.mark.slow`
- Integration tests need `@pytest.mark.integration`
- Keep unit tests fast (<100ms)

---

## Testing Requirements

### Unit Tests (Fast, No External Dependencies)

| Test Case | Priority | AC Link |
|-----------|----------|---------|
| Consolidated "GROUP" detection | P1 | AC1.2 |
| Consolidated "Consolidated" detection | P1 | AC1.2 |
| Consolidated "Total Group" detection | P1 | AC1.2 |
| Company "SA" suffix detection | P1 | AC1.3 |
| Company "Ltd" suffix detection | P1 | AC1.3 |
| Segment "Division" detection | P1 | AC1.4 |
| Segment "Cement" detection | P1 | AC1.4 |
| Geographic country detection | P1 | AC1.5 |
| Geographic region detection | P1 | AC1.5 |
| Table title context | P1 | AC2.1 |
| Entity overrides table title | P1 | AC2.4 |
| Empty string handling | P1 | AC4.1 |
| N/A marker handling | P1 | AC4.2 |
| Case-insensitive matching | P1 | AC1 |

### Integration Tests

| Test Case | Priority | AC Link | Marker |
|-----------|----------|---------|--------|
| Ground truth 90%+ accuracy | P0 | AC1 | `@pytest.mark.integration` |
| Batch classification correctness | P1 | AC5.1 | `@pytest.mark.integration` |
| EntityLevelReport accuracy | P1 | AC5.2 | `@pytest.mark.integration` |

### Performance Tests

| Test Case | Priority | AC Link | Marker |
|-----------|----------|---------|--------|
| Cache performance <100ms for 1000 | P2 | AC5.3 | `@pytest.mark.slow` |

### Coverage Targets

- `entity_level_classifier.py`: >80% coverage
- All public functions have docstrings
- All acceptance criteria have at least one test

---

## References

- [Epic 9 Tracking](../../epics/epic-9-tracking.md) - Parent epic
- [Story 9.1 (Schema Migration)](../../implementation-artifacts/9-1-schema-migration-add-classification-columns.md) - Dependency (DONE)
- [Story 9.2 (Period Type Classification)](./9-2-classification-module-period-type-classification.md) - Sibling story (DONE)
- [Story 9.3 (Value Type Classification)](./9-3-classification-module-value-type-classification.md) - Sibling story (DONE)
- [Test Design Epic 9](../../test-design-epic-9.md) - Test strategy, risk assessment
- [Value Type Classifier Source](../../../raglite/ingestion/classification/value_type_classifier.py) - Pattern reference (329 LOC)
- [Database Safety Rules](../../../.claude/rules/database-safety.md) - Production protection

---

## Dev Agent Record

### Agent Model Used

(To be filled by implementing agent)

### Debug Log References

(To be filled by implementing agent)

### Completion Notes List

(To be filled by implementing agent)

### File List

**Files to Create:**
- `raglite/ingestion/classification/entity_level_classifier.py` (~250 LOC)
- `tests/unit/ingestion/classification/test_entity_level_classifier.py` (~200 LOC)
- `tests/integration/test_entity_level_classification_accuracy.py` (~60 LOC)
- `tests/fixtures/entity_level_ground_truth.json` (~100 lines)

**Files to Update:**
- `raglite/ingestion/classification/models.py` (~40 LOC additions)
- `raglite/ingestion/classification/__init__.py` (~10 LOC additions)

**Total New/Modified Code:** ~660 LOC
