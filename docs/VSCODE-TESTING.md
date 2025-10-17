# VSCode Test Explorer Setup Guide

## Quick Start

Your VSCode Test Explorer is now configured for optimal discovery and execution.

### ✅ Test Discovery Fixed

**Problem:** VSCode Test Explorer had discovery errors with parallel execution flags.

**Solution:** Parallel execution is now **opt-in** via tasks or Makefile commands, allowing Test Explorer to discover tests correctly.

## How to Run Tests in VSCode

### Option 1: Test Explorer (Recommended for Individual Tests)

**Use for:**
- Running/debugging individual tests
- Exploring test structure
- Quick test validation

**How to use:**
1. Open Test Explorer (Testing icon in sidebar)
2. Tests should now be discoverable ✓
3. Click ▶️ to run individual tests or test classes
4. Right-click → "Debug Test" for debugging

**Note:** Test Explorer runs tests **sequentially** (one at a time). For parallel execution, use Option 2 or 3.

### Option 2: VSCode Tasks (Parallel Execution)

**Use for:**
- Running full test suite with parallel execution
- Running test categories (unit, integration)
- Performance profiling

**How to use:**
1. Press `Cmd+Shift+P` (Mac) or `Ctrl+Shift+P` (Windows/Linux)
2. Type "Tasks: Run Task"
3. Select a task:
   - **Test: All (Parallel)** - Run all tests with parallelization
   - **Test: Unit (Parallel)** - Unit tests only, fast feedback
   - **Test: Integration (Parallel)** - Integration tests only
   - **Test: Unit Fast (Exit on First Failure)** - TDD mode
   - **Test: With Coverage (Parallel)** - Generate coverage report
   - **Test: Show Performance Profile** - Identify slow tests
   - **Test: Failed Only (Parallel)** - Rerun only failed tests

**Keyboard shortcut:**
- `Cmd+Shift+B` (Mac) or `Ctrl+Shift+B` (Windows/Linux) → Select test task

### Option 3: Integrated Terminal + Makefile (Most Powerful)

**Use for:**
- Development workflow with quick commands
- CI/CD simulation
- Advanced test filtering

**How to use:**
Open integrated terminal (`Ctrl+``) and run:

```bash
# Fast unit tests (ideal for TDD)
make test-fast

# All tests in parallel
make test

# Unit tests with coverage
make test-unit

# Integration tests
make test-integration

# Show performance profile
make test-profile

# See all commands
make help
```

## Test Execution Comparison

| Method | Parallel | Discovery | Best For |
|--------|----------|-----------|----------|
| **Test Explorer** | ❌ Sequential | ✅ Works | Individual tests, debugging |
| **VSCode Tasks** | ✅ Parallel | ✅ Works | Full suite with parallelization |
| **Makefile** | ✅ Parallel | ✅ Works | CLI workflow, automation |
| **Direct pytest** | ⚙️ Manual | ✅ Works | Custom test runs |

## Why Two Methods?

**Test Explorer** needs to discover tests without parallelization (it's a VSCode limitation). Once discovered, you can:
- Run individual tests via Test Explorer (sequential, good for debugging)
- Run full suite via Tasks/Makefile (parallel, good for speed)

This gives you the best of both worlds! 🎉

## Configuration Details

### .vscode/settings.json
```jsonc
{
  "python.testing.pytestArgs": [
    "tests"  // Simple args for discovery
  ]
}
```

### pytest.ini
```ini
# Parallel execution NOT enabled by default
# Use tasks or Makefile for parallel execution
addopts = -v --tb=short --durations=10
```

### .vscode/tasks.json
Defines parallel test execution tasks (see Option 2 above).

## Troubleshooting

### Test Explorer shows no tests

**Solution:**
1. Reload VSCode: `Cmd+Shift+P` → "Developer: Reload Window"
2. Clear pytest cache: `make clean-test`
3. Check Python interpreter: Bottom status bar should show correct venv

### Tests are slow in Test Explorer

**Expected:** Test Explorer runs tests sequentially.

**Solution:** Use VSCode Tasks or Makefile for parallel execution.

### Tests pass in Test Explorer but fail in Makefile

**Cause:** Different execution environments (sequential vs parallel).

**Check for:**
- Test isolation issues (shared state)
- Race conditions in integration tests
- Non-unique test data (use timestamps/UUIDs)

### Task "Test: All (Parallel)" not found

**Solution:**
1. Ensure `.vscode/tasks.json` exists
2. Reload VSCode window
3. Try `Cmd+Shift+P` → "Tasks: Run Task" → Select task

## Recommended Workflow

### During Development (TDD)
```bash
# Option 1: Makefile (fastest)
make test-fast  # Unit tests only, exit on first failure

# Option 2: VSCode Task
Cmd+Shift+B → "Test: Unit Fast (Exit on First Failure)"

# Option 3: Test Explorer (for specific test)
Click on individual test → Run
```

### Before Committing
```bash
# Run full suite with coverage
make test-coverage

# Or via VSCode Task
Cmd+Shift+B → "Test: With Coverage (Parallel)"
```

### Debugging a Specific Test
1. Open Test Explorer
2. Find the failing test
3. Right-click → "Debug Test"
4. Set breakpoints as needed

### Profiling Performance
```bash
# Via Makefile
make test-profile

# Or VSCode Task
Cmd+Shift+B → "Test: Show Performance Profile"
```

## Performance Tips

1. **Use parallel execution for full test runs:**
   - Makefile: `make test` (auto-detects CPU cores)
   - VSCode Task: "Test: All (Parallel)"

2. **Use Test Explorer for individual tests:**
   - Fast discovery
   - Easy debugging
   - No parallelization overhead

3. **Run unit tests frequently:**
   - `make test-fast` (TDD workflow)
   - VSCode Task: "Test: Unit Fast"

4. **Check slow tests regularly:**
   - `make test-profile`
   - Look at `--durations` output

## Advanced Usage

### Custom Test Runs

**Terminal:**
```bash
# Specific test file with parallel execution
uv run pytest -n auto tests/unit/test_ingestion.py

# Specific test marker
uv run pytest -n auto -m "unit and not slow"

# With verbose output
uv run pytest -n auto -vv tests/
```

### Environment Variables

```bash
# Control number of parallel workers
PYTEST_XDIST_AUTO_NUM_WORKERS=4 pytest tests/

# Skip parallel execution
PYTEST_XDIST_AUTO_NUM_WORKERS=0 pytest tests/
```

## Summary

✅ **Test Explorer** - Discover and run individual tests (sequential)
✅ **VSCode Tasks** - Run full suite with parallel execution
✅ **Makefile** - Quick commands for common workflows
✅ **All options work together** - Use what fits your workflow!

For more details, see:
- `docs/TESTING-PERFORMANCE.md` - Performance optimization guide
- `Makefile` - All available test commands
- `pytest.ini` - Test configuration

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────┐
│                 VSCode Test Quick Ref                   │
├─────────────────────────────────────────────────────────┤
│ Individual Test:     Test Explorer → Click ▶️          │
│ Debug Test:          Test Explorer → Right-click → Debug│
│ All Tests (Parallel):  Cmd+Shift+B → "All (Parallel)"   │
│ Unit Tests (Fast):     make test-fast                    │
│ With Coverage:         make test-coverage                │
│ Show Slow Tests:       make test-profile                 │
│ Rerun Failed:          make test-failed                  │
│ Clean Cache:           make clean-test                   │
└─────────────────────────────────────────────────────────┘
```

Happy testing! 🚀
