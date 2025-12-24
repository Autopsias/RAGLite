# CI Documentation Hub

Comprehensive reference for RAGLite CI/CD infrastructure, troubleshooting, and lessons learned.

**Last Updated:** 2025-12-24
**Coverage:** 12 failure categories, 15+ root causes, 99%+ reliability target
**Audience:** Developers, DevOps engineers, new team members

---

## Quick Navigation

### For Urgent Issues (CI is Failing)

Start here to diagnose and fix CI failures:

**File:** [`troubleshooting-runbook.md`](./troubleshooting-runbook.md)

- Quick reference table of common failures
- 12 failure categories with root cause analysis
- Step-by-step diagnosis procedures
- Copy-paste ready commands
- Prevention strategies

**Typical usage time:** 5-30 minutes to resolve

---

### For Understanding CI Architecture

Learn how RAGLite CI is designed and why:

**File:** [`infrastructure-architecture.md`](./infrastructure-architecture.md)

- Container naming conventions
- Port allocation strategy
- Health check mechanisms
- CI job dependency graph
- Service lifecycle timeline
- Disaster recovery procedures
- Future improvements

**Typical usage:** Architecture review, planning changes, capacity planning

---

### For Learning Why CI Failures Happen

Understand the root causes and principles that resolved them:

**File:** [`lessons-learned.md`](./lessons-learned.md)

- Root cause analysis (Five Whys) for 15+ fixes
- What didn't work (failed approaches)
- What works (successful solutions)
- Strategic framework (architectural vs symptomatic fixes)
- Prevention rules
- Metrics and improvement timeline
- Principles for future infrastructure work

**Typical usage:** Code review, architectural decisions, preventing regression

---

## Problem Resolution Flowchart

```
CI test fails?
  │
  ├─ "Don't know what's wrong"
  │  └─ Start: troubleshooting-runbook.md (Quick Reference Table)
  │
  ├─ "Know the error, need to fix it"
  │  └─ Go to: troubleshooting-runbook.md (Find Category N)
  │     └─ Follow: Step-by-step solution in category
  │
  ├─ "Failure keeps recurring"
  │  └─ Go to: lessons-learned.md (Root Cause Analysis)
  │     └─ Apply: Prevention rules from that section
  │
  ├─ "Planning CI changes"
  │  └─ Go to: infrastructure-architecture.md
  │     └─ Review: Relevant section (ports, containers, health checks)
  │
  └─ "Need to explain CI to new person"
     └─ Start: infrastructure-architecture.md (Executive Summary)
        └─ Then: lessons-learned.md (Principles)
```

---

## Document Map

### troubleshooting-runbook.md (50 KB, 1,200 lines)

**Purpose:** Quick diagnosis and resolution for CI failures

**Structure:**
- Quick Reference Table (13 common failures)
- 12 Failure Categories:
  1. Test Collection Failures
  2. Port Conflicts and Connection Failures
  3. Service Startup and Health Checks
  4. Docker Socket and Daemon Issues
  5. Database Configuration and Credentials
  6. Worker Controller and pytest-xdist Failures
  7. Environment Variable and Configuration Issues
  8. Async Timeouts and Slow Operations
  9. Test State Pollution and Collection Modification
  10. Import Errors and Dependency Issues
  11. Container Lifecycle and Auto-Restart
  12. Performance Regression and Timeout Issues
- Diagnostic Script
- Common Resolution Paths
- Support and Escalation

**When to use:**
- CI job just failed
- Need to resolve within 30 minutes
- Don't have time for theory, just fix it

**Key sections:**
- Each category has: Symptoms, Root Cause Analysis, Solution (multi-step), Prevention
- Quick Reference Table at top for instant lookup

---

### infrastructure-architecture.md (45 KB, 1,000 lines)

**Purpose:** Reference for CI system design, components, and interactions

**Structure:**
- Executive Summary
- Container Naming Convention (production + test + job-specific)
- Port Allocation Strategy (5432-5438 PostgreSQL, 6333-6339 Qdrant)
- Health Check Mechanisms (PostgreSQL pg_isready, Qdrant /health)
- CI Job Dependency Graph (with timing targets)
- Service Lifecycle Timeline (startup sequence in detail)
- Environment Variable Configuration (flow diagram)
- Database Schema and Initialization
- Container Resource Limits (memory, CPU)
- Cleanup and Teardown
- Concurrent Execution Model
- pytest Configuration
- Debugging and Observability
- Architecture Decisions and Rationale
- Future Improvements
- Disaster Recovery

