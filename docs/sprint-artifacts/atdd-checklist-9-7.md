# ATDD Checklist - Story 9.7: Re-ingestion - Process Existing PDFs with New Pipeline

**Story:** 9.7 - Re-ingestion with Classification Pipeline
**Epic:** Epic 9 - Data Quality at Ingestion
**Status:** RED (Tests Created, Implementation Pending)
**Created:** 2026-02-01

## Overview

This checklist tracks acceptance tests for Story 9.7, which implements the re-ingestion of all 33 production PDFs using the classification-enabled pipeline from Stories 9.5 and 9.6.

## Test Summary

| AC | Description | Tests | Status |
|----|-------------|-------|--------|
| AC1 | Re-ingestion Script Updates | 7 | RED |
| AC2 | Production Data Cleanup | 10 | RED |
| AC3 | Classification Coverage Validation | 10 | RED |
| AC4 | Classification Accuracy Validation | 12 | RED |
| AC5 | Re-ingestion Performance Metrics | 9 | RED |
| AC6 | Error Handling and Recovery | 10 | RED |
| **Total** | | **58** | **RED** |

## Test File Locations

```
tests/acceptance/story_9_7/
    __init__.py
    conftest.py                           # Shared fixtures
    test_ac1_reingestion_script.py        # 7 tests
    test_ac2_production_cleanup.py        # 10 tests
    test_ac3_coverage_validation.py       # 10 tests
    test_ac4_accuracy_validation.py       # 12 tests
    test_ac5_performance_metrics.py       # 9 tests
    test_ac6_error_handling.py            # 10 tests
```

## AC1: Re-ingestion Script Updates

| Test ID | Test | Priority | Status |
|---------|------|----------|--------|
| TEST-AC-9.7.1.1 | Reingest script exists | P0 | PASS |
| TEST-AC-9.7.1.2 | Script includes all 33 documents | P0 | FAIL |
| TEST-AC-9.7.1.3 | Script supports --parallel N flag | P0 | FAIL |
| TEST-AC-9.7.1.4 | Script reports classification summary | P0 | FAIL |
| TEST-AC-9.7.1.5 | Script uses classification-enabled pipeline | P0 | PASS |
| TEST-AC-9.7.1.6 | Script supports --dry-run option | P1 | FAIL |
| TEST-AC-9.7.1.7 | Script has progress tracking | P1 | PASS |

**Blocking Issues:**
- `scripts/reingest-all-documents.py` only has 10 documents (needs 33)
- No argparse for --parallel and --dry-run flags
- No classification summary reporting

## AC2: Production Data Cleanup

| Test ID | Test | Priority | Status |
|---------|------|----------|--------|
| TEST-AC-9.7.2.1 | Cleanup script exists | P0 | FAIL |
| TEST-AC-9.7.2.2 | Script supports --dry-run | P0 | FAIL |
| TEST-AC-9.7.2.3 | Script requires --force-production | P0 | FAIL |
| TEST-AC-9.7.2.4 | Script uses SafetyGuard | P0 | FAIL |
| TEST-AC-9.7.2.5 | Script verifies backup before cleanup | P0 | FAIL |
| TEST-AC-9.7.2.6 | Script requires explicit confirmation | P0 | FAIL |
| TEST-AC-9.7.2.7 | Dry-run prevents destructive operations | P0 | FAIL |
| TEST-AC-9.7.2.8 | Cleanup truncates financial_tables | P1 | FAIL |
| TEST-AC-9.7.2.9 | Cleanup recreates Qdrant collection | P1 | FAIL |
| TEST-AC-9.7.2.10 | Cleanup truncates financial_chunks | P1 | FAIL |

**Blocking Issues:**
- `scripts/prepare-reingestion.py` does not exist

## AC3: Classification Coverage Validation

