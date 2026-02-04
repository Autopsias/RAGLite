# ATDD Checklist - Story 9.9: Validation - Verify Data Quality Improvement

**Story:** 9.9 - Validation - Verify Data Quality Improvement
**Phase:** RED (tests written, all failing)
**Created:** 2026-02-01
**Status:** Ready for Implementation

## Test Coverage Summary

| AC | Description | Tests | Priority | Status |
|----|-------------|-------|----------|--------|
| AC1 | Period Type Accuracy >= 95% | 6 | P0 | RED |
| AC2 | Value Type Accuracy >= 90% | 5 | P1 | RED |
| AC3 | Entity Level Accuracy >= 90% | 5 | P1 | RED |
| AC4 | 100% Coverage (No NULLs) | 6 | P0 | RED |
| AC5 | Ingestion Overhead < 20% | 4 | P2 | RED |
| AC6 | MCP Tool Compatibility | 7 | P0 | RED |
| AC7 | Test Suite Regression | 7 | P0 | RED |
| AC8 | Validation Report Generated | 9 | P1 | RED |

**Total Tests:** 49
**All Tests Status:** FAILING (expected in RED phase)

## Test Files

| File | ACs Covered | Test Count |
|------|-------------|------------|
| `test_ac1_period_type_accuracy.py` | AC1 | 6 |
| `test_ac2_value_type_accuracy.py` | AC2 | 5 |
| `test_ac3_entity_level_accuracy.py` | AC3 | 5 |
| `test_ac4_classification_coverage.py` | AC4 | 6 |
| `test_ac5_ingestion_overhead.py` | AC5 | 4 |
| `test_ac6_mcp_compatibility.py` | AC6 | 7 |
| `test_ac7_test_suite_regression.py` | AC7 | 7 |
| `test_ac8_validation_report.py` | AC8 | 9 |

## Detailed Test IDs

### AC1: Period Type Classification Accuracy >= 95% [P0]

| Test ID | Description | Priority |
|---------|-------------|----------|
| TEST-AC-9.9.1.1 | Period type overall accuracy >= 95% | P0 |
| TEST-AC-9.9.1.2 | Accuracy breakdown by period type | P0 |
| TEST-AC-9.9.1.3 | Misclassifications documented | P0 |
| TEST-AC-9.9.1.4 | Monthly actual accuracy reasonable | P1 |
| TEST-AC-9.9.1.5 | YTD actual accuracy reasonable | P1 |
| TEST-AC-9.9.1.6 | Budget period type accuracy | P1 |

### AC2: Value Type Classification Accuracy >= 90% [P1]

| Test ID | Description | Priority |
|---------|-------------|----------|
| TEST-AC-9.9.2.1 | Value type overall accuracy >= 90% | P1 |
| TEST-AC-9.9.2.2 | Accuracy breakdown by value type | P1 |
| TEST-AC-9.9.2.3 | Misclassifications logged | P1 |
| TEST-AC-9.9.2.4 | Actual value type accuracy | P2 |
| TEST-AC-9.9.2.5 | Variance value type accuracy | P2 |

### AC3: Entity Level Classification Accuracy >= 90% [P1]

| Test ID | Description | Priority |
|---------|-------------|----------|
| TEST-AC-9.9.3.1 | Entity level overall accuracy >= 90% | P1 |
| TEST-AC-9.9.3.2 | Accuracy breakdown by entity level | P1 |
| TEST-AC-9.9.3.3 | Misclassifications logged | P1 |
| TEST-AC-9.9.3.4 | Consolidated entity accuracy | P2 |
| TEST-AC-9.9.3.5 | Segment entity accuracy | P2 |

### AC4: 100% Classification Coverage [P0]

| Test ID | Description | Priority |
|---------|-------------|----------|
| TEST-AC-9.9.4.1 | Zero NULL period_type rows | P0 |
| TEST-AC-9.9.4.2 | Zero NULL value_type rows | P0 |
| TEST-AC-9.9.4.3 | Zero NULL entity_level rows | P0 |
| TEST-AC-9.9.4.4 | Coverage report shows 100% | P0 |
| TEST-AC-9.9.4.5 | Minimum row count met (78759+) | P1 |
| TEST-AC-9.9.4.6 | Classification distribution reasonable | P2 |

