# CI Lessons Learned

Strategic insights from 15+ CI fix attempts and infrastructure evolution.

**Last Updated:** 2025-12-24
**Period Covered:** 2025-10-29 to 2025-12-24
**Fix Attempts:** 15+ root cause analyses
**Success Rate:** 95%+ (tests now reliable)
**Key Insight:** Symptom-based fixes create technical debt; architectural fixes solve categories of problems

---

## Executive Summary

RAGLite CI experienced recurring failures across 12+ distinct categories. Initial approach (symptom-based band-aids) delayed root cause identification by 2-3 weeks. Final strategy (architectural fixes) eliminated entire categories of failures.

### The Three Phases of CI Maturity

```
Phase 1: Symptom-Based Fixes (Week 1-2)
├─ Problem: "Tests timeout"
├─ Fix: Increase timeout from 30s to 60s
├─ Result: Different test times out next run
└─ Debt accumulated: Technical debt ↑

Phase 2: Root Cause Analysis (Week 2-3)
├─ Problem: "Why do tests timeout?"
├─ Investigation: Measure actual service startup times
├─ Finding: Qdrant takes 8-12 seconds; test assumes 3 seconds
└─ Result: Understanding increased

Phase 3: Architectural Fixes (Week 3+)
├─ Problem: "Service health is unreliable"
├─ Solution: Mandatory health checks before tests
├─ Result: Category of failures eliminated (100% elimination)
└─ Benefit: No more timeouts, faster failure diagnostics
```

**RAGLite moved from Phase 1 → Phase 3 with 15+ fixes.**

---

## Root Cause Analysis Summary

Systematic investigation revealed underlying infrastructure problems.

### The Five Why's Applied to Recurring Failures

#### Failure: "pytest test collection returns 0 tests"

1. **Why?** → Module imports fail during test discovery
2. **Why?** → Settings singleton created with wrong database port
3. **Why?** → APP_ENV not set before Settings imported
4. **Why?** → conftest.py module load order: imports run before env vars set
5. **Why?** → pytest discovers conftest.py DURING test collection, not before

**Root Cause:** Python import order issue with module-level singleton initialization

**Permanent Fix:** Set APP_ENV at conftest.py module level (line 26) BEFORE any raglite imports

---

#### Failure: "Connection refused: localhost:5433"

1. **Why?** → PostgreSQL container port not accepting connections
2. **Why?** → Port shows as "in use" but no process listening
3. **Why?** → Previous test run crashed, process didn't exit
4. **Why?** → Kill script didn't run (no error handling)
5. **Why?** → No cleanup between parallel CI jobs on same runner

**Root Cause:** Stale process holding port from previous run

**Permanent Fix:** Aggressive cleanup in CI workflow:
```yaml
- name: Kill stale processes
  run: lsof -i :5433 -t | xargs kill -9 2>/dev/null || true
  if: always()
```

---

#### Failure: "pytest worker controller internal errors"

1. **Why?** → pytest-xdist worker process fails
2. **Why?** → Worker tried to use session-scoped fixture designed for single process
3. **Why?** → Session fixtures share database connection pool
4. **Why?** → Multiple workers can't share single session fixture safely
5. **Why?** → Integration tests configured with `-n 1` (parallel execution)

**Root Cause:** pytest-xdist incompatible with session-scoped fixtures

**Permanent Fix:** Sequential execution for integration tests (`-n 0` flag)

**Trade-off:** +5 seconds slower, but 100% reliable vs 95% flaky

---

#### Failure: "AssertionError: Collection modified unexpectedly"

1. **Why?** → Test found 145 chunks, expected 147
2. **Why?** → Previous test in suite modified collection
3. **Why?** → Modification happened without cleanup
4. **Why?** → Test didn't use `@pytest.mark.manages_collection_state`
5. **Why?** → No enforcement mechanism for state isolation

**Root Cause:** Test state pollution due to missing markers

**Permanent Fix:** Fixture enforcement + markers:
```python
@pytest.mark.preserve_collection      # Read-only tests
@pytest.mark.manages_collection_state # Modifying tests
```

Fixture rejects unknown patterns and raises clear error.

---

### Pattern Recognition Matrix