| Test ID | Test | Priority | Status |
|---------|------|----------|--------|
| TEST-AC-9.7.3.1 | Coverage validation script exists | P0 | FAIL |
| TEST-AC-9.7.3.2 | Script checks period_type NULLs | P0 | FAIL |
| TEST-AC-9.7.3.3 | Script checks value_type NULLs | P0 | FAIL |
| TEST-AC-9.7.3.4 | Script checks entity_level NULLs | P0 | FAIL |
| TEST-AC-9.7.3.5 | Script generates classification breakdown | P0 | FAIL |
| TEST-AC-9.7.3.6 | Script saves report to file | P0 | FAIL |
| TEST-AC-9.7.3.7 | Script returns exit code (0/1) | P0 | FAIL |
| TEST-AC-9.7.3.8 | Coverage report shows 100% period_type | P0 | PASS (fixture) |
| TEST-AC-9.7.3.9 | Coverage report shows 100% value_type | P0 | PASS (fixture) |
| TEST-AC-9.7.3.10 | Coverage report shows 100% entity_level | P0 | PASS (fixture) |

**Blocking Issues:**
- `scripts/validate-classification-coverage.py` does not exist

## AC4: Classification Accuracy Validation

| Test ID | Test | Priority | Status |
|---------|------|----------|--------|
| TEST-AC-9.7.4.1 | Ground truth JSON file exists | P0 | FAIL |
| TEST-AC-9.7.4.2 | Ground truth has 50+ entries | P0 | FAIL |
| TEST-AC-9.7.4.3 | Ground truth has required fields | P0 | FAIL |
| TEST-AC-9.7.4.4 | Accuracy validation script exists | P0 | FAIL |
| TEST-AC-9.7.4.5 | Script loads ground truth | P0 | FAIL |
| TEST-AC-9.7.4.6 | Script queries database | P0 | FAIL |
| TEST-AC-9.7.4.7 | Script calculates period_type accuracy | P0 | FAIL |
| TEST-AC-9.7.4.8 | Script validates 95% period_type target | P0 | FAIL |
| TEST-AC-9.7.4.9 | Script validates 90% value_type target | P0 | FAIL |
| TEST-AC-9.7.4.10 | Script logs misclassifications | P0 | FAIL |
| TEST-AC-9.7.4.11 | Script generates accuracy report | P0 | FAIL |
| TEST-AC-9.7.4.12 | Accuracy report has expected structure | P0 | PASS (fixture) |

**Blocking Issues:**
- `tests/fixtures/classification_ground_truth.json` does not exist
- `scripts/validate-classification-accuracy.py` does not exist

## AC5: Re-ingestion Performance Metrics

| Test ID | Test | Priority | Status |
|---------|------|----------|--------|
| TEST-AC-9.7.5.1 | Script tracks total duration | P0 | FAIL |
| TEST-AC-9.7.5.2 | Script tracks per-document timing | P0 | FAIL |
| TEST-AC-9.7.5.3 | Script calculates rows/second | P0 | FAIL |
| TEST-AC-9.7.5.4 | Script logs document metrics | P0 | FAIL |
| TEST-AC-9.7.5.5 | Script saves metrics report | P0 | FAIL |
| TEST-AC-9.7.5.6 | Classification overhead <20% | P0 | FAIL |
| TEST-AC-9.7.5.7 | Performance report has expected structure | P0 | PASS (fixture) |
| TEST-AC-9.7.5.8 | Report has per-document metrics | P0 | PASS (fixture) |
| TEST-AC-9.7.5.9 | Overhead below 20% in report | P0 | PASS (fixture) |

**Blocking Issues:**
- `scripts/reingest-all-documents.py` lacks detailed timing/metrics tracking
- No metrics report output

## AC6: Error Handling and Recovery