**When to use:**
- Planning changes to CI infrastructure
- Understanding why something is designed a certain way
- Explaining CI to new team members
- Capacity planning or resource optimization

**Key sections:**
- Container naming (understand container → job mapping)
- Port allocation (plan new jobs/workflows)
- Dependency graph (understand execution order)
- Health checks (understand uptime guarantees)

---

### lessons-learned.md (40 KB, 900 lines)

**Purpose:** Strategic insights from 15+ CI fixes; principles that work

**Structure:**
- Executive Summary (Three Phases of CI Maturity)
- Root Cause Analysis Summary (Five Whys for each major category)
- What Didn't Work (4 failed approaches)
- What Works (5 successful fixes with rationale)
- Strategic Framework (Architectural vs Symptomatic fixes decision matrix)
- Prevention Rules (6 rules derived from failures)
- Metrics Showing Improvement (Success rate, timing, category elimination)
- Lessons for Future Infrastructure Changes
- Evolution Timeline (8-week journey)
- Recommendations for Similar Projects
- Summary: Principles That Worked

**When to use:**
- Reviewing code/architecture decisions
- Planning improvements to CI
- Training new engineers on principles
- Preventing similar failures in future

**Key sections:**
- "What Didn't Work" (avoid repeating mistakes)
- "Prevention Rules" (apply these consistently)
- "Strategic Framework" (distinguish symptom vs root cause)
- "Metrics" (see impact of architectural fixes)

---

## Key Metrics

### Current CI Reliability

| Metric | Before Fixes | After Fixes | Target |
|--------|---|---|---|
| Success Rate | 82% | 98% | 99%+ |
| MTTR | 6 hours | <1 hour | <30 min |
| Failure Categories | 12+ | 0 (eliminated) | 0 |
| Collection Time | 15-30s | 8-12s | <10s |
| Integration Test Suite | 12-18m | 10-12m | <15m |
| Total CI Job | 35-45m | 28-32m | <30m |

---

## Common Scenarios

### Scenario 1: "Tests aren't running, 0 collected"

**Start with:** `troubleshooting-runbook.md` → Category 1 (Test Collection Failures)

**Steps:**
1. Check container status
2. Verify environment variables
3. Test container health
4. Manual collection test
5. Check conftest import

**Typical resolution:** 10 minutes

---

### Scenario 2: "Connection refused error"

**Start with:** `troubleshooting-runbook.md` → Category 2 (Port Conflicts)

**Steps:**
1. Kill stale process
2. Remove stale container
3. Verify port cleanup
4. Restart fresh container

**Typical resolution:** 5 minutes

---

### Scenario 3: "asyncio.TimeoutError in tests"

**Start with:** `troubleshooting-runbook.md` → Category 8 (Async Timeouts)

**Steps:**
1. Identify slow operation
2. Check fixture timeout
3. Measure actual duration
4. Adjust timeout or mark as slow

**Typical resolution:** 15 minutes

---

### Scenario 4: "Same test fails intermittently"

**Start with:** `lessons-learned.md` → Prevention Rules

**Analysis:**
1. Is it truly intermittent? (Measure 5+ runs)
2. Check if symptom vs root cause issue
3. Apply architectural fix (not timeout increase)

**Typical resolution:** 30+ minutes (investigation required)

---

### Scenario 5: "Planning new CI job/workflow"

**Start with:** `infrastructure-architecture.md`

**Review:**
1. Port allocation strategy (choose unique port)
2. Container naming convention (follow pattern)
3. Health check mechanisms (implement before tests)
4. Job dependency graph (understand timing)

**Typical time:** 30 minutes (design) + implementation

---

## References and Cross-Links

### Within Documentation

