# Test Design: Epic 9 - Data Quality at Ingestion

**Date:** 2026-01-31
**Author:** Ricardo
**Status:** Draft

---

## Executive Summary

**Scope:** Full test design for Epic 9 - Data Quality at Ingestion

**Epic Context:** Add classification layer (period_type, value_type, entity_level) at ingestion time to resolve 99.3% data loss in forecasting. Eliminates need for 20+ fix scripts by addressing root cause.

**Expected Impact:** 292 GROUP EBITDA records with 0.7% usability (2/292 usable) → 90% usability target = **128x improvement** in forecasting data quality (AC3).

**Risk Summary:**

- Total risks identified: 7
- High-priority risks (≥6): 2 (R-001: LLM classification accuracy, R-007: LLM API resilience)
- Critical categories: TECH (4), DATA (2), PERF (1), BUS (1)

**Coverage Summary:**

- P0 scenarios: 9 (18 hours)
- P1 scenarios: 12 (12 hours)
- P2 scenarios: 10 (5 hours)
- P3 scenarios: 4 (1 hour)
- **Total effort**: 35 hours (~4.5 days)

---

## Risk Assessment

### High-Priority Risks (Score ≥6)

| Risk ID | Category | Description                                                                      | Probability | Impact | Score | Mitigation                                                                             | Owner | Timeline    |
| ------- | -------- | -------------------------------------------------------------------------------- | ----------- | ------ | ----- | -------------------------------------------------------------------------------------- | ----- | ----------- |
| R-001   | TECH     | LLM classification accuracy <95% on edge cases (ambiguous periods, mixed entities) | 2 (Possible) | 3 (Critical) | **6** | Ground truth validation (50+ samples), regex fallbacks, iterative prompt tuning, AC1/AC2 validation gates | DEV   | Story 9.2-9.4 |

### High-Priority Risks (Score ≥6) - CONTINUED

| Risk ID | Category | Description                                                                      | Probability | Impact | Score | Mitigation                                                                             | Owner | Timeline    |
| ------- | -------- | -------------------------------------------------------------------------------- | ----------- | ------ | ----- | -------------------------------------------------------------------------------------- | ----- | ----------- |
| **R-007** | **TECH** | **LLM API unavailable/rate-limited blocks entire ingestion pipeline (synchronous dependency)** | **2 (Possible)** | **3 (Critical)** | **6** | **Fail-fast regex fallback within 5s, no retries during batch, AC2.4 validation, P0 test added (Winston)** | **DEV** | **Story 9.2** |

### Medium-Priority Risks (Score 3-4)

| Risk ID | Category | Description                                                                  | Probability | Impact | Score | Mitigation                                                                         | Owner |
| ------- | -------- | ---------------------------------------------------------------------------- | ----------- | ------ | ----- | ---------------------------------------------------------------------------------- | ----- |
| R-002   | DATA     | Re-ingestion creates duplicates or conflicts in PostgreSQL (78K existing rows) | 2 (Possible) | 2 (Degraded) | 4 | Dry-run validation, transaction rollback on conflict, backup before Story 9.7       | DEV   |
| R-003   | PERF     | Ingestion time increase >20% target due to LLM overhead                      | 2 (Possible) | 2 (Degraded) | 4 | Benchmark baseline, optimize LLM batch calls, async classification, AC4 validation | DEV   |
| R-005   | TECH     | Integration breaks existing test suite (372 tests)                           | 2 (Possible) | 2 (Degraded) | 4 | Run full suite after each story, maintain test count, CI quality gates             | QA    |
| R-006   | DATA     | Period normalization introduces parsing errors (30+ format variants)         | 2 (Possible) | 2 (Degraded) | 4 | Comprehensive unit tests, fallback to original on error, ground truth validation   | DEV   |

### Low-Priority Risks (Score 1-3)

| Risk ID | Category | Description                                                | Probability | Impact | Score | Action   |
| ------- | -------- | ---------------------------------------------------------- | ----------- | ------ | ----- | -------- |
| R-004   | BUS      | Forecasting queries fail if classification fields NULL      | 1 (Unlikely) | 3 (Critical) | 3 | Nullable columns provide safety, validation ensures 100% coverage (AC3) |

