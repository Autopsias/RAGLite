# ATDD Checklist - Story 9.4: Entity Level Classification

**Story:** 9.4 - Classification Module - Entity Level Classification
**Phase:** TDD RED (Tests created, all failing)
**Status:** RED (43/43 tests failing - expected)
**Generated:** 2026-01-31

---

## Test Coverage Summary

| AC | Description | Tests | Priority | Status |
|----|-------------|-------|----------|--------|
| AC1 | Entity Level Classification with 90%+ Accuracy | 11 | P0/P1 | RED |
| AC2 | Table Context Integration | 8 | P0/P1 | RED |
| AC3 | Geographic Entity Recognition | 8 | P1 | RED |
| AC4 | Unknown Entity Handling | 8 | P0/P1 | RED |
| AC5 | Batch Processing Performance | 8 | P0/P1/P2 | RED |

**Total Tests:** 43
**Total Failing:** 43 (expected - TDD RED phase)

---

## AC1: Entity Level Classification with 90%+ Accuracy

### Test File: `tests/acceptance/story_9_4/test_ac1_entity_level_accuracy.py`

| Test ID | Test Name | Priority | BDD Scenario | Status |
|---------|-----------|----------|--------------|--------|
| TEST-AC-9.4.1.1 | test_ac_1_1_1_achieves_90_percent_accuracy | P0 | Ground truth validation passes at 90%+ | RED |
| TEST-AC-9.4.1.2 | test_ac_1_1_2_consolidated_group_pattern | P1 | Classify consolidated entity "GROUP" | RED |
| TEST-AC-9.4.1.3 | test_ac_1_1_3_consolidated_total_group_pattern | P1 | Classify consolidated with "Total" keyword | RED |
| TEST-AC-9.4.1.4 | test_ac_1_1_4_consolidated_keyword_variations | P1 | Classify consolidated variations | RED |
| TEST-AC-9.4.1.5 | test_ac_1_1_5_company_sa_suffix_pattern | P1 | Classify company entity with SA suffix | RED |
| TEST-AC-9.4.1.6 | test_ac_1_1_6_company_ltd_suffix_pattern | P1 | Classify company with Ltd suffix | RED |
| TEST-AC-9.4.1.7 | test_ac_1_1_7_company_patterns_variations | P1 | Classify various company patterns | RED |
| TEST-AC-9.4.1.8 | test_ac_1_1_8_segment_division_pattern | P1 | Classify segment entity | RED |
| TEST-AC-9.4.1.9 | test_ac_1_1_9_segment_patterns_variations | P1 | Classify various segment patterns | RED |
| TEST-AC-9.4.1.10 | test_ac_1_1_10_geographic_country_pattern | P1 | Classify geographic entity (country) | RED |
| TEST-AC-9.4.1.11 | test_ac_1_1_11_case_insensitive_matching | P1 | Case-insensitive pattern matching | RED |

---

## AC2: Table Context Integration

### Test File: `tests/acceptance/story_9_4/test_ac2_table_context_integration.py`

| Test ID | Test Name | Priority | BDD Scenario | Status |
|---------|-----------|----------|--------------|--------|
| TEST-AC-9.4.2.1 | test_ac_2_2_1_table_title_group_financial_statements | P0 | Table title provides consolidated context | RED |
| TEST-AC-9.4.2.2 | test_ac_2_2_2_table_title_portugal_operations | P1 | Table title provides geographic context | RED |
| TEST-AC-9.4.2.3 | test_ac_2_2_3_table_title_cement_division_results | P1 | Table title provides segment context | RED |
| TEST-AC-9.4.2.4 | test_ac_2_2_4_entity_pattern_overrides_table_title | P0 | Entity pattern overrides table title | RED |
| TEST-AC-9.4.2.5 | test_ac_2_2_5_table_title_consolidated_variations | P1 | Various consolidated table titles | RED |
| TEST-AC-9.4.2.6 | test_ac_2_2_6_table_title_geographic_variations | P1 | Various geographic table titles | RED |
| TEST-AC-9.4.2.7 | test_ac_2_2_7_empty_table_title_uses_entity_only | P1 | Empty table title falls back to entity | RED |
| TEST-AC-9.4.2.8 | test_ac_2_2_8_specific_entity_overrides_generic_table | P1 | Specific entity overrides generic table | RED |

---

## AC3: Geographic Entity Recognition

### Test File: `tests/acceptance/story_9_4/test_ac3_geographic_recognition.py`

| Test ID | Test Name | Priority | BDD Scenario | Status |
|---------|-----------|----------|--------------|--------|
| TEST-AC-9.4.3.1 | test_ac_3_3_1_country_name_tunisia | P1 | Classify country name Tunisia | RED |
| TEST-AC-9.4.3.2 | test_ac_3_3_2_region_name_iberia | P1 | Classify region name Iberia | RED |
| TEST-AC-9.4.3.3 | test_ac_3_3_3_portuguese_geographic_term | P1 | Classify Portuguese geographic term | RED |
| TEST-AC-9.4.3.4 | test_ac_3_3_4_common_countries_in_financial_data | P1 | Common countries in financial data | RED |
| TEST-AC-9.4.3.5 | test_ac_3_3_5_common_regions_in_financial_data | P1 | Common regions in financial data | RED |
| TEST-AC-9.4.3.6 | test_ac_3_3_6_portuguese_geographic_keywords | P1 | Portuguese geographic keywords work | RED |
| TEST-AC-9.4.3.7 | test_ac_3_3_7_geographic_precedence_over_generic | P1 | Geographic takes precedence over generic | RED |
| TEST-AC-9.4.3.8 | test_ac_3_3_8_case_insensitive_geographic | P1 | Case-insensitive geographic matching | RED |

