# Module Rename Checklist

Safe process for renaming Python modules to prevent broken imports and test collection failures.

**Status:** For use during refactoring tasks (e.g., Epic 8 cleanup)

**Related:** `docs/ci-failure-runbook.md` → Section 10 (Module Rename Not Propagated)

---

## Pre-Rename Verification

### Step 1: Verify No External Dependencies

```bash
# Check if other projects import this module
grep -r "from OLD_MODULE_NAME import" ../
grep -r "import OLD_MODULE_NAME" ../

# If external imports exist, coordinate before renaming
```

**Decision:** Are there external imports?
- **YES** → Coordinate with other projects, use deprecation period
- **NO** → Safe to proceed

### Step 2: Document Current Location

Create a note with:
- Old module name and path: `/path/to/old_module_name.py`
- New module name and path: `/path/to/new_module_name.py`
- List of all import styles to find:
  - `from old_module_name import ...`
  - `import old_module_name`
  - `old_module_name.function()`
  - `old_module_name.ClassName`

---

## Rename Process

### Phase 1: Identify All References (Non-Destructive)

```bash
# Step 1: Find all import statements
grep -r "from old_module_name import" . --include="*.py" > /tmp/refs_from.txt
grep -r "import old_module_name" . --include="*.py" > /tmp/refs_import.txt

# Step 2: Find all usage references
grep -r "old_module_name\." . --include="*.py" > /tmp/refs_usage.txt

# Step 3: Combine and review
cat /tmp/refs_*.txt | sort | uniq > /tmp/all_references.txt
echo "Total references found: $(wc -l < /tmp/all_references.txt)"
cat /tmp/all_references.txt
```

**Validation:** Verify no references should be missed:
- [ ] Check for string references: `grep -r "old_module_name" . --include="*.py" --include="*.md"`
- [ ] Check for type hints: `grep -r "old_module_name" . --include="*.pyi"`
- [ ] Check for docstrings: `grep -r "old_module_name" . --include="*.py" | grep "\"\"\""`
- [ ] Review any matches in `.md` documentation files (update separately)

---

### Phase 2: Create New Module (Keep Old Module)

```bash
# Step 1: Copy file (don't delete yet)
cp raglite/path/old_module_name.py raglite/path/new_module_name.py

# Step 2: Verify copy is identical
diff raglite/path/old_module_name.py raglite/path/new_module_name.py
# Should show: (no output = identical)

# Step 3: Update __init__.py if needed
# (only if module is exposed via package __init__)
```

**Validation:**
- [ ] New file exists: `ls -la raglite/path/new_module_name.py`
- [ ] File is readable: `wc -l raglite/path/new_module_name.py`
- [ ] No syntax errors: `python -m py_compile raglite/path/new_module_name.py`

---

### Phase 3: Update Import References (Batch Updates)

**IMPORTANT:** Update in batches and validate after each batch

#### Batch 1: Test Files

```bash
# Find test files importing old module
grep -r "from old_module_name import\|import old_module_name" tests/ --files-with-matches

# Use sed to update (with backup)
find tests/ -name "*.py" -type f -exec sed -i.bak 's/from old_module_name import/from new_module_name import/g' {} +
find tests/ -name "*.py" -type f -exec sed -i.bak 's/import old_module_name/import new_module_name/g' {} +
find tests/ -name "*.py" -type f -exec sed -i.bak 's/old_module_name\./new_module_name\./g' {} +

# Verify changes
grep -r "new_module_name" tests/ --include="*.py" | head -10

# Clean up backup files
find tests/ -name "*.bak" -delete
```

#### Batch 2: Source Code Files

```bash
# Find source files importing old module
grep -r "from old_module_name import\|import old_module_name" raglite/ --files-with-matches

# Use sed to update
find raglite/ -name "*.py" -type f -exec sed -i.bak 's/from old_module_name import/from new_module_name import/g' {} +
find raglite/ -name "*.py" -type f -exec sed -i.bak 's/import old_module_name/import new_module_name/g' {} +
find raglite/ -name "*.py" -type f -exec sed -i.bak 's/old_module_name\./new_module_name\./g' {} +

# Verify changes
grep -r "new_module_name" raglite/ --include="*.py" | head -10

# Clean up backup files
find raglite/ -name "*.bak" -delete
```

#### Batch 3: Documentation Files (If Needed)

```bash
# Find docs mentioning old module
grep -r "old_module_name" docs/ --include="*.md"

# Update with editor or sed
find docs/ -name "*.md" -type f -exec sed -i.bak 's/old_module_name/new_module_name/g' {} +

# Verify and clean up
grep -r "old_module_name" docs/ --include="*.md"
find docs/ -name "*.bak" -delete
```

**Validation After Each Batch:**
- [ ] Run syntax check: `python -m py_compile <updated_file>`
- [ ] No references to old module remain: `grep -r "old_module_name" <batch_dir>`

---

### Phase 4: Validate Test Collection

```bash
# Clear bytecode cache
find . -name "*.pyc" -delete
find . -type d -name "__pycache__" -exec rm -rf {} +

# Run test collection only (no actual tests)
pytest --collect-only -q 2>&1 | tee /tmp/collection_output.txt

# Check for ModuleNotFoundError
grep -i "error\|ModuleNotFoundError\|ImportError" /tmp/collection_output.txt
# Should be EMPTY or only unrelated errors

# Count total tests collected
echo "Total tests collected: $(grep -c "<Function\|<Method" /tmp/collection_output.txt)"
```

**Validation Checklist:**
- [ ] No `ModuleNotFoundError` in output
- [ ] No `ImportError` mentioning old module name
- [ ] Test count stable (similar to before rename)
- [ ] All test files collected without errors

