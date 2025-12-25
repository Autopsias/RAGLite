# CI Documentation Index

Quick reference to find the right document for your need.

---

## By Use Case

### "CI just failed, what do I do?"
→ **troubleshooting-runbook.md** - Find error in Quick Reference Table, follow solution

### "I need to understand CI architecture"
→ **infrastructure-architecture.md** - Container naming, ports, health checks, job dependencies

### "Why does this CI failure keep happening?"
→ **failure-patterns.md** - Root cause analysis + prevention rules for 6 major patterns

### "How do I prevent CI failures in code review?"
→ **prevention-rules.md** - 6 mandatory core rules + 21 specific derived rules + checklist

### "What should I know about CI strategy?"
→ **STRATEGY.md** - Memory architecture, decisions, optimization strategies, timeline

### "How has CI improved over time?"
→ **success-metrics.md** - Metrics (82%→98%), cost savings ($9.6k/month), team impact

### "What went wrong in the past?"
→ **lessons-learned.md** - Historical analysis, Five Whys for 15+ fixes, principles that work

### "Navigate all these docs"
→ **README.md** - Hub with document map, feature matrix, usage scenarios

---

## By Audience

### Developers
1. **Quick fix:** troubleshooting-runbook.md
2. **Understand:** failure-patterns.md
3. **Prevent:** prevention-rules.md (code review checklist)

### DevOps Engineers
1. **System design:** infrastructure-architecture.md
2. **Decisions:** STRATEGY.md
3. **Health:** success-metrics.md (weekly monitoring)

### Tech Leads / Architects
1. **Strategy:** STRATEGY.md
2. **Prevention:** prevention-rules.md (enforcement)
3. **Metrics:** success-metrics.md (ROI tracking)

### New Team Members
1. **Overview:** README.md
2. **Architecture:** infrastructure-architecture.md
3. **Principles:** lessons-learned.md

### Product / Leadership
1. **ROI:** success-metrics.md (cost savings, team velocity)
2. **Risk:** failure-patterns.md (what can go wrong)
3. **Timeline:** STRATEGY.md (implementation phases)

---

## By Problem Type

### Memory Issues (OOM, Exit 137)
- Pattern: failure-patterns.md → Pattern 1
- Prevention: prevention-rules.md → Memory Category (Rules 1.1-1.3)
- Strategy: STRATEGY.md → Memory Optimization Strategies

### Container Startup
- Pattern: failure-patterns.md → Pattern 2
- Prevention: prevention-rules.md → Container Startup Category (Rules 2.1-2.3)
- Architecture: infrastructure-architecture.md → Health Check Mechanisms

### Port Conflicts
- Pattern: failure-patterns.md → Pattern 3
- Prevention: prevention-rules.md → Port Conflict Category (Rules 3.1-3.3)
- Troubleshooting: troubleshooting-runbook.md → Category 2

### Parallel Execution
- Pattern: failure-patterns.md → Pattern 4
- Prevention: prevention-rules.md → Parallelization Category (Rules 4.1-4.2)
- Architecture: infrastructure-architecture.md → Concurrent Execution Model

### Timeouts
- Pattern: failure-patterns.md → Pattern 5
- Prevention: prevention-rules.md → Timeout Category (Rules 5.1-5.3)
- Troubleshooting: troubleshooting-runbook.md → Category 8

### Test Isolation
- Pattern: failure-patterns.md → Pattern 6
- Prevention: prevention-rules.md → Isolation Category (Rules 6.1-6.3)
- Troubleshooting: troubleshooting-runbook.md → Category 9

---

## By Document

### README.md
**Purpose:** Navigation hub and feature matrix
**Length:** ~490 lines
**Contains:**
- Quick navigation guide
- Problem resolution flowchart
- Document map with summaries
- Key metrics table
- Common scenarios
- Document versions
- Feature matrix

**Best for:** Getting oriented, finding where to look

---

### troubleshooting-runbook.md
**Purpose:** Quick reference for diagnosing and resolving failures
**Length:** ~1,200 lines
**Contains:**
- Quick Reference Table (13 failures)
- 12 Failure Categories with solutions
- Diagnostic script
- Common resolution paths
- Support and escalation

**Best for:** "CI failed right now, need to fix it fast"

---

### infrastructure-architecture.md
**Purpose:** Reference for system design and component interactions
**Length:** ~1,000 lines
**Contains:**
- Container naming convention
- Port allocation strategy
- Health check mechanisms
- CI job dependency graph
- Service lifecycle timeline
- Resource limits
- Debugging and observability
- Architecture decisions
- Disaster recovery

