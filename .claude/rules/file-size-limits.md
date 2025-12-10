# File Size Limits

**PRIORITY: HIGH** - Large files degrade AI comprehension and increase maintenance burden.

---

## Research-Backed Thresholds

| Threshold | LOC | Token Estimate | AI Impact |
|-----------|-----|----------------|-----------|
| **Ideal** | 100-250 | 1,000-2,500 | Full context comprehension |
| **Warning** | 400 | ~4,000 | Design review recommended |
| **Hard Limit** | 500 | ~5,000 | Must refactor or justify exception |

**Token Ratio:** ~10 tokens per line of Python code

**Sources:**
- Cursor forum (300-350 LOC optimal for AI parsing/refactoring)
- Augment Code research (500-800 LOC: more AI mistakes, partial edits)
- Uncle Bob / Clean Code (average 20-50 LOC, most files <100 LOC)
- PEP 8 community practices (300-500 soft limit, 1000 red flag)

---

## Enforcement Mechanisms

### 1. Pre-commit Hook
Blocks commits with new files >500 LOC:
```bash
# Runs automatically on git commit
pre-commit run check-file-sizes
```

### 2. CI Job
GitHub Actions validates against baseline:
- Fails on NEW violations in `raglite/` (production code)
- Warns only on `tests/` (soft enforcement)

### 3. Exception File
`.file-size-exceptions` grandfathers existing violations.

---

## Quick Reference

```bash
# Check file sizes locally
python scripts/check_file_sizes.py

# Check with verbose output (shows all violations)
python scripts/check_file_sizes.py --verbose

# Generate new baseline (after intentional refactoring)
python scripts/check_file_sizes.py --generate-baseline

# Strict mode (fail on ALL violations, ignore exceptions)
python scripts/check_file_sizes.py --strict
```

---

## Enforcement Policy

| Directory | Mode | New Violations |
|-----------|------|----------------|
| `raglite/` | **Strict** | CI fails, must fix or add exception |
| `tests/` | **Warn** | Warnings only, no CI failure |

**Rationale:** Test files often have more fixtures/assertions but should still be split by behavior when large. Research shows same limits work for both, but strict enforcement on tests creates overhead.

---

## Exception Process

To add an exception, file must meet ONE of:
1. Generated/boilerplate code (data classes, mappings)
2. Refactoring scheduled with linked issue/story
3. Complex algorithm that cannot be reasonably split

### Adding an Exception

1. Open `.file-size-exceptions`
2. Add entry with justification:
```json
"raglite/path/to/file.py": {
  "lines": 650,
  "reason": "Refactoring planned for Epic 7 Story 7.X",
  "target_lines": 500,
  "directory": "raglite/"
}
```
3. Create PR with explanation of why exception is necessary

---

## Ratchet Rules

1. **No NEW files >500 LOC** - Hard fail in CI for `raglite/`
2. **Existing violations tracked** - Grandfathered in `.file-size-exceptions`
3. **Count must not increase** - Each PR must not add new exceptions
4. **Reward reductions** - Removing file from exceptions is always welcome

---

## Refactoring Guidance

### When a file approaches 400 LOC:

1. **Identify cohesive groups** - Functions that work together
2. **Extract to new module** - Create `*_utils.py`, `*_helpers.py`, or domain-specific files
3. **Keep imports clean** - Avoid circular dependencies
4. **Update `__init__.py`** - Maintain public API if needed

### Common Split Patterns

| Current File | Split Into |
|--------------|------------|
| `module.py` (600 LOC) | `module.py` (300) + `module_utils.py` (300) |
| `client.py` (800 LOC) | `client/api.py` (400) + `client/parser.py` (400) |
| `processor.py` (700 LOC) | `processor.py` (350) + `processor_types.py` (350) |

### Standard Acceptance Criteria for Refactoring

- AC1: Original file reduced to <500 LOC
- AC2: All new modules <500 LOC each
- AC3: All existing tests pass unchanged
- AC4: No circular dependencies
- AC5: Maintain ≥80% coverage on modified modules

---

## Current Status

**See:** `docs/analysis/file-size-refactoring-briefing.md` for full inventory of violations and refactoring plans.

**Quick Stats:**
- Production files exceeding limit: Check with `python scripts/check_file_sizes.py --verbose`
- Total exceptions: Check `.file-size-exceptions`

---

## Why This Matters

### AI Comprehension
- Large files get chunked by LLMs, breaking global understanding
- Partial context leads to missed side effects
- Increased risk of inconsistent edits

### Developer Experience
- Smaller files are easier to review
- Single responsibility = easier maintenance
- Faster navigation and understanding

### Code Quality
- Forces modular design
- Encourages separation of concerns
- Prevents "god files" that do everything
