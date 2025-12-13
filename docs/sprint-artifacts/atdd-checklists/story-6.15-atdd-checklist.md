# ATDD Checklist: Story 6.15 - Entity-Specific Variable Cost Extraction

**Story:** 6.15 - Entity-Specific Variable Cost Extraction
**Status:** RED (Tests Created - Failing)
**Date Created:** 2025-12-12
**TDD Phase:** RED (Acceptance tests written before implementation)

## Story Overview

**Problem Statement:**
Variable Cost MAPE is at 41.43% (target <8%), making it the worst-performing metric in the forecasting system. Root cause analysis identified:
1. Multi-Entity Data Mixing: Variable Cost data mixes Portugal + Tunisia + Brazil values
2. High Coefficient of Variation: 33% CV due to currency/entity mixing (target: <15%)
3. No Entity Detection: Current extraction does not filter by geographic entity
4. Unit Inconsistency: Values in EUR/ton, BRL/ton, TND/ton mixed without normalization

**Solution:**
Implement entity detection to filter Portugal-only data and normalize to EUR/ton.

## Acceptance Criteria Mapping

| AC | Description | Test File | Test Class/Method | Status |
|----|-------------|-----------|-------------------|--------|
| AC1 | Entity detection identifies Portugal/Tunisia/Brazil with >95% accuracy | `tests/unit/test_entity_detection.py` | `TestDetectEntityFunction`, `TestEntityPatternsConstant`, `TestEntityDetectionAccuracy` | RED |
| AC2 | Portugal-only extraction produces <15% CV (vs 33% current) | `tests/integration/test_variable_cost_extraction.py` | `TestVariableCostCoefficientOfVariation`, `TestSufficientDataPoints` | RED |
| AC3 | Values normalized to EUR/ton (range -150 to -350) | `tests/integration/test_variable_cost_extraction.py` | `TestEurTonRangeValidation` | RED |
| AC4 | Variable Cost MAPE improves to <25% (from 41%) | `tests/integration/test_variable_cost_extraction.py` | `TestVariableCostMAPEImprovement` | RED |
| AC5 | No regression in other metric extraction | `tests/integration/test_variable_cost_extraction.py` | `TestNoRegressionOtherMetrics` | RED |

## Test Files Created

### Unit Tests: `tests/unit/test_entity_detection.py`

**Total Tests:** 18

| Test ID | Test Method | AC | Description |
|---------|-------------|----|-----------
| test_ac1_detect_portugal_explicit_keyword | TestDetectEntityFunction | AC1 | Detect Portugal from explicit keyword |
| test_ac1_detect_portugal_from_eur_ton_currency | TestDetectEntityFunction | AC1 | Detect Portugal from EUR/ton |
| test_ac1_detect_portugal_from_portuguese_language | TestDetectEntityFunction | AC1 | Detect Portugal from Custos Variáveis |
| test_ac1_detect_portugal_pt_abbreviation | TestDetectEntityFunction | AC1 | Detect Portugal from PT |
| test_ac1_detect_tunisia_explicit_keyword | TestDetectEntityFunction | AC1 | Detect Tunisia from keyword |
| test_ac1_detect_tunisia_from_tnd_currency | TestDetectEntityFunction | AC1 | Detect Tunisia from TND/ton |
| test_ac1_detect_tunisia_tn_abbreviation | TestDetectEntityFunction | AC1 | Detect Tunisia from TN |
| test_ac1_detect_brazil_explicit_keyword | TestDetectEntityFunction | AC1 | Detect Brazil from keyword |
| test_ac1_detect_brazil_from_brl_currency | TestDetectEntityFunction | AC1 | Detect Brazil from BRL/ton |
| test_ac1_detect_brazil_brasil_variant | TestDetectEntityFunction | AC1 | Detect Brazil from Brasil |
| test_ac1_detect_brazil_br_abbreviation | TestDetectEntityFunction | AC1 | Detect Brazil from BR |
| test_ac1_unknown_entity_returns_none | TestDetectEntityFunction | AC1 | Unknown returns None |
| test_ac1_case_insensitive_detection | TestDetectEntityFunction | AC1 | Case insensitive |
| test_entity_patterns_exists | TestEntityPatternsConstant | AC1 | ENTITY_PATTERNS exists |
| test_entity_patterns_has_portugal | TestEntityPatternsConstant | AC1 | Portugal patterns |
| test_entity_patterns_has_tunisia | TestEntityPatternsConstant | AC1 | Tunisia patterns |
| test_entity_patterns_has_brazil | TestEntityPatternsConstant | AC1 | Brazil patterns |
| test_ac1_entity_detection_accuracy_above_95_percent | TestEntityDetectionAccuracy | AC1 | >95% accuracy |

### Integration Tests: `tests/integration/test_variable_cost_extraction.py`

**Total Tests:** 15

