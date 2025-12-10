# Quality Gates & NFR Validation

**Test Suite:** ~372 tests consolidated in `tests/` directory

---

## NFR Validation (Automated in CI)

### NFR6: Retrieval Accuracy
- **Target:** 90%+ retrieval accuracy on test set
- **Validated in:** `tests/integration/test_ac3_ground_truth.py`
- **Ground truth:** `tests/ground_truth.json` (50+ Q&A pairs)

### NFR7: Source Attribution
- **Target:** 95%+ source attribution accuracy
- **Validated in:** `tests/integration/test_accuracy_validation.py`

### NFR13: Query Response Time
- **Target:** <5s p50, <15s p95
- **Validated in:** `tests/performance/` (when implemented)

---

## Test Coverage Requirements

- **Target:** 80%+ unit test coverage (enforced in CI)
- Integration tests for end-to-end flows
- Accuracy regression tests in CI/CD
- Test count validation (prevents shadow test suites)

---

## Test Organization Summary

| Suite | Location | Count | Dependencies |
|-------|----------|-------|--------------|
| Unit | `tests/unit/` | ~200 | None |
| Integration | `tests/integration/` | ~115 | Qdrant/PostgreSQL |
| E2E | `tests/e2e/` | ~28 | Full system |

---

## CI Quality Checks

1. **Linting:** ruff, black formatting
2. **Type checking:** mypy strict mode
3. **Security:** bandit scan
4. **Tests:** pytest with coverage
5. **Accuracy:** Ground truth validation
6. **Performance:** Budget enforcement

---

## Pre-Commit Checklist

Before committing, ensure:
- [ ] All tests pass locally
- [ ] Type hints added to new functions
- [ ] Docstrings for public functions
- [ ] No new dependencies without approval
- [ ] Coverage maintained at 80%+