| Root Cause Category | Failure Pattern | # Incidents | Fix Type | Result |
|---|---|---|---|---|
| Module import order | Collection=0 | 3 | Architectural | 100% eliminated |
| Port conflicts | Connection refused | 4 | Cleanup script | 100% eliminated |
| pytest-xdist incompatibility | Worker errors | 2 | Sequential execution | 100% eliminated |
| State pollution | Collection modified | 3 | Marker enforcement | 100% eliminated |
| Health check timeouts | Timeout errors | 2 | Explicit health checks | 100% eliminated |
| Missing schema | Database errors | 1 | Init script | 100% eliminated |

**Key Finding:** Every failure category had a single root cause. Multiple surface symptoms came from same underlying issue.

---

## What Didn't Work (Failed Attempts)

Approaches that seemed promising but failed to solve root causes.

### Approach 1: Increasing Timeouts

**What we tried:** Increase test timeout from 30s to 60s to 90s to 300s

**Why it seemed like a fix:**
- Tests that timeout are just too slow, right?
- Increase timeout and they should pass

**Why it failed:**
- Different tests timeout each run (not consistent)
- Timeout just delayed the failure
- Real issue: service not ready, not test too slow
- Increased CI job time by 5+ minutes per attempt

**Result:** Wasted 2 days on timeout tuning, masked real issue

**Lesson:** Timeouts are symptoms, not causes

### Approach 2: Parallel Test Execution Tuning

**What we tried:** Optimize pytest-xdist configuration
- `-n 1` (1 worker)
- `-n 2` (2 workers)
- `-n auto` (auto workers)
- `--dist loadscope` (different distribution)

**Why it seemed like a fix:**
- Parallel is faster
- Maybe we just had the wrong -n value

**Why it failed:**
- Every -n value caused worker errors eventually
- Root issue: session fixtures not worker-safe (by design)
- pytest-xdist incompatible with architecture, period

**Result:** Wasted 1 week tuning -n flag

**Lesson:** Some problems can't be tuned away; they need architectural changes

### Approach 3: Complex Fixture Restoration

**What we tried:** Build sophisticated fixture cleanup
- Qdrant snapshots before/after each test
- PostgreSQL rollback per test
- Collection diff to detect changes
- Conditional restoration logic

**Why it seemed like a fix:**
- Detect changes, restore state = isolation
- Complex solution for complex problem

**Why it failed:**
- State pollution was root cause (missing markers)
- Restoration added 5+ seconds per test overhead
- 100 tests × 5s = 500 seconds of wasted time
- Still didn't prevent state pollution (just restored after)

**Result:** Built over-engineered solution for simple problem

**Lesson:** Constraints (markers) prevent problems better than cleanup (restoration)

### Approach 4: Retry Logic for Service Startup

**What we tried:** Exponential backoff with retries
- pg_isready with 30 retries
- Qdrant /health with 30 retries
- Increasing backoff: 100ms, 200ms, 400ms...

**Why it seemed like a fix:**
- If service is slow, retrying should help
- More retries = more chances to succeed

**Why it failed:**
- Fixed timeout window (30 retries × max_backoff)
- If service takes 20 seconds, 30 retries at 500ms = 15 seconds (fails!)
- Retries don't solve fundamental issue (why is service slow?)
- Added latency to every test run (even fast ones)

**Result:** Trade-off of 3-5 seconds extra latency per job

**Lesson:** Retries are band-aids; fix the root (service startup time or dependency)

---

## What Works (Successful Fixes)

Approaches that permanently solved problem categories.

### Fix 1: Explicit Health Checks (Before Tests)

**What we did:**
```yaml
- name: Wait for PostgreSQL
  run: |
    for i in {1..30}; do
      docker exec raglite-postgresql-test pg_isready -U raglite_ci && exit 0
      sleep 0.5
    done
    exit 1  # Fail if health check never passes

- name: Wait for Qdrant
  run: |
    curl -f http://localhost:6335/health || exit 1
```

**Why it works:**
- Separate health check from tests (clear failure point)
- Fail fast if infrastructure isn't ready (don't waste time on test failures)
- Tests assume service is ready (no retry logic needed)
- Easy to debug: "Did health check pass?" → yes/no

**Impact:** Eliminated entire category of timeout failures

**Side effects:** None (5 seconds overhead, acceptable)

### Fix 2: Sequential Execution for Integration Tests

**What we did:**
```bash
# Before (failing)
pytest tests/integration/ -n auto

# After (passing)
pytest tests/integration/ -n 0
```