### Risk Category Legend

- **TECH**: Technical/Architecture (flaws, integration, scalability)
- **SEC**: Security (access controls, auth, data exposure)
- **PERF**: Performance (SLA violations, degradation, resource limits)
- **DATA**: Data Integrity (loss, corruption, inconsistency)
- **BUS**: Business Impact (UX harm, logic errors, revenue)
- **OPS**: Operations (deployment, config, monitoring)

---

## Test Coverage Plan

### P0 (Critical) - Run on every commit

**Criteria**: Blocks Epic 4 forecasting + High classification accuracy (AC1) + No fallback path

| Requirement                                                  | Test Level  | Risk Link | Test Count | Owner | Notes                                          |
| ------------------------------------------------------------ | ----------- | --------- | ---------- | ----- | ---------------------------------------------- |
| AC1: Period type classification ≥95% accuracy                | Integration | R-001     | 1          | QA    | Ground truth validation (50+ samples)          |
| AC1: Value type classification ≥90% accuracy                 | Integration | R-001     | 1          | QA    | Context clue detection (budget vs actual)      |
| AC1: Entity level classification ≥90% accuracy               | Integration | R-001     | 1          | QA    | Hierarchy detection (country/region/group)     |
| AC3: 100% classification field coverage (no NULLs)           | Integration | R-004     | 1          | QA    | Validation after ingestion                     |
| AC4: All 372 existing tests pass after integration           | E2E         | R-005     | 1          | QA    | Regression prevention                          |
| Story 9.1: Schema migration succeeds without data loss       | Integration | R-002     | 1          | DEV   | ALTER TABLE with rollback validation           |
| Story 9.7: Re-ingestion completes without duplicates         | Integration | R-002     | 1          | DEV   | Conflict detection, rollback validation, 33 PDFs |
| Story 9.8: Forecasting queries use classification columns    | Integration | R-004     | 1          | DEV   | Simple WHERE clauses replace parsing logic     |
| Story 9.2 AC2.4: Regex fallback within 5s when LLM API unavailable (429/503/timeout) | Integration | R-007 | 1 | DEV | External dependency resilience (Winston) |

**Total P0**: 9 tests, 18 hours

### P1 (High) - Run on PR to main

**Criteria**: Critical logic paths + Medium risk (3-4) + Quality gates

| Requirement                                                | Test Level  | Risk Link | Test Count | Owner | Notes                                    |
| ---------------------------------------------------------- | ----------- | --------- | ---------- | ----- | ---------------------------------------- |
| Period normalization handles Portuguese months            | Unit        | R-006     | 1          | DEV   | Jan-24 → January 2024                    |
| Period normalization handles 4-digit years                 | Unit        | R-006     | 1          | DEV   | 2024 → Year 2024                         |
| Period normalization handles YTD prefixes                  | Unit        | R-006     | 1          | DEV   | "YTD Jun-24" → ytd_actual + Jun-24       |
| Period normalization handles budget prefixes               | Unit        | R-006     | 1          | DEV   | "B Dec-21" → budget + Dec-21             |
| LLM fallback triggers when regex patterns fail             | Unit        | R-001     | 1          | DEV   | Unknown formats use LLM inference        |
| Classification reports generated with usability metrics    | Integration | R-001     | 1          | QA    | AC3: Reports for every ingestion         |
| AC4: Ingestion time increases <20% from baseline           | Performance | R-003     | 1          | QA    | Benchmark before/after classification    |
| Story 9.6: Storage layer stores all classification fields  | Integration | R-002     | 1          | DEV   | INSERT verification with new columns     |
| Story 9.8: Forecasting module reduces 50+ LOC             | Unit        | R-006     | 1          | DEV   | AC2: Complexity reduction                |
| AC4: MCP tools function without breaking changes           | Integration | R-005     | 1          | QA    | Ingestion/query tools still work         |
| Schema migration rollback succeeds on error                | Integration | R-002     | 1          | DEV   | Transaction safety                       |
| Ground truth validation detects classification failures    | Integration | R-001     | 1          | QA    | AC3: 50+ classified examples             |

**Total P1**: 12 tests, 12 hours

### P2 (Medium) - Run nightly/weekly