**Best for:** Planning changes, understanding design decisions

---

### lessons-learned.md
**Purpose:** Strategic insights from 15+ CI fixes
**Length:** ~900 lines
**Contains:**
- Three phases of CI maturity
- Root cause analysis summaries (Five Whys)
- What didn't work (4 failed approaches)
- What works (5 successful fixes)
- Strategic framework
- Prevention rules (6 core)
- Metrics showing improvement
- Lessons for future infrastructure
- Evolution timeline

**Best for:** Understanding why things work, training new engineers

---

### STRATEGY.md
**Purpose:** CI/CD strategy with memory architecture focus
**Length:** ~584 lines
**Contains:**
- Executive summary
- CI architecture overview
- Root cause analysis (monolithic dependencies)
- 6 strategic decisions with rationale
- 6 core prevention rules
- Memory optimization strategies
- Implementation timeline (Phase 1-4)
- Dependency management
- Monitoring & metrics
- Long-term roadmap

**Best for:** Strategic planning, memory budgeting, dependency decisions

---

### failure-patterns.md
**Purpose:** Document specific failure patterns with solutions
**Length:** ~702 lines
**Contains:**
- Quick pattern lookup table
- Pattern 1: Memory OOM (Exit 137)
- Pattern 2: Empty Collection (Exit 1)
- Pattern 3: Port in Use (EADDRINUSE)
- Pattern 4: Worker Controller Errors
- Pattern 5: asyncio.TimeoutError
- Pattern 6: State Pollution
- Summary table
- Cross-references

**Each pattern includes:**
- Symptoms & error messages
- Root cause (Five Whys)
- Step-by-step solution
- 3-5 prevention rules
- Success metrics (before/after)

**Best for:** Understanding specific failure patterns, deep learning

---

### prevention-rules.md
**Purpose:** Comprehensive prevention rules and best practices
**Length:** ~754 lines
**Contains:**
- 6 Core Prevention Rules (mandatory)
  - Memory Budget Explicit
  - Health Checks Before Collection
  - Sequential Execution (Integration Tests)
  - Process Cleanup
  - Environment Isolation
  - Test Isolation & Cleanup

- Specific Prevention Rules by Category
  - Memory (3 rules)
  - Container Startup (3 rules)
  - Port Conflicts (3 rules)
  - Parallelization (2 rules)
  - Timeouts (3 rules)
  - Test Isolation (3 rules)

- Prevention Rules Checklist
- Quick reference by job type
- Impact analysis

**Best for:** Code review, implementation guidance, best practices

---

### success-metrics.md
**Purpose:** Track improvement metrics and demonstrate ROI
**Length:** ~568 lines
**Contains:**
- Executive summary (16 pp improvement)
- Success rate trends (82% → 98%)
- MTTR metrics (6h → <30min)
- Failure category elimination (12→0)
- Performance improvements (-30% duration)
- Prevention rule adoption
- Team productivity impact
- Cost analysis ($9.6k/month savings)
- Knowledge metrics
- Sustainability metrics
- Measurement methodology
- Historical timeline
- Lessons & recommendations

**Best for:** Status reporting, ROI justification, tracking improvement

---

## Quick Lookup Table

| Problem | Document | Section |
|---------|----------|---------|
| "I don't know what's wrong" | troubleshooting-runbook | Quick Reference Table |
| "CI ran out of memory" | failure-patterns | Pattern 1 |
| "0 tests collected" | failure-patterns | Pattern 2 |
| "Port already in use" | failure-patterns | Pattern 3 |
| "Worker controller error" | failure-patterns | Pattern 4 |
| "Test timeout" | failure-patterns | Pattern 5 |
| "Collection modified" | failure-patterns | Pattern 6 |
| "Why does this keep happening?" | STRATEGY | Root Cause Analysis |
| "How do I prevent this?" | prevention-rules | Core Rules or Specific Category |
| "What's changed?" | success-metrics | Historical Timeline |
| "How do I explain CI to someone?" | infrastructure-architecture | Executive Summary |
| "Where do I start?" | README | Quick Navigation |

---

## Reading Paths

### The "I'm Broken" Path (5-30 min)
1. Error message → troubleshooting-runbook.md Quick Reference
2. Find category → Follow solution steps
3. Still broken? → failure-patterns.md Pattern lookup
4. Understand pattern → Read Root Cause section
5. Prevent next time → Read Prevention Rules section