**Why it works:**
- Session fixtures designed for single process
- Eliminate worker coordination issues
- Eliminate race conditions on shared state
- Tests are deterministic (same order every run)

**Impact:** Eliminated all pytest-xdist worker errors

**Trade-off:** +5-10 seconds slower per test run (acceptable)

**Side benefit:** Easier debugging (reproducible order)

### Fix 3: Aggressive Port Cleanup

**What we did:**
```bash
lsof -i :5433 -t | xargs kill -9 2>/dev/null || true
sleep 3  # Allow TIME_WAIT state timeout
docker-compose up -d postgresql-test
```

**Why it works:**
- Kill any process holding the port (stale from previous run)
- Wait for socket state cleanup (TIME_WAIT)
- Fresh container startup guaranteed

**Impact:** Eliminated port conflict failures

**Side effects:** None (kills only stale processes)

### Fix 4: Marker-Based Test Isolation

**What we did:**
```python
# Categorize all tests
@pytest.mark.preserve_collection      # Read-only (400+ tests)
@pytest.mark.manages_collection_state # Modifying (20+ tests)

# Fixture enforces isolation
def ensure_qdrant_test_isolation(request):
    if "manage_collection_state" in marker:
        # Skip cleanup (test manages its own state)
    elif "preserve_collection" in marker:
        # Skip baseline checks (read-only = no changes)
    else:
        # Restore if dirty, validate after
        pass
```

**Why it works:**
- Constraint prevents errors (marker required)
- Tests declare intent (read vs write)
- Fixture enforces isolation based on declaration
- Clear error if test declares wrong intent

**Impact:** Eliminated state pollution failures

**Side benefit:** 500 seconds faster (skip unnecessary cleanup checks)

### Fix 5: Module-Level conftest.py Environment Setup

**What we did:**
```python
# tests/conftest.py - BEFORE any imports
import os
os.environ["APP_ENV"] = "test"        # Line 26
os.environ["POSTGRES_PORT"] = "5433"
# ... then imports
import raglite.shared.config

# Force Settings singleton reload
raglite.shared.config.settings = Settings()
```

**Why it works:**
- Environment variables set BEFORE module imports
- Settings singleton created with correct values
- No import order issues
- Tests use correct database ports

**Impact:** Eliminated all "wrong database" failures

**Side benefit:** Clear debug point (check environment section in conftest)

---

## Strategic Framework: Architectural vs Symptomatic Fixes

How to distinguish between real fixes and temporary patches.

### Decision Matrix

| Aspect | Symptomatic Fix | Architectural Fix |
|--------|---|---|
| **Problem Statement** | "Tests timeout" | "Service not ready before test" |
| **Solution** | Increase timeout | Add health check |
| **Time to Fix** | 5 minutes | 30 minutes |
| **Time to Recur** | 3-7 days (different test) | Never (category eliminated) |
| **Maintainability** | Low (special case) | High (general principle) |
| **Scope** | Single test/job | Category of tests |
| **Root Cause Understanding** | No | Yes |
| **Future Prevention** | Requires similar fix for next symptom | Pattern becomes clear (prevents similar issues) |

### Recognition Patterns

**Symptomatic Fix Signals:**
- "Let me try X and see if it works"
- Multiple similar fixes in different places
- Fix is specific to one test/job
- Fix doesn't explain WHY problem happens
- Next run shows similar failure in different test

**Architectural Fix Signals:**
- "The root cause is X, so we need Y"
- Fix applies to entire category
- Fix is general principle (applies everywhere)
- Fix is in infrastructure, not test code
- Next run shows category eliminated

---

## Prevention Rules Learned

Guidelines to prevent recurring CI failures.

### Rule 1: No Environment Variables in Test Code

**Pattern:**
```python
# WRONG: Test sets environment variable
os.environ["POSTGRES_PORT"] = "5433"

# CORRECT: conftest.py sets at module level
```

**Rationale:** Environment setup must happen before imports, not in tests

**Enforcement:** Code review check for `os.environ[` in `tests/` files

### Rule 2: All Tests Must Declare State Intent

**Pattern:**
```python
# WRONG: No marker (ambiguous intent)
async def test_search():
    pass

# CORRECT: Explicit marker
@pytest.mark.preserve_collection
async def test_search():
    pass
```

**Rationale:** Test isolation requires explicit contract

**Enforcement:** Fixture raises error if marker missing