**Criteria**: Edge cases + Error handling + Performance optimizations

| Requirement                                              | Test Level  | Risk Link | Test Count | Owner | Notes                               |
| -------------------------------------------------------- | ----------- | --------- | ---------- | ----- | ----------------------------------- |
| Unknown period formats fallback to "unknown"             | Unit        | R-006     | 1          | DEV   | Graceful degradation                |
| Unknown entity names fallback gracefully                 | Unit        | R-006     | 1          | DEV   | No classification blocking          |
| Budget vs actual detection from context clues            | Unit        | R-001     | 1          | DEV   | Table caption parsing               |
| Consolidated entity level detection                      | Unit        | R-001     | 1          | DEV   | Group-level aggregation             |
| Error logging captures classification failures           | Unit        | -         | 1          | DEV   | Observability for debugging         |
| Multiple period format variants normalize correctly      | Unit        | R-006     | 1          | DEV   | Comprehensive format coverage       |
| Batch classification optimizes LLM calls                 | Integration | R-003     | 1          | DEV   | Performance optimization            |
| PostgreSQL indexes improve query performance             | Integration | R-003     | 1          | DEV   | Query plan analysis                 |
| Transaction rollback on conflict during re-ingestion     | Integration | R-002     | 1          | DEV   | Story 9.7 safety mechanism          |
| Classification prompt tuning workflow                    | Manual      | R-001     | 1          | QA    | Iterative accuracy improvement      |

**Total P2**: 10 tests, 5 hours

### P3 (Low) - Run on-demand

**Criteria**: Observability + Debug tools + Analytics

| Requirement                                  | Test Level  | Test Count | Owner | Notes                        |
| -------------------------------------------- | ----------- | ---------- | ----- | ---------------------------- |
| Classification metrics exported for analytics | Integration | 1          | DEV   | Tracking classification accuracy over time |
| Debug mode shows classification reasoning    | Unit        | 1          | DEV   | LLM prompt inspection        |
| Manual override for misclassifications       | Unit        | 1          | DEV   | Correction mechanism (future) |
| Historical accuracy trend tracking           | Manual      | 1          | QA    | Dashboard/reporting          |

**Total P3**: 4 tests, 1 hour

---

## Execution Order

### Smoke Tests (<5 min)

**Purpose**: Fast feedback on classification pipeline integration

- [ ] Schema migration check: All new columns exist in PostgreSQL (30s)
- [ ] Classification module imports successfully without errors (15s)
- [ ] Single PDF ingestion completes with all classification fields populated (2min)

**Total**: 3 scenarios (~3 min)

### P0 Tests (<10 min)

**Purpose**: Critical quality gates for Epic 4 unblocking

- [ ] Period type classification ≥95% accuracy on ground truth (Integration, 2min)
- [ ] Value type classification ≥90% accuracy on ground truth (Integration, 1min)
- [ ] Entity level classification ≥90% accuracy on ground truth (Integration, 1min)
- [ ] 100% classification field coverage validation (Integration, 1min)
- [ ] All 372 existing tests pass (E2E, 3min)
- [ ] Schema migration succeeds without data loss (Integration, 30s)
- [ ] Re-ingestion of 33 PDFs without duplicates (Integration, 1min)
- [ ] Forecasting queries use new classification columns (Integration, 30s)
- [ ] Classification succeeds with regex-only when LLM API unavailable (Integration, 1min)

**Total**: 9 scenarios (~11 min)

### P1 Tests (<20 min)

**Purpose**: Classification logic and integration quality

- [ ] Period normalization edge cases (Unit, 5min)
- [ ] LLM fallback mechanisms (Unit, 2min)
- [ ] Classification report generation (Integration, 2min)
- [ ] Ingestion time <20% increase (Performance, 3min)
- [ ] Storage layer integration (Integration, 2min)
- [ ] Forecasting module simplification (Unit, 2min)
- [ ] MCP tools compatibility (Integration, 2min)
- [ ] Schema rollback safety (Integration, 1min)
- [ ] Ground truth validation (Integration, 1min)

**Total**: 12 scenarios (~20 min)

### P2/P3 Tests (<30 min)

**Purpose**: Edge cases, optimizations, observability

