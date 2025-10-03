# RAGLite Documentation

**Version:** 1.1 (Simplified MVP-First Approach)
**Date:** October 3, 2025
**Status:** Ready for BMAD Sharding & Development

---

## 📁 Document Overview

This folder contains the **final, BMAD-ready documentation** for RAGLite.

### Core Documents (Use These)

| Document | Size | Purpose | BMAD Usage |
|----------|------|---------|------------|
| **architecture.md** | 188KB | ⭐ **PRIMARY** - Complete architecture specification | ✅ Shard this for agents |
| **prd.md** | 66KB | Product Requirements Document | ✅ Reference for features |
| **front-end-spec.md** | 36KB | MCP response format specification | ✅ Reference for UX |
| **phase1-mvp-checklist.md** | 9KB | Week-by-week MVP implementation guide | ✅ Daily implementation helper |
| **brief.md** | 48KB | Project brief (original) | ℹ️ Context/background |

---

## 🎯 Primary Document: architecture.md

**This is your single source of truth.** Everything you need for implementation is here.

### Structure

```
architecture.md (5,386 lines)
│
├─ PART 1: v1.1 MONOLITHIC MVP (Lines 1-607) ⭐ START HERE
│  ├─ 1. Introduction & Vision
│  ├─ 2. Executive Summary
│  ├─ 3. Repository Structure (exact file layout)
│  ├─ 4. Research Findings (validated technologies)
│  ├─ 5. Technology Stack (definitive choices)
│  ├─ 6. Reference Implementation (250+ lines of code)
│  ├─ 7. Data Layer (Qdrant, S3, Neo4j)
│  ├─ 8. Phased Implementation (Week 1-16)
│  └─ 9. Deployment (Docker Compose)
│
└─ PART 2: v1.0 MICROSERVICES REFERENCE (Lines 608+)
   └─ Future scaling guide (use in Phase 4 if needed)
```

### How to Use

**For MVP Development (Weeks 1-12):**
```
Read: architecture.md Part 1 (lines 1-607)
Copy: Section 6 - Reference Implementation
Follow: Section 8 - Phased Implementation
Helper: phase1-mvp-checklist.md (day-to-day tasks)
```

**For AI Agents (Claude Code):**
```
Primary: architecture.md
Patterns: Section 6 (reference code)
Standards: Section 6.2 (coding rules)
Structure: Section 3 (repository layout)
```

**For Future Scaling (Phase 4+):**
```
Read: architecture.md Part 2 (line 608+)
Reference: Microservices Architecture
Migration: Evolution Path sections
```

---

## 🔧 BMAD Sharding Guide

### Recommended Shards

When using BMAD to shard `architecture.md`, suggest these logical boundaries:

**Critical MVP Shards:**
1. `overview-and-vision.md` - Lines 1-100
2. `executive-summary-v1.1.md` - Lines 101-200
3. `repository-structure.md` - Lines 201-300
4. `research-findings.md` - Lines 301-400
5. `reference-implementation.md` - Lines 401-550 (⭐ most important)
6. `coding-standards.md` - Lines 551-600
7. `phased-implementation.md` - Lines 451-500

**Reference Shards (Phase 4+):**
8. `microservices-architecture.md` - Part 2 microservices sections
9. `deployment-aws.md` - Part 2 AWS deployment
10. `monitoring-observability.md` - Part 2 monitoring

### BMAD Command (Example)

```bash
# If you have BMAD CLI:
bmad shard architecture.md --output shards/ --auto

# Or specify sections:
bmad shard architecture.md \
  --sections "1-9" \
  --output mvp-shards/
```

---

## 📖 Reading Paths

### Path 1: Quick Start (30 minutes)

```
1. architecture.md → "How to Read This Document" (line 10)
2. architecture.md → Executive Summary (lines 100-200)
3. phase1-mvp-checklist.md → Week 1 tasks
4. START CODING
```

### Path 2: Deep Dive (2-3 hours)

```
1. architecture.md → Part 1: v1.1 Monolithic (lines 1-607)
2. architecture.md → Section 6: Reference Implementation
3. prd.md → Understand all requirements
4. front-end-spec.md → MCP response patterns
5. phase1-mvp-checklist.md → Implementation plan
```

### Path 3: Research Validation (1 hour)

```
1. architecture.md → Section 4: Research Findings
2. architecture.md → Section 5: Technology Stack
3. prd.md → Cross-check NFRs with architecture
```

---

## ✅ Validation Checklist

Before starting development, verify:

- [ ] Read architecture.md Part 1 (v1.1 Monolithic)
- [ ] Understand Section 6 (Reference Implementation)
- [ ] Review Section 6.2 (Coding Standards)
- [ ] Read phase1-mvp-checklist.md Week 1
- [ ] Have Claude Code / AI pair programmer ready
- [ ] Docker + Python 3.11+ installed
- [ ] CLAUDE_API_KEY environment variable set

---

## 🗂️ Archive Folder

The `archive/` folder contains **historical documents** from the architecture development process:
- Design exploration drafts
- Original v1.0 microservices backup
- Integration process artifacts

**You don't need these for development.** They're kept for historical context only.

See `archive/README.md` for details.

---

## 🚀 Getting Started

### Day 1: Setup

```bash
# 1. Read the architecture
cd docs
cat architecture.md | head -700  # Read Part 1: v1.1

# 2. Read the MVP checklist
cat phase1-mvp-checklist.md

# 3. Start project setup
cd ..
mkdir -p raglite/{ingestion,retrieval,shared,tests}
touch raglite/{main.py,config.py}
poetry init
```

### Week 1: Ingestion Pipeline

Follow:
1. `phase1-mvp-checklist.md` - Week 1 tasks
2. `architecture.md` Section 6 - Copy these patterns
3. `architecture.md` Section 8 - Week 1 deliverables

### Week 2-4: Complete MVP

Continue following the weekly breakdown in:
- `phase1-mvp-checklist.md` (day-to-day)
- `architecture.md` Section 8 (phase overview)

---

## 📞 Questions?

**For architecture decisions:**
→ Read `architecture.md` Part 1

**For implementation patterns:**
→ Read `architecture.md` Section 6

**For daily tasks:**
→ Read `phase1-mvp-checklist.md`

**For product requirements:**
→ Read `prd.md`

**For MCP response format:**
→ Read `front-end-spec.md`

---

## 🎯 Success Criteria

**Week 4 Gate (MVP Success):**
- ✅ Can ingest 5 financial PDFs (≥4/5 succeed)
- ✅ 80%+ test queries useful (≥16/20)
- ✅ Query response <10 seconds (≥8/10)
- ✅ All answers cite sources (20/20)

**If met:** Proceed to Phase 3 (Forecasting/Insights)
**If not:** Analyze failures, improve, retry

---

*Ready to build? Start with `phase1-mvp-checklist.md` Week 1!* 🚀