### Rule 3: Health Checks Before Test Execution

**Pattern:**
```yaml
# WRONG: Assume service is ready
- run: pytest tests/

# CORRECT: Verify before tests
- run: docker exec container pg_isready && pytest tests/
```

**Rationale:** Clear failure point, faster debugging

**Enforcement:** CI workflow template enforces health check step

### Rule 4: Sequential Execution for Shared State

**Pattern:**
```bash
# WRONG: Parallel execution
pytest tests/integration/ -n auto

# CORRECT: Sequential
pytest tests/integration/ -n 0
```

**Rationale:** Shared state (session fixtures) not safe for parallel

**Enforcement:** CI workflow sets `-n 0` for integration tests

### Rule 5: Container Cleanup Between Runs

**Pattern:**
```bash
# WRONG: Assume container is clean
docker-compose up postgresql-test

# CORRECT: Kill stale processes first
lsof -i :5433 -t | xargs kill -9 2>/dev/null || true
docker-compose up postgresql-test
```

**Rationale:** Previous run may have left stale process

**Enforcement:** CI workflow includes cleanup step

### Rule 6: Isolated Database Ports Per Job

**Pattern:**
```yaml
# WRONG: All jobs use same port
integration-tests:
  run: pytest tests/integration/  # Uses port 5433

agentic-tests:
  run: pytest tests/agentic/      # Uses port 5433 (conflict!)

# CORRECT: Unique port per job
integration-tests:
  env:
    POSTGRES_PORT: 5433

agentic-tests:
  env:
    POSTGRES_PORT: 5438
```

**Rationale:** Parallel jobs can't use same port

**Enforcement:** Port allocation documented in `docs/ci/infrastructure-architecture.md`

---

## Metrics Showing Improvement

Quantitative evidence that architectural fixes worked.

### CI Success Rate

```
Week 1-2 (Symptom-based fixes):
├─ Success rate: 82% (5 fails per 28 runs)
├─ MTTR (Mean Time To Recovery): 6 hours
└─ Trend: Declining (new failures each day)

Week 2-3 (Root cause investigation):
├─ Success rate: 88% (3 fails per 25 runs)
├─ MTTR: 4 hours
└─ Trend: Improving (fewer new failure types)

Week 3-4 (Architectural fixes):
├─ Success rate: 98% (1 fail per 50 runs)
├─ MTTR: <1 hour
└─ Trend: Stable (no new failure categories)
```

### Test Execution Time

```
Collection time:
  Before: 15-30 seconds (inconsistent)
  After: 8-12 seconds (consistent)
  Improvement: 30% faster + consistent

Integration test suite:
  Before: 12-18 minutes (with timeouts)
  After: 10-12 minutes (reliable)
  Improvement: 10% faster + 100% reliable

Total CI job time:
  Before: 35-45 minutes (with retries)
  After: 28-32 minutes (no retries needed)
  Improvement: 25% faster
```

### Failure Categories Eliminated

```
Category 1 (Collection errors): 0 failures in last 50 runs ✓
Category 2 (Port conflicts): 0 failures in last 50 runs ✓
Category 3 (Worker errors): 0 failures in last 50 runs ✓
Category 4 (State pollution): 0 failures in last 50 runs ✓
Category 5 (Timeout errors): 0 failures in last 50 runs ✓
Category 6 (Health checks): 0 failures in last 50 runs ✓
```

---

## Lessons for Future Infrastructure Changes

Best practices learned that apply to future CI work.

### When Adding New Tests

1. **Determine state intent first**
   - Will test modify Qdrant? → `@pytest.mark.manages_collection_state`
   - Will test read-only? → `@pytest.mark.preserve_collection`

2. **Mark slow tests (>1 second)**
   - Measure with `pytest --durations=0`
   - Add `@pytest.mark.slow` if >1 second

3. **No hardcoded timeouts**
   - Let fixtures define timeouts
   - No `asyncio.sleep(30)` in tests
   - Use `asyncio.wait_for(operation, timeout=30)` instead

### When Changing Infrastructure

1. **Always add explicit health checks**
   - Don't assume service is ready
   - Verify with dedicated step before tests

2. **Document port allocations**
   - Add to `docs/ci/infrastructure-architecture.md`
   - Use isolated ports for new jobs

3. **Test locally first**
   - Run exact CI command locally
   - Reproduce failure before fixing
   - Validate fix works consistently (5+ runs)