- [ ] Unknown format fallbacks (Unit, 5min)
- [ ] Error logging and debugging (Unit, 3min)
- [ ] Performance optimizations (Integration, 8min)
- [ ] Transaction safety (Integration, 2min)
- [ ] Classification metrics/analytics (Integration/Manual, 12min)

**Total**: 14 scenarios (~30 min)

---

## Resource Estimates

### Test Development Effort

| Priority  | Count  | Hours/Test | Total Hours | Notes                                      |
| --------- | ------ | ---------- | ----------- | ------------------------------------------ |
| P0        | 9      | 2.0        | 18          | Ground truth validation, regression prevention, API resilience |
| P1        | 12     | 1.0        | 12          | Classification logic, integration quality  |
| P2        | 10     | 0.5        | 5           | Edge cases, error handling                 |
| P3        | 4      | 0.25       | 1           | Observability, analytics                   |
| **Total** | **35** | **-**      | **36**      | **~4.5 days**                              |

### Prerequisites

**Test Data:**

- **Ground truth dataset**: 50+ manually classified financial table records (period, value type, entity level)
- **PDF fixtures**: Existing 33 PDFs from `tests/fixtures/financial-reports/`
- **Classification test set**: Edge cases (Portuguese months, 4-digit years, YTD/Budget prefixes, consolidated entities)
- **Performance baseline**: Current ingestion times for 33 PDFs (measured before Epic 9)

**Tooling:**

- **pytest** for unit/integration tests
- **PostgreSQL test database** (port 5433) with schema migration scripts
- **LLM mocking** for deterministic unit tests (avoid API calls in CI)
- **Ground truth validation script** (`scripts/validate_classification_accuracy.py`)
- **Performance profiler** (`cProfile` or `pytest-benchmark`) for ingestion time measurement

**Environment:**

- PostgreSQL test database with `APP_ENV=test` safety guard
- Qdrant test instance (port 6335) for integration tests
- Test PDFs with diverse period formats, entity hierarchies, value types
- CI environment variables for LLM API keys (or mocked in unit tests)

---

## Quality Gate Criteria

### Pass/Fail Thresholds

- **P0 pass rate**: 100% (no exceptions)
- **P1 pass rate**: ≥95% (waivers required for failures)
- **P2/P3 pass rate**: ≥90% (informational)
- **High-risk mitigations**: 100% complete or approved waivers

### Coverage Targets

- **Critical paths**: ≥80%
- **Security scenarios**: 100%
- **Business logic**: ≥70%
- **Edge cases**: ≥50%

### Non-Negotiable Requirements

- [ ] All P0 tests pass
- [ ] No high-risk (≥6) items unmitigated
- [ ] Security tests (SEC category) pass 100%
- [ ] Performance targets met (PERF category)

---

## Mitigation Plans

### R-001: LLM Classification Accuracy <95% (Score: 6)

**Mitigation Strategy:**

1. **Ground Truth Validation (Story 9.9)**: Create 50+ manually classified examples covering edge cases:
   - Portuguese month abbreviations (Jan-24, Fev-24, etc.)
   - 4-digit year formats (2024 → Year 2024)
   - YTD prefixes ("YTD Jun-24" → ytd_actual + Jun-24)
   - Budget prefixes ("B Dec-21" → budget + Dec-21)
   - Mixed entity hierarchies (Portugal/Iberia/GROUP)

2. **Regex Fallback Layer**: Implement deterministic patterns for known formats before LLM invocation
   - Period patterns: `r"(YTD |B )?([A-Z][a-z]{2})-(\d{2})"` → Extract prefix, month, year
   - Entity patterns: Known countries/regions dictionary lookup
   - Unit patterns: Standard abbreviations (M EUR, K$, etc.)

3. **Iterative Prompt Tuning**: If accuracy <95% after Story 9.2-9.4:
   - Analyze misclassified samples from ground truth
   - Add examples to LLM prompt (few-shot learning)
   - Re-run validation, repeat until ≥95%

4. **Acceptance Criteria Enforcement**: Story 9.9 validation BLOCKS Epic 9 completion if AC1 not met

**Owner:** DEV (Stories 9.2-9.4) + QA (Story 9.9 validation)