| Topic | File | Section |
|-------|------|---------|
| Container naming | architecture | Container Naming Convention |
| Port allocation | architecture | Port Allocation Strategy |
| Health checks | architecture | Health Check Mechanisms |
| Test markers | troubleshooting | Category 9 (State Pollution) |
| pytest-xdist | troubleshooting | Category 6 (Worker Controller) |
| Environment setup | troubleshooting | Category 7 (Environment Variables) |
| Database config | troubleshooting | Category 5 (Database Configuration) |

### External References

- **pytest documentation:** https://docs.pytest.org/
- **Docker Compose:** https://docs.docker.com/compose/
- **GitHub Actions:** https://docs.github.com/en/actions
- **PostgreSQL documentation:** https://www.postgresql.org/docs/
- **Qdrant documentation:** https://qdrant.tech/documentation/

### Related Project Documentation

- **RAGLite Architecture:** `/docs/architecture/`
- **Test Guidelines:** `/tests/CLAUDE.md`
- **Database Safety:** `.claude/rules/database-safety.md`
- **Testing Rules:** `.claude/rules/testing.md`

---

## Contributing to CI Documentation

When you fix a CI issue:

1. **Check if pattern exists**
   - Is it in troubleshooting-runbook.md?
   - Is root cause in lessons-learned.md?

2. **If new pattern:**
   - Document root cause analysis (Five Whys)
   - Add to appropriate troubleshooting category
   - Extract prevention rule

3. **If existing pattern:**
   - Update metrics (success rate, timing)
   - Add new example if different
   - Note if conditions changed

4. **Update this file**
   - Update metrics if they changed
   - Add new scenario if appropriate
   - Note date of change

---

## Maintenance Schedule

| Task | Frequency | Owner | Location |
|------|-----------|-------|----------|
| Review CI metrics | Weekly | DevOps | GitHub Actions dashboard |
| Update success rate | Weekly | DevOps | metrics table above |
| Investigate new failures | As-needed | On-call | troubleshooting-runbook |
| Extract lessons learned | Monthly | Architecture | lessons-learned.md |
| Validate prevention rules | Quarterly | Team | code review checklist |
| Update infrastructure docs | Quarterly | Architecture | infrastructure-architecture.md |

---

## Quick Commands

### Diagnostics

```bash
# Run diagnostics script
./scripts/ci-diagnostics.sh

# Check container status
docker ps -a --filter "name=raglite" --format "table {{.Names}}\t{{.Status}}"

# Check health
docker exec raglite-postgresql-test pg_isready -U raglite_ci
curl -s http://localhost:6335/health | jq .

# Collect test metrics
uv run pytest tests/ --durations=20 -v
```

### Common Fixes

```bash
# Kill stale processes
lsof -i :5433 -t | xargs kill -9 2>/dev/null || true

# Restart containers
docker-compose down -v && docker-compose up -d postgresql-test qdrant-test

# Initialize database
APP_ENV=test uv run python scripts/init-test-postgresql.py

# Run tests locally (same as CI)
export APP_ENV=test
uv run pytest tests/ -v -m "not slow"
```

---

## Support

### Getting Help

1. **Quick issue:** Check Quick Reference Table in troubleshooting-runbook.md
2. **Specific failure:** Find category in troubleshooting-runbook.md
3. **Understanding why:** Read relevant section in lessons-learned.md
4. **Planning changes:** Review infrastructure-architecture.md
5. **Still stuck:** See "Escalation" section in troubleshooting-runbook.md

### Reporting Issues

When reporting a CI issue:

1. Include error message (exact output)
2. Include workflow that failed (which .yml file)
3. Include recent commits (what changed?)
4. Include container status (`docker ps -a`)
5. Reference relevant troubleshooting category

---

## Document Versions

| File | Version | Last Updated | Status |
|------|---------|--------------|--------|
| troubleshooting-runbook.md | 1.0 | 2025-12-24 | Stable |
| infrastructure-architecture.md | 1.0 | 2025-12-24 | Stable |
| lessons-learned.md | 1.0 | 2025-12-24 | Stable |
| README.md (this file) | 1.0 | 2025-12-24 | Stable |

---

**Documentation Hub Version:** 1.0
**Coverage:** 12 failure categories, 15+ root causes, 99%+ reliability
**Last Validation:** 2025-12-24
**Next Review:** 2025-01-24 (quarterly)