### AC5: Ingestion Time Overhead < 20% [P2]

| Test ID | Description | Priority |
|---------|-------------|----------|
| TEST-AC-9.9.5.1 | Average overhead < 20% | P2 |
| TEST-AC-9.9.5.2 | Per-document breakdown provided | P2 |
| TEST-AC-9.9.5.3 | No document exceeds 50% overhead | P2 |
| TEST-AC-9.9.5.4 | Epic 9 performance validation passes | P2 |

### AC6: MCP Tool Backward Compatibility [P0]

| Test ID | Description | Priority |
|---------|-------------|----------|
| TEST-AC-9.9.6.1 | ingest_financial_document works | P0 |
| TEST-AC-9.9.6.2 | get_financial_forecast works | P0 |
| TEST-AC-9.9.6.3 | query_financial_documents works | P0 |
| TEST-AC-9.9.6.4 | get_health_status works | P0 |
| TEST-AC-9.9.6.5 | MCP unit tests pass | P0 |
| TEST-AC-9.9.6.6 | No new required parameters | P1 |
| TEST-AC-9.9.6.7 | Response schema unchanged | P1 |

### AC7: All Existing Tests Pass [P0]

| Test ID | Description | Priority |
|---------|-------------|----------|
| TEST-AC-9.9.7.1 | Unit tests pass | P0 |
| TEST-AC-9.9.7.2 | Integration tests pass | P0 |
| TEST-AC-9.9.7.3 | E2E tests pass | P0 |
| TEST-AC-9.9.7.4 | Stories 9.1-9.8 acceptance tests pass | P0 |
| TEST-AC-9.9.7.5 | No test failures introduced | P0 |
| TEST-AC-9.9.7.6 | Test count maintained | P1 |
| TEST-AC-9.9.7.7 | Coverage maintained at 80%+ | P1 |

### AC8: Validation Report Generated [P1]

| Test ID | Description | Priority |
|---------|-------------|----------|
| TEST-AC-9.9.8.1 | Report file created | P1 |
| TEST-AC-9.9.8.2 | Executive summary with pass/fail | P1 |
| TEST-AC-9.9.8.3 | Accuracy metrics included | P1 |
| TEST-AC-9.9.8.4 | Coverage metrics included | P1 |
| TEST-AC-9.9.8.5 | Performance metrics included | P1 |
| TEST-AC-9.9.8.6 | Test results summary included | P1 |
| TEST-AC-9.9.8.7 | Misclassification log included | P2 |
| TEST-AC-9.9.8.8 | Recommendations included | P2 |
| TEST-AC-9.9.8.9 | Report suitable for stakeholders | P2 |

## Ground Truth Requirements

- **Location:** `tests/fixtures/classification_ground_truth.json`
- **Minimum entries:** 50+
- **Coverage:** All classification types (period, value, entity)
- **Diversity:** Multiple documents represented

## Validation Scripts

- **Accuracy:** `scripts/validate-classification-accuracy.py`
- **Coverage:** `scripts/validate-classification-coverage.py`

## Success Criteria Mapping

| Epic 9 Success Criteria | Story 9.9 AC |
|-------------------------|--------------|
| Period type >= 95% accuracy | AC1 |
| Value type >= 90% accuracy | AC2 |
| Entity level >= 90% accuracy | AC3 |
| 100% coverage (no NULLs) | AC4 |
| Ingestion overhead < 20% | AC5 |
| Backward compatibility | AC6, AC7 |
| Documented validation | AC8 |

## Next Steps (Implementation Phase)

1. Verify ground truth dataset has 50+ entries (Task 1)
2. Execute accuracy validation scripts (Task 2)
3. Execute coverage validation scripts (Task 3)
4. Validate ingestion performance (Task 4)
5. Run MCP compatibility tests (Task 5)
6. Run full test suite regression (Task 6)
7. Generate validation report (Task 7)
8. Update Epic 9 tracking (Task 8)

## Notes

- This is the final story in Epic 9
- All tests are currently in RED state (failing with explicit fail message)
- Implementation should make tests pass by executing validation scripts and generating report
- No new code implementation required - primarily validation and documentation