**Timeline:** Stories 9.2-9.4 (Days 2-3), Story 9.9 (Day 6)

**Status:** Planned

**Verification:** `scripts/validate_classification_accuracy.py --ground-truth tests/ground_truth_classification.json --threshold 0.95` (automated gate check)

---

## Assumptions and Dependencies

### Assumptions

1. **Existing 33 PDFs contain sufficient format diversity** - Ground truth validation assumes current test fixtures cover all major period/entity/value type variants
2. **LLM API availability** - Classification relies on Claude/Mistral API being accessible during ingestion (Story 9.2-9.4 should include fallback to regex if API unavailable)
3. **Nullable columns provide migration safety** - Story 9.1 assumes nullable classification columns allow gradual rollout without breaking existing queries
4. **Forecasting module complexity reduction is measurable** - AC2 assumes 50+ LOC reduction can be objectively measured before/after Story 9.8
5. **Re-ingestion does NOT require downtime** - Story 9.7 assumes PostgreSQL can handle re-ingestion while forecasting queries continue (read-write concurrency)

### Dependencies

1. **Story 9.1 (Schema Migration) blocks Stories 9.2-9.6** - Classification modules cannot store results until columns exist
2. **Stories 9.2-9.4 (Classification Modules) block Story 9.5 (Integration)** - Extraction pipeline cannot call classifiers until modules exist
3. **Story 9.6 (Storage Extension) blocks Story 9.7 (Re-Ingestion)** - Cannot re-ingest until storage layer supports new fields
4. **Story 9.7 (Re-Ingestion) blocks Story 9.8 (Forecasting Simplification)** - Forecasting cannot use classification fields until data is populated
5. **Story 9.8 blocks Story 9.9 (Validation)** - Cannot validate end-to-end flow until forecasting uses new columns

### Risks to Plan

- **Risk**: Classification accuracy fails to reach 95% threshold after multiple prompt tuning iterations
  - **Impact**: Epic 9 blocked, Epic 4 remains blocked, data quality issue persists
  - **Contingency**: Escalate to architect for hybrid approach (manual classification for high-value metrics, automated for long-tail)

- **Risk**: Re-ingestion of 33 PDFs takes >1 hour (blocking development workflow)
  - **Impact**: Story 9.7 delayed, slows validation cycle
  - **Contingency**: Batch re-ingestion overnight, use subset (10 PDFs) for smoke tests

- **Risk**: Ingestion time increase exceeds 20% threshold (AC4 violation)
  - **Impact**: User experience degraded, Epic 9 acceptance criteria not met
  - **Contingency**: Implement async classification pipeline (queue-based), optimize LLM batch calls

---

---

## Follow-on Workflows (Manual)

- Run `*atdd` to generate failing P0 tests (separate workflow; not auto-run).
- Run `*automate` for broader coverage once implementation exists.

---

## Approval

**Test Design Approved By:**

- [ ] Product Manager: {name} Date: {date}
- [ ] Tech Lead: {name} Date: {date}
- [ ] QA Lead: {name} Date: {date}

**Comments:**

---

---

---

## Appendix

### Knowledge Base References

- `risk-governance.md` - Risk classification framework
- `probability-impact.md` - Risk scoring methodology
- `test-levels-framework.md` - Test level selection
- `test-priorities-matrix.md` - P0-P3 prioritization

### Related Documents

- **Sprint Change Proposal**: `docs/implementation-artifacts/sprint-change-proposal-2026-01-30.md` (root cause analysis, Epic 9 rationale)
- **Epic 9 Tracking**: `docs/epics/epic-9-tracking.md` (story breakdown, success criteria, timeline)
- **Architecture**: `docs/architecture/3-repository-structure-monolithic.md` (module structure)
- **Database Schema**: `migrations/002_add_classification_columns.py` (Story 9.1)
- **Classification Foundation**: Commit `58fbc9e` (PeriodType enum, Portuguese months, classification report)
- **Epic 4 (Forecasting)**: `docs/prd/epic-4-forecasting-proactive-insights.md` (blocked until Epic 9 complete)

---

**Generated by**: BMad TEA Agent - Test Architect Module
**Workflow**: `_bmad/bmm/testarch/test-design`
**Version**: 4.0 (BMad v6)