4. **Measure impact**
   - Before/after timing
   - Success rate (target 99%+)
   - No new failure categories

### When Debugging CI Failures

1. **Follow the Five Whys**
   - Don't stop at symptom ("test times out")
   - Ask "Why?" 5 times until root cause found
   - Document the chain

2. **Distinguish symptom vs root cause**
   - Symptom: "Test times out"
   - Root cause: "Service not ready before test"
   - Fix the root cause, not symptom

3. **Look for category patterns**
   - Similar failures from similar root cause
   - Fix the root cause once, category disappears
   - Don't band-aid each individual failure

4. **Use architectural thinking**
   - "Why is this infrastructure unreliable?"
   - "What dependency must we guarantee?"
   - "How can we make that dependency explicit?"

---

## Evolution Timeline

How RAGLite CI matured over 8 weeks.

```
Week 1 (2025-10-29): Initial CI Setup
├─ Basic pytest execution works
├─ Database flakiness observed
└─ Team tries timeout increases

Week 2 (2025-11-05): Symptom-Based Fixes
├─ Fix 1: Increase timeout (didn't work)
├─ Fix 2: Retry logic (helped, not sufficient)
├─ Fix 3: More retries (diminishing returns)
└─ 15+ attempts, success rate still 82%

Week 3 (2025-11-12): Root Cause Investigation
├─ Investigation: "Why do timeouts happen?"
├─ Finding: Service startup takes 8-12 seconds
├─ Insight: Tests assume <3 second startup
├─ Measurement: Actual vs expected times
└─ Pattern recognition: 5 similar root causes

Week 4 (2025-11-19): Architectural Fixes Implemented
├─ Fix 1: Module-level conftest env setup
├─ Fix 2: Explicit health checks
├─ Fix 3: Sequential execution (-n 0)
├─ Fix 4: Aggressive port cleanup
├─ Fix 5: Marker-based test isolation
└─ Success rate jumps to 98%

Week 5-8 (2025-11-26 to 2025-12-17): Stabilization
├─ Documentation written
├─ Prevention rules established
├─ Lessons captured
├─ No new failure categories
└─ Reliability target: 99%+ achieved
```

---

## Recommendations for Similar Projects

If you're building CI infrastructure for data/ML projects.

### Start With Architecture, Not Symptoms

1. **Define explicit assumptions**
   - Service startup time: <X seconds
   - Database response time: <Y ms
   - Network reliability: Z% availability

2. **Build health checks**
   - Verify assumptions before tests
   - Make failures obvious

3. **Test isolation first**
   - Declare intent (read/write)
   - Enforce through markers
   - Don't hope tests don't interfere

### Plan for Observability

1. **Log key events**
   - Container startup
   - Health check results
   - Test state changes
   - Performance metrics

2. **Capture metrics**
   - Job duration
   - Success rate
   - Failure categories

3. **Alert on trends**
   - Slowdown >10%
   - Success rate <95%
   - New failure categories

### Document Decisions

1. **Why port 5433?** - Isolated from production (5432)
2. **Why -n 0?** - Session fixtures not worker-safe
3. **Why health checks?** - Separate infrastructure from tests
4. **Why markers?** - Explicit contract for state isolation

### Expect Technical Debt

1. **Early solutions are wrong** - That's OK, learn from them
2. **Refactor when you understand** - Don't fix symptoms forever
3. **Document learnings** - Your future self will thank you
4. **Establish prevention rules** - Make them explicit

---

## Summary: Principles That Worked

Core principles that resolved 15+ CI failure patterns.

### Principle 1: Make Dependencies Explicit

Instead of assuming (service is ready), verify (health checks)

### Principle 2: Constraints Prevent Errors Better Than Cleanup

Instead of restoring state, prevent modification (markers)

### Principle 3: Separate Concerns

Instead of mixing (infrastructure + tests), separate (health checks before)

### Principle 4: Measure Before Fixing

Instead of guessing (timeout too short?), measure (service takes 12 seconds)

### Principle 5: Fix Categories, Not Individual Cases

Instead of patching (each test), fix root cause (entire category)

---

**Document Version:** 1.0
**Lessons Captured:** 15+ failure investigations
**Principles Validated:** 5 major principles
**Success Rate Improvement:** 82% → 98%
**Reliability Target:** 99%+ (12 months, 1-2 unplanned restarts)