### The "I'm Learning" Path (2-3 hours)
1. Start → README.md (understand structure)
2. System → infrastructure-architecture.md (how it works)
3. Strategy → STRATEGY.md (why these decisions)
4. Failures → failure-patterns.md (what can go wrong)
5. Prevention → prevention-rules.md (how to avoid)
6. Results → success-metrics.md (it works!)

### The "I'm Reviewing Code" Path (10 min)
1. Grab → prevention-rules.md Prevention Rules Checklist
2. Check → Is memory budget declared?
3. Check → Are health checks present?
4. Check → Is execution sequential for integration?
5. Check → Is cleanup in first step?
6. Approve → If all core rules ✓

### The "I'm Planning Changes" Path (30 min)
1. Current state → STRATEGY.md (understand constraints)
2. Architecture → infrastructure-architecture.md (port allocation, containers)
3. Prevention → prevention-rules.md (rules for your job type)
4. Impact → success-metrics.md (how to track improvement)

### The "I'm New Here" Path (2-4 hours)
1. Welcome → README.md (get oriented)
2. Design → infrastructure-architecture.md (understand system)
3. History → lessons-learned.md (understand principles)
4. Patterns → failure-patterns.md (what to watch for)
5. Rules → prevention-rules.md (do's and don'ts)
6. Troubleshoot → troubleshooting-runbook.md (when things break)

---

## Cross-Reference Map

```
README.md (Start Here)
    ↓
    ├─→ troubleshooting-runbook.md (Quick Fixes)
    │   ├─→ failure-patterns.md (Understand Why)
    │   └─→ lessons-learned.md (Learn Principles)
    │
    ├─→ infrastructure-architecture.md (System Design)
    │   ├─→ STRATEGY.md (Strategic Decisions)
    │   └─→ prevention-rules.md (How to Implement)
    │
    ├─→ failure-patterns.md (Common Issues)
    │   ├─→ prevention-rules.md (How to Prevent)
    │   └─→ troubleshooting-runbook.md (Quick Fix)
    │
    ├─→ prevention-rules.md (Best Practices)
    │   ├─→ failure-patterns.md (Why These Rules)
    │   ├─→ STRATEGY.md (Strategic Alignment)
    │   └─→ success-metrics.md (Impact Proof)
    │
    ├─→ STRATEGY.md (Long-term Vision)
    │   ├─→ prevention-rules.md (Implementation)
    │   └─→ success-metrics.md (Success Tracking)
    │
    ├─→ success-metrics.md (Progress & ROI)
    │   ├─→ prevention-rules.md (How We Got Here)
    │   └─→ failure-patterns.md (What We Fixed)
    │
    └─→ lessons-learned.md (Wisdom)
        ├─→ prevention-rules.md (Specific Rules)
        └─→ STRATEGY.md (Strategic Insights)
```

---

## File Statistics

| Document | Type | Lines | Words | Code Examples | Tables |
|----------|------|-------|-------|---------------|--------|
| README.md | Navigation | 490 | 2,800 | 5 | 8 |
| troubleshooting-runbook.md | Reference | 1,200 | 8,500 | 25 | 15 |
| infrastructure-architecture.md | Design | 1,000 | 7,200 | 20 | 12 |
| lessons-learned.md | Strategy | 900 | 6,400 | 15 | 10 |
| STRATEGY.md | Strategy | 584 | 4,200 | 12 | 8 |
| failure-patterns.md | Reference | 702 | 5,100 | 30 | 6 |
| prevention-rules.md | Guidance | 754 | 5,500 | 35 | 8 |
| success-metrics.md | Metrics | 568 | 4,100 | 8 | 18 |
| **TOTAL** | | **6,198** | **43,800** | **150** | **85** |

---

## Document Update History

| Document | Created | Last Updated | Version |
|----------|---------|--------------|---------|
| README.md | 2025-12-24 | 2025-12-24 | 1.1 |
| troubleshooting-runbook.md | 2025-12-24 | 2025-12-24 | 1.0 |
| infrastructure-architecture.md | 2025-12-24 | 2025-12-24 | 1.0 |
| lessons-learned.md | 2025-12-24 | 2025-12-24 | 1.0 |
| STRATEGY.md | 2025-12-24 | 2025-12-24 | 1.0 |
| failure-patterns.md | 2025-12-24 | 2025-12-24 | 1.0 |
| prevention-rules.md | 2025-12-24 | 2025-12-24 | 1.0 |
| success-metrics.md | 2025-12-24 | 2025-12-24 | 1.0 |

---

**Index Version:** 1.0
**Last Updated:** 2025-12-24
**Total Documents Indexed:** 8
**Total Content:** 6,198 lines, ~44k words
**Coverage:** 100% of CI knowledge base