| Test ID | Test | Priority | Status |
|---------|------|----------|--------|
| TEST-AC-9.7.6.1 | Script catches document errors | P0 | PASS |
| TEST-AC-9.7.6.2 | Script continues after failure | P0 | PASS |
| TEST-AC-9.7.6.3 | Script tracks failed documents | P0 | PASS |
| TEST-AC-9.7.6.4 | Script logs error context | P0 | PASS |
| TEST-AC-9.7.6.5 | Script supports --retry-failed | P0 | FAIL |
| TEST-AC-9.7.6.6 | Script reports success/failure summary | P0 | PASS |
| TEST-AC-9.7.6.7 | Script documents rollback procedure | P1 | FAIL |
| TEST-AC-9.7.6.8 | Script returns partial success code | P1 | PASS |
| TEST-AC-9.7.6.9 | Error handling preserves partial data | P1 | PASS |
| TEST-AC-9.7.6.10 | Failed documents saved to log file | P2 | PASS |

**Blocking Issues:**
- No --retry-failed flag support
- No rollback documentation in script

## Implementation Requirements

### Scripts to Create

1. **scripts/prepare-reingestion.py** (AC2)
   - SafetyGuard integration
   - --dry-run mode
   - --force-production flag
   - Backup verification
   - User confirmation (type DELETE)
   - Qdrant collection recreation
   - PostgreSQL TRUNCATE

2. **scripts/validate-classification-coverage.py** (AC3)
   - Query PostgreSQL for NULL counts
   - Generate breakdown by classification type
   - Output markdown report
   - Exit code 0/1

3. **scripts/validate-classification-accuracy.py** (AC4)
   - Load ground truth JSON
   - Query database for actual values
   - Calculate accuracy percentages
   - Log misclassifications
   - Output markdown report

### Files to Create

1. **tests/fixtures/classification_ground_truth.json** (AC4)
   - 50+ manually verified entries
   - Required fields: document, page, table_index, row_index, expected_*

### Files to Update

1. **scripts/reingest-all-documents.py** (AC1, AC5, AC6)
   - Expand DOCUMENTS list to 33 PDFs
   - Add argparse for --parallel, --dry-run, --retry-failed
   - Add classification summary output
   - Add performance timing/metrics
   - Add rollback documentation

## Running Tests

```bash
# Run all Story 9.7 tests (expects failures in RED state)
uv run pytest tests/acceptance/story_9_7/ -v --tb=short -m "not slow"

# Run specific AC tests
uv run pytest tests/acceptance/story_9_7/test_ac1_reingestion_script.py -v
uv run pytest tests/acceptance/story_9_7/test_ac2_production_cleanup.py -v
uv run pytest tests/acceptance/story_9_7/test_ac3_coverage_validation.py -v
uv run pytest tests/acceptance/story_9_7/test_ac4_accuracy_validation.py -v
uv run pytest tests/acceptance/story_9_7/test_ac5_performance_metrics.py -v
uv run pytest tests/acceptance/story_9_7/test_ac6_error_handling.py -v
```

## TDD Phase Transition

### RED -> GREEN Checklist

- [ ] Create `scripts/prepare-reingestion.py`
- [ ] Create `scripts/validate-classification-coverage.py`
- [ ] Create `scripts/validate-classification-accuracy.py`
- [ ] Create `tests/fixtures/classification_ground_truth.json`
- [ ] Update `scripts/reingest-all-documents.py` with 33 documents
- [ ] Add argparse to reingest script (--parallel, --dry-run, --retry-failed)
- [ ] Add classification summary to reingest script
- [ ] Add performance metrics tracking to reingest script
- [ ] All 58 tests pass

### GREEN -> REFACTOR Checklist

- [ ] Review script code quality
- [ ] Ensure file size limits (<500 LOC)
- [ ] Add proper docstrings
- [ ] Integration test with sample documents

## References

- Story file: `docs/implementation-artifacts/9-7-re-ingestion-process-existing-pdfs-with-new-pipeline.md`
- Epic tracking: `docs/epics/epic-9-tracking.md`
- SafetyGuard: `raglite/shared/safety.py`
- Database safety: `.claude/rules/database-safety.md`
