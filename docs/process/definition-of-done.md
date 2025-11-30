# Definition of Done (DoD)

This checklist defines what "done" means for any user story in the RAGLite project. All items must be satisfied before a story can be marked complete and merged.

## Quick Reference

Use this checklist for PR reviews and story completion verification.

---

## 1. Code Quality

- [ ] Code review approved by senior developer
- [ ] All acceptance criteria verified and working
- [ ] No untracked `TODO`/`FIXME` markers (or linked to issue tracker)
- [ ] Type hints on all function signatures
- [ ] Google-style docstrings on all public functions
- [ ] Code follows project patterns (see `docs/architecture/6-complete-reference-implementation.md`)

## 2. Testing

- [ ] All unit tests pass (`uv run pytest tests/unit/`)
- [ ] All integration tests pass (`uv run pytest tests/integration/`)
- [ ] All E2E tests pass (`uv run pytest tests/e2e/`)
- [ ] **New code has ≥80% test coverage** (measured via `pytest --cov`)
- [ ] **Overall project coverage must not decrease** (CI/CD enforced ratchet)
- [ ] No skipped tests without issue reference (`@pytest.mark.skip(reason="Issue #123")`)

### Coverage Commands

```bash
# Check overall coverage locally
uv run pytest --cov=raglite --cov=scripts --cov-report=term

# Check coverage with HTML report (detailed view)
uv run pytest --cov=raglite --cov-report=html
# Then open: htmlcov/index.html

# Check coverage of specific module
uv run pytest --cov=raglite/ingestion --cov-report=term tests/unit/

# Check coverage diff for changed files (used by CI/CD)
python scripts/check_coverage_diff.py --threshold=80

# Check coverage ratchet (verify no regression)
python scripts/check_coverage_ratchet.py
```

### Coverage Requirements (Non-Negotiable)

| Requirement | Threshold | Enforcement |
|-------------|-----------|-------------|
| New code coverage | ≥80% | CI/CD gate (fails PR if not met) |
| Overall coverage | No decrease | CI/CD ratchet (fails if regression) |

**Why 80%?** Based on Epic 3 retrospective findings: explicit thresholds prevent technical debt accumulation. The 80% threshold balances coverage quality with practical development velocity.

## 3. Documentation

- [ ] Code changes documented in story file (Dev Agent Record → Completion Notes)
- [ ] Architecture decisions documented (if significant changes)
- [ ] README updated (if user-facing changes or new features)
- [ ] Docstrings explain non-obvious logic

## 4. Security & Quality

- [ ] No secrets, credentials, or API keys in code
- [ ] No hardcoded environment-specific values
- [ ] Linting passes: `uv run ruff check .`
- [ ] Type checking passes (if configured): `uv run mypy raglite/`

## 5. CI/CD

- [ ] All GitHub Actions checks pass
- [ ] Coverage gate passes (new code ≥80%)
- [ ] Coverage ratchet passes (no regression)
- [ ] PR receives coverage summary comment

### CI/CD Enforcement Details

The CI/CD pipeline (`.github/workflows/ci.yml`) automatically enforces coverage requirements:

| Check | Script | Behavior |
|-------|--------|----------|
| Coverage Gate | `scripts/check_coverage_diff.py` | Fails PR if new code <80% covered |
| Coverage Ratchet | `scripts/check_coverage_ratchet.py` | Fails PR if overall coverage decreases |
| Coverage Comment | Automated | Posts coverage summary on PR |

**PRs that fail coverage checks cannot be merged.**

---

## Story Completion Workflow

1. **Before PR:** Run coverage locally to verify thresholds
2. **Create PR:** CI/CD runs all checks automatically
3. **Fix Issues:** Address any coverage or test failures
4. **Review:** Senior developer reviews and approves
5. **Merge:** Only after all DoD items checked

## Related Documentation

- [CI/CD Workflow](.github/workflows/ci.yml) - Automated enforcement
- [Coverage Diff Script](scripts/check_coverage_diff.py) - 80% threshold logic
- [Coverage Ratchet Script](scripts/check_coverage_ratchet.py) - Regression prevention
- [Testing Guidelines](docs/architecture/6-complete-reference-implementation.md) - Test patterns

---

*Last updated: 2025-11-24 (Story 4.0.2)*
*Source: Epic 3 Retrospective Action Item 2*