---

### Phase 5: Run Full Test Suite (Local)

```bash
# Run unit tests (no databases required)
pytest tests/unit/ -v --tb=short 2>&1 | tee /tmp/unit_tests.txt

# Check for any failures
grep -E "FAILED|ERROR" /tmp/unit_tests.txt | head -20

# If failures, examine them
# If pass, proceed
```

**Validation:**
- [ ] Unit tests pass: `grep "passed" /tmp/unit_tests.txt`
- [ ] No import-related failures
- [ ] All modules resolving correctly

---

### Phase 6: Delete Old Module (Final Step)

**ONLY after validation passes:**

```bash
# Final confirmation before deletion
echo "Files still referencing old_module_name:"
grep -r "old_module_name" . --include="*.py" --include="*.md" 2>/dev/null | grep -v ".bak" | wc -l

# If count is ZERO, safe to delete
rm raglite/path/old_module_name.py

# Verify deletion
test -f raglite/path/old_module_name.py && echo "FAILED: File still exists" || echo "SUCCESS: File deleted"
```

**DANGER ZONE:** Do NOT proceed to this step if:
- [ ] Any references to old module name remain
- [ ] Test collection failed
- [ ] Test suite showed failures

---

## Rollback Procedure (If Things Break)

### If Deletion Failed

```bash
# Step 1: Restore old module from git
git checkout raglite/path/old_module_name.py

# Step 2: Keep new module (both exist during deprecation)
# Or remove new module if rename is being abandoned
rm raglite/path/new_module_name.py

# Step 3: Revert all import changes
git checkout tests/ raglite/
```

### If Only Some Files Updated

```bash
# Find which files reference which module
grep -r "from old_module_name\|from new_module_name" . --include="*.py" | sort

# Revert and retry with more care
git checkout raglite/ tests/
# Start over from Phase 3 with better tracking
```

---

## Verification Checklist

**Before Committing:**

- [ ] All references found and updated
- [ ] Test collection succeeds without errors
- [ ] Unit tests pass locally
- [ ] Old module file deleted (if in Phase 6)
- [ ] New module file exists and is identical to old
- [ ] No `.bak` files left behind
- [ ] No `.pyc` files in repository
- [ ] Documentation updated if mentioning module name
- [ ] Commit message references module rename

### Commit Message Template

```
refactor: rename module old_module_name -> new_module_name

- Renamed raglite/path/old_module_name.py -> raglite/path/new_module_name.py
- Updated X imports in tests/
- Updated Y imports in raglite/
- Updated Z references in documentation
- Verified test collection and unit tests pass
- Resolved issue #XXX (if applicable)
```

---

## Automated Verification Script

### Quick Validation

```bash
#!/bin/bash
# save as: scripts/verify-module-rename.sh

OLD_NAME=${1:-ingestion}
NEW_NAME=${2:-ingestion_tool}

echo "Verifying rename: $OLD_NAME -> $NEW_NAME"
echo ""

# Check old module still exists (error if deleted before validation)
if [ ! -f "raglite/path/${OLD_NAME}.py" ]; then
    echo "WARNING: Old module already deleted (ok if final step)"
fi

# Check new module exists
if [ ! -f "raglite/path/${NEW_NAME}.py" ]; then
    echo "ERROR: New module not found"
    exit 1
fi

# Check for orphaned references
ORPHANED=$(grep -r "$OLD_NAME" . --include="*.py" 2>/dev/null | grep -v ".bak" | wc -l)
if [ "$ORPHANED" -gt 0 ]; then
    echo "ERROR: Found $ORPHANED orphaned references:"
    grep -r "$OLD_NAME" . --include="*.py" 2>/dev/null | grep -v ".bak"
    exit 1
fi

# Test collection
pytest --collect-only -q > /tmp/collection.txt 2>&1
if grep -qi "error\|ModuleNotFoundError" /tmp/collection.txt; then
    echo "ERROR: Test collection failed:"
    grep -i "error\|ModuleNotFoundError" /tmp/collection.txt
    exit 1
fi

echo "SUCCESS: Rename validation complete"
echo "- New module exists: raglite/path/${NEW_NAME}.py"
echo "- No orphaned references to $OLD_NAME"
echo "- Test collection successful"
```

**Usage:**

```bash
bash scripts/verify-module-rename.sh old_module_name new_module_name
```

---

## Common Pitfalls

| Pitfall | Prevention |
|---------|-----------|
| Missing imports in hidden files (e.g., `__init__.py`) | Use `grep -r` on ALL Python files |
| String references in docstrings not updated | Search docstrings explicitly |
| `.pyc` files caching old module | Clear cache: `find . -name "*.pyc" -delete` |
| Stale imports in type hints | Check `.pyi` files and `TYPE_CHECKING` blocks |
| External projects still importing | Verify no external dependencies first |
| Reverting in middle of rename leaves duplicates | Use git checkout to revert entire rename |
| Commit without validation | Always run full checklist before committing |

---

## Success Criteria

Rename is COMPLETE when:

1. [ ] Old module deleted (or marked deprecated with warning)
2. [ ] New module exists and is identical to old
3. [ ] All imports updated to new module name
4. [ ] `grep -r "old_module_name" .` returns ZERO matches (except comments)
5. [ ] `pytest --collect-only` succeeds
6. [ ] Unit tests pass: `pytest tests/unit/ -v`
7. [ ] All changes committed with clear message

---

## Related Documentation

- **CI Failure Runbook**: `docs/ci-failure-runbook.md` → Section 10
- **Test Reliability Rules**: `.claude/rules/testing.md`
- **Quality Gates**: `.claude/rules/quality-gates.md`