| Test ID | Test Method | AC | Description |
|---------|-------------|----|-----------
| test_ac2_portugal_only_cv_under_15_percent | TestVariableCostCoefficientOfVariation | AC2 | CV <15% |
| test_ac2_entity_filter_reduces_variability | TestVariableCostCoefficientOfVariation | AC2 | Filter reduces CV |
| test_ac3_all_values_in_eur_ton_range | TestEurTonRangeValidation | AC3 | Values in -350 to -150 |
| test_ac3_values_are_negative_costs | TestEurTonRangeValidation | AC3 | Negative costs |
| test_ac3_typical_value_around_280_eur_ton | TestEurTonRangeValidation | AC3 | Mean ~-280 EUR/ton |
| test_ac2_minimum_six_data_points | TestSufficientDataPoints | AC2 | >=6 data points |
| test_ac2_data_points_have_valid_dates | TestSufficientDataPoints | AC2 | Valid dates |
| test_ac2_data_sorted_chronologically | TestSufficientDataPoints | AC2 | Chronological sort |
| test_ac4_entity_param_accepted_by_extraction | TestVariableCostMAPEImprovement | AC4 | Entity param works |
| test_ac4_filtered_data_more_consistent | TestVariableCostMAPEImprovement | AC4 | Filtered = consistent |
| test_ac5_revenue_extraction_unaffected | TestNoRegressionOtherMetrics | AC5 | Revenue OK |
| test_ac5_ebitda_extraction_unaffected | TestNoRegressionOtherMetrics | AC5 | EBITDA OK |
| test_ac5_sales_volume_extraction_unaffected | TestNoRegressionOtherMetrics | AC5 | Sales volume OK |
| test_ac5_timeseries_data_structure_unchanged | TestNoRegressionOtherMetrics | AC5 | Model unchanged |
| test_entity_portugal_filters_correctly | TestEntityParameterIntegration | AC2/AC3 | Filter works |
| test_default_entity_is_portugal | TestEntityParameterIntegration | AC2 | Default = portugal |

## Implementation Requirements (from tests)

The tests expect the following to be implemented in `raglite/forecasting/timeseries_extract.py`:

### 1. ENTITY_PATTERNS Constant
```python
ENTITY_PATTERNS = {
    "portugal": ["Portugal", "PT", "Custos Variáveis", "EUR/ton", "EUR/m³"],
    "tunisia": ["Tunisia", "TN", "TND", "Tunisie", "TND/ton"],
    "brazil": ["Brazil", "BR", "BRL", "Brasil", "BRL/ton"],
}
```

### 2. detect_entity() Function
```python
def detect_entity(text: str) -> str | None:
    """Detect geographic entity from chunk text.

    Story 6.15: Identifies Portugal/Tunisia/Brazil from context patterns.

    Args:
        text: Chunk text to analyze

    Returns:
        Canonical entity name ('portugal', 'tunisia', 'brazil') or None if undetectable
    """
    # Implementation to match patterns case-insensitively
```

### 3. Update extract_variable_cost_from_qdrant_chunks()
```python
async def extract_variable_cost_from_qdrant_chunks(
    entity: str = "portugal",  # NEW: Entity filter parameter
    min_points: int = 6,
) -> "TimeSeriesData | None":
    """Extract Variable Cost with entity filtering.

    Story 6.15: Filter chunks by entity before value extraction.
    """
    # Call detect_entity() on each chunk
    # Only process chunks matching requested entity
    # Validate EUR/ton range for Portugal
```

## Running Tests

### Run Unit Tests Only (fast, no external dependencies)
```bash
uv run pytest tests/unit/test_entity_detection.py -v
```

### Run Integration Tests (requires Qdrant/PostgreSQL)
```bash
uv run pytest tests/integration/test_variable_cost_extraction.py -v -m integration
```

### Run All Story 6.15 Tests
```bash
uv run pytest tests/unit/test_entity_detection.py tests/integration/test_variable_cost_extraction.py -v
```

## Expected Test Results

### RED Phase (Current State)
All tests should FAIL because:
1. `detect_entity` function does not exist
2. `ENTITY_PATTERNS` constant does not exist
3. `extract_variable_cost_from_qdrant_chunks` does not support entity filtering

### GREEN Phase (After Implementation)
All 33 tests should PASS after implementing:
1. ENTITY_PATTERNS constant with Portugal/Tunisia/Brazil patterns
2. detect_entity() function with case-insensitive pattern matching
3. Entity parameter and filtering in extract_variable_cost_from_qdrant_chunks()

## Verification Command
```bash
# After implementation, run to verify GREEN status:
uv run pytest tests/unit/test_entity_detection.py tests/integration/test_variable_cost_extraction.py -v --tb=short
```

## Notes

- Tests follow Given-When-Then structure in docstrings
- Test IDs map to acceptance criteria (e.g., test_ac1_*, test_ac2_*)
- Integration tests are marked with `@pytest.mark.integration`
- Async tests use `@pytest.mark.asyncio`
- Tests are designed to fail initially (RED phase of TDD)