---

## AC4: Unknown Entity Handling

### Test File: `tests/acceptance/story_9_4/test_ac4_unknown_entity_handling.py`

| Test ID | Test Name | Priority | BDD Scenario | Status |
|---------|-----------|----------|--------------|--------|
| TEST-AC-9.4.4.1 | test_ac_4_4_1_empty_string_returns_unknown | P0 | Empty string returns unknown | RED |
| TEST-AC-9.4.4.2 | test_ac_4_4_2_whitespace_only_returns_unknown | P0 | Whitespace-only returns unknown | RED |
| TEST-AC-9.4.4.3 | test_ac_4_4_3_na_marker_returns_unknown | P0 | N/A marker returns unknown | RED |
| TEST-AC-9.4.4.4 | test_ac_4_4_4_various_na_markers_return_unknown | P0 | Various N/A markers return unknown | RED |
| TEST-AC-9.4.4.5 | test_ac_4_4_5_ambiguous_numeric_returns_unknown | P1 | Ambiguous numeric returns unknown | RED |
| TEST-AC-9.4.4.6 | test_ac_4_4_6_ambiguous_patterns_return_unknown | P1 | Ambiguous patterns return unknown | RED |
| TEST-AC-9.4.4.7 | test_ac_4_4_7_no_exceptions_for_malformed_inputs | P0 | No exceptions for malformed inputs | RED |
| TEST-AC-9.4.4.8 | test_ac_4_4_8_conservative_approach_defaults_unknown | P1 | Conservative approach defaults unknown | RED |

---

## AC5: Batch Processing Performance

### Test File: `tests/acceptance/story_9_4/test_ac5_batch_processing.py`

| Test ID | Test Name | Priority | BDD Scenario | Status |
|---------|-----------|----------|--------------|--------|
| TEST-AC-9.4.5.1 | test_ac_5_5_1_batch_returns_correct_order | P0 | Batch classification with report | RED |
| TEST-AC-9.4.5.2 | test_ac_5_5_2_report_has_accurate_counts | P0 | Report has accurate counts | RED |
| TEST-AC-9.4.5.3 | test_ac_5_5_3_cache_performance_under_100ms | P2 | Cached batch performance <100ms | RED |
| TEST-AC-9.4.5.4 | test_ac_5_5_4_handles_none_table_titles | P1 | Handles None table_titles gracefully | RED |
| TEST-AC-9.4.5.5 | test_ac_5_5_5_batch_with_table_titles_list | P1 | Batch supports table_titles list | RED |
| TEST-AC-9.4.5.6 | test_ac_5_5_6_batch_validates_list_lengths | P1 | Batch validates mismatched list lengths | RED |
| TEST-AC-9.4.5.7 | test_ac_5_5_7_batch_preserves_original_values | P1 | Batch preserves original entity values | RED |
| TEST-AC-9.4.5.8 | test_ac_5_5_8_large_batch_performance | P2 | Large batch (1000 entities) <500ms | RED |

---

## Ground Truth Dataset

**File:** `tests/fixtures/entity_level_ground_truth.json`
**Samples:** 55 total

| Category | Count | Examples |
|----------|-------|----------|
| Consolidated | 10 | GROUP, Consolidated, Total Group, Holding, Corporate |
| Company Only | 10 | SECIL SA, Company Ltd, Empresa Lda, Corporation Inc |
| Segment | 10 | Cement Division, Ready-Mix Segment, Concrete Unit |
| Geographic | 12 | Portugal, Tunisia, Iberia, Europe, MENA, LATAM |
| Unknown | 10 | "", N/A, None, null, 12345, whitespace |
| Table Context | 3 | Generic entity with table title context |

---

## Modules to be Implemented (Phase 4)

### New Files

1. `raglite/ingestion/classification/entity_level_classifier.py` (~250 LOC)
   - `classify_entity_level(entity, table_title=None) -> ClassifiedEntityLevel`
   - `classify_entity_levels_batch(entities, table_titles=None) -> tuple[list, EntityLevelReport]`
   - Regex patterns for CONSOLIDATED, COMPANY_ONLY, SEGMENT, GEOGRAPHIC
   - LRU caching for batch performance

### Model Additions to `raglite/ingestion/classification/models.py`

1. `EntityLevel` enum (CONSOLIDATED, COMPANY_ONLY, SEGMENT, GEOGRAPHIC, UNKNOWN)
2. `ClassifiedEntityLevel` dataclass (original, entity_level, source)
3. `EntityLevelReport` dataclass (total_records, counts per level)

### Export Updates to `raglite/ingestion/classification/__init__.py`

- `EntityLevel`
- `ClassifiedEntityLevel`
- `EntityLevelReport`
- `classify_entity_level`
- `classify_entity_levels_batch`

---

## Validation Command

```bash
# Run ATDD tests for Story 9-4 (should all FAIL in RED phase)
uv run pytest tests/acceptance/story_9_4/ -m "atdd" -v --tb=short

# Expected: 43 tests failing with ImportError
# After implementation (GREEN phase): 43 tests passing
```

---

## Next Steps

1. **Phase 4 (GREEN):** Implement `entity_level_classifier.py` to make all tests pass
2. **Phase 5 (REFACTOR):** Optimize code while keeping tests green
3. **Update this checklist:** Change status from RED to GREEN for each passing test
