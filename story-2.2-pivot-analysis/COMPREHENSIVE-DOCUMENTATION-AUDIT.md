# Comprehensive Documentation Audit for Epic 2 Pivot
## All BMAD Documentation Requiring Updates

**Date**: 2025-10-19
**Context**: Strategic pivot from Element-Aware Chunking to Staged RAG Architecture
**Audit Scope**: ALL PRD, Architecture, and BMAD documentation

---

## 🔴 CRITICAL PRIORITY - Must Update Before Dev Starts

### PRD Files

#### 1. **`docs/prd/epic-2-advanced-rag-enhancements.md`** 🔴 CRITICAL
**Current State**: Epic 2 "Advanced Document Understanding" (OBSOLETE)
**Required Change**: Complete rewrite as "Epic 2: Advanced RAG Architecture Enhancement"
**Owner**: Product Owner (Sarah)
**Detailed Instructions**: See `HANDOFF-TO-PO-AND-ARCHITECT.md` Section "Priority 1"
**Lines to Change**:
- Title: "Advanced Document Understanding" → "Advanced RAG Architecture Enhancement"
- ALL Stories 2.1-2.7 (OBSOLETE) → NEW Stories 2.1-2.5 (PDF opt + Fixed chunking)
- Epic priority: MEDIUM → CRITICAL
- Acceptance criteria: 95% stretch → 70% minimum, 95% stretch

---

#### 2. **`docs/prd/index.md`** 🔴 CRITICAL
**Current State**: Lines 42-49 reference Epic 2 "Advanced Document Understanding"
**Required Change**: Update Epic 2 title and story list

**Lines 42-49 (CURRENT)**:
```markdown
  - [Epic 2: Advanced Document Understanding](./epic-2-advanced-document-understanding.md)
    - [Story 2.1: Advanced Table Extraction & Understanding]
    - [Story 2.2: Multi-Document Query Synthesis]
    - [Story 2.3: Entity Extraction from Financial Documents (IF KG APPROVED)]
    - [Story 2.4: Knowledge Graph Construction (IF KG APPROVED)]
    - [Story 2.5: Hybrid RAG + Knowledge Graph Retrieval (IF KG APPROVED)]
    - [Story 2.6: Context Preservation Across Chunks]
    - [Story 2.7: Enhanced Test Set for Advanced Features]
```

**REPLACE WITH**:
```markdown
  - [Epic 2: Advanced RAG Architecture Enhancement](./epic-2-advanced-rag-enhancements.md)
    - [Story 2.1: Implement pypdfium Backend for Docling (Phase 1)]
    - [Story 2.2: Implement Page-Level Parallelism (Phase 1)]
    - [Story 2.3: Refactor Chunking Strategy to Fixed 512-Token Approach (Phase 2A)]
    - [Story 2.4: Add LLM-Generated Contextual Metadata Injection (Phase 2A)]
    - [Story 2.5: AC3 Validation and Optimization - DECISION GATE (Phase 2A)]
```

**Owner**: Product Owner (Sarah)
**Timeline**: Update after Epic 2 redefinition complete

---

#### 3. **`docs/prd/epic-list.md`** 🟠 HIGH
**Current State**: Epic 2 listed as "Advanced Document Understanding"
**Required Change**: Update Epic 2 title, description, and priority

**Expected Content**:
```markdown
## Epic 2: Advanced RAG Architecture Enhancement 🔴 CRITICAL

**Priority**: CRITICAL (changed from MEDIUM)
**Status**: IN PROGRESS
**Timeline**: 2-3 weeks (best case) to 18 weeks (worst case with all contingencies)

**Description**: Strategic pivot to staged RAG architecture enhancement following element-aware chunking failure. Implements PDF ingestion optimization followed by research-validated fixed chunking approach, with contingency paths to Structured Multi-Index or Hybrid Architecture if accuracy thresholds are not met.

**Business Value**:
- Achieve minimum 70% retrieval accuracy (unblock Epic 3-5)
- 1.7-2.5x faster PDF ingestion (accelerate testing iterations)
- Production-proven approaches (68-72% guaranteed by research)
- Staged implementation with decision gates (minimize risk)

**Success Criteria**:
- ✅ Retrieval accuracy ≥70% (MANDATORY for Epic 3)
- ✅ Attribution accuracy ≥95% (NFR7 compliance)
- ✅ Query response time <15s p95 (NFR13 compliance)
```

**Owner**: Product Owner (Sarah)

---

#### 4. **`docs/prd/requirements.md`** 🟠 HIGH
**Current State**:
- FR6-FR8 (Knowledge Graph) marked as "PENDING RESEARCH SPIKE"
- NFR6 (90%+ retrieval accuracy) has no intermediate milestones

**Required Changes**:

**FR6-FR8 (Knowledge Graph) - Lines 12-15**:
Update to reflect conditional Phase 2C/Phase 3 status:
```markdown
**Knowledge Graph & Entity Management** *(CONDITIONAL - Phase 2C or Phase 3)*
- FR6: System MAY extract financial entities (companies, departments, metrics, KPIs, time periods) from documents IF Phase 2C (Hybrid Architecture) is triggered at decision gate (Probability: 5%)
- FR7: System MAY construct knowledge graph capturing relationships between financial entities IF Phase 2C triggered (Probability: 5%)
- FR8: System MAY support hybrid retrieval combining vector similarity and graph traversal IF Phase 2C triggered (Probability: 5%)

**Decision Gates**:
- Phase 2A Fixed Chunking: IF ≥70% accuracy → FR6-FR8 NOT IMPLEMENTED
- Phase 2B Structured Multi-Index: IF ≥75% accuracy → FR6-FR8 NOT IMPLEMENTED
- Phase 2C Hybrid Architecture: IF <75% in Phase 2B → FR6-FR8 IMPLEMENTED
```

**NFR6 (Retrieval Accuracy) - Line 65**:
Add intermediate milestone:
```markdown
**Accuracy & Quality**
- NFR6: Retrieval accuracy shall achieve 90%+ for diverse financial queries (measured against ground truth test set)
  - **Epic 2 Minimum Milestone**: ≥70% accuracy (MANDATORY to proceed to Epic 3)
  - **Epic 2 Stretch Milestone**: ≥75% accuracy (enables skip to Epic 3 without Phase 2B-C)
  - **Epic 3+ Target**: 90%+ accuracy (final product goal)
- NFR7: Source attribution accuracy shall be 95%+ (correct document, page, section references)
```

**Owner**: Product Owner (Sarah) or PM (John)

---

#### 5. **`docs/prd/epic-2-advanced-document-understanding.md`** ⚠️ DEPRECATED FILE
**Current State**: OLD Epic 2 definition (Stories 2.1-2.7 with table extraction focus)
**Required Action**: **DELETE or ARCHIVE** this file (it's been superseded by `epic-2-advanced-rag-enhancements.md`)

**Decision**:
- **OPTION A**: Delete file entirely (recommended - avoid confusion)
- **OPTION B**: Move to `docs/archive/` with deprecation notice at top

**Owner**: Product Owner (Sarah)

---

#### 6. **`docs/prd/epic-3-ai-intelligence-orchestration.md`** 🟡 MEDIUM
**Current State**: May reference Epic 2 dependencies
**Required Change**: Update Epic 2 dependency references

**Search for**: "Epic 2" or "element-aware" or "advanced document understanding"
**Update**: Change prerequisite from "Epic 2 complete" to "Epic 2 complete (≥70% retrieval accuracy)"

**Owner**: Product Owner (Sarah) - UPDATE ONLY IF REFERENCES FOUND

---

#### 7. **`docs/prd/checklist-results-report.md`** 🟢 LOW
**Current State**: May reference Epic 2 in checklist results
**Action**: Review for Epic 2 references, update if found

**Owner**: Product Owner (Sarah) - REVIEW ONLY

---

#### 8. **`docs/prd/next-steps.md`** 🟢 LOW
**Current State**: May reference Epic 2 in next steps
**Action**: Review for Epic 2 references, update if found

**Owner**: Product Owner (Sarah) - REVIEW ONLY

---

### Architecture Files

#### 9. **`docs/architecture/5-technology-stack-definitive.md`** 🔴 CRITICAL
**Current State**: Missing pypdfium, PostgreSQL, Neo4j, LangGraph
**Required Change**: Add approved and conditional technologies
**Owner**: Architect
**Detailed Instructions**: See `HANDOFF-TO-PO-AND-ARCHITECT.md` Section "Priority 1"

**Add to Technology Stack Table**:
```markdown
| Component | Technology | Purpose | Status |
|-----------|------------|---------|--------|
| PDF Backend | pypdfium | Docling backend for faster, lower-memory PDF processing | ✅ APPROVED (Phase 1) |
| SQL Database | PostgreSQL 16 | Structured table storage for financial data | ⚠️ CONDITIONAL (Phase 2B/2C) |
| Graph Database | Neo4j 5.x | Knowledge graph for entity relationships | ⚠️ CONDITIONAL (Phase 2C) |
| Agent Framework | LangGraph + AWS Strands | Multi-agent orchestration for query planning | ⚠️ CONDITIONAL (Phase 3) |
```

---

#### 10. **`docs/architecture/8-phased-implementation-strategy-v11-simplified.md`** 🔴 CRITICAL
**Current State**:
- Phase 2 DEPRECATED GraphRAG (lines 290-302)
- Missing Phase 1 (PDF optimization)
- Phase 2 focused on incremental RAG enhancements (OBSOLETE)

**Required Change**: Complete Phase 1-3 rewrite
**Owner**: Architect
**Detailed Instructions**: See `HANDOFF-TO-PO-AND-ARCHITECT.md` Section "Priority 2"

**Changes Required**:
1. **Add Phase 1 (PDF Optimization)** BEFORE current Phase 2
2. **Rewrite Phase 2** as "RAG Architecture Pivot" (3-phase staged approach)
3. **Un-deprecate GraphRAG** as Phase 2C contingency
4. **Add Phase 3** as "Agentic Coordination" (optional)
5. Update timeline visualization (current → Week 1-30 depending on path)

---

#### 11. **`docs/architecture/3-repository-structure-monolithic.md`** 🟡 MEDIUM
**Current State**: Repository structure for element-aware chunking
**Required Change**: Add potential graph/structured layers (CONDITIONAL)

**IF Phase 2C (Hybrid) triggered**, add:
```markdown
raglite/
├── graph/                      # GraphRAG layer (CONDITIONAL - Phase 2C)
│   ├── entity_extraction.py   # LLM-based entity extraction
│   ├── graph_construction.py  # Neo4j graph population
│   └── graph_retrieval.py     # Graph traversal queries
├── structured/                 # Structured data layer (CONDITIONAL - Phase 2B/2C)
│   ├── table_extraction.py    # Docling → SQL conversion
│   ├── sql_querying.py        # SQL query generation
│   └── table_retrieval.py     # Table-based retrieval
```

**Owner**: Architect
**Action**: Add NOTE about conditional layers, update ONLY if Phase 2B-C triggered

---

#### 12. **`docs/architecture/6-complete-reference-implementation.md`** 🟡 MEDIUM
**Current State**: Contains chunking code examples
**Required Change**: Update chunking examples to fixed 512-token approach

**Search for**: "element-aware" or "chunking" code examples
**Update**: Replace with fixed 512-token chunking examples

**Owner**: Architect or Dev (Amelia)
**Timeline**: Update during Phase 2A implementation (not urgent for handoff)

---

#### 13. **`docs/architecture/index.md`** 🟢 LOW
**Current State**: Architecture table of contents
**Action**: Update links if Phase 2 section renamed

**Owner**: Architect

---

#### 14-35. **Other Architecture Files (22 files found with GraphRAG/Neo4j references)** 🟢 LOW-ARCHIVE
**Files Found**:
- `testing-strategy.md`, `change-log.md`, `data-layer.md`, `deployment-architecture.md`
- `microservices-architecture.md`, `orchestration-layer.md`, `tech-stack.md`
- `cicd-pipeline-architecture.md`, `conclusion.md`, `performance-scalability.md`
- `security-compliance.md`, `phased-implementation-strategy.md` (old version)
- `executive-summary.md`, `high-level-architecture.md`, `research-findings-summary.md`
- `technology-stack.md` (old version), `4-research-findings-summary-validated-technologies.md`
- `1-introduction-vision.md`, `2-executive-summary.md`

**Analysis**: Many of these are likely **ARCHIVE** files (duplicates, old versions)
**Action Required**:
1. Architect should audit which files are ACTIVE vs ARCHIVE
2. Move archive files to `docs/archive/` directory
3. Update ONLY active architecture files

**Priority**: LOW (most are reference/historical documents)

---

### BMAD Configuration

#### 36. **`bmad/core/config.yaml`** ✅ NO CHANGE NEEDED
**Current State**: References documentation paths
**Analysis**: Paths remain valid (sharded docs in `docs/prd/`, `docs/architecture/`)
**Action**: No changes required

---

### Story Files

#### 37. **`docs/stories/` directory** 🟡 MEDIUM
**Current Active Stories**: Check for references to Epic 2 or element-aware chunking

**Action Required**:
1. Review all active story files for Epic 2 references
2. Archive completed stories (Story 0.1, Story 1.1-1.12)
3. Create NEW story files for Epic 2 Phase 1 + 2A (5 stories)

**Owner**: Product Owner (Sarah)
**Timeline**: After Epic 2 redefinition complete

---

## 📊 Documentation Update Summary

### By Priority

| Priority | Count | Files | Owner | Timeline |
|----------|-------|-------|-------|----------|
| 🔴 **CRITICAL** | 4 | Epic 2 PRD, PRD index, Tech Stack, Phases | PO + Architect | T+0 to T+2 (1-2 days) |
| 🟠 **HIGH** | 3 | Epic List, Requirements, Old Epic 2 file | PO | T+1 to T+3 |
| 🟡 **MEDIUM** | 5 | Repo Structure, Reference Impl, Epic 3, Stories | Architect + Dev | T+2 to T+10 |
| 🟢 **LOW** | 28+ | Architecture index, Epic 4-5, Archive files | Architect | T+10+ (as needed) |

### By Owner

| Owner | Critical | High | Medium | Low | Total |
|-------|----------|------|--------|-----|-------|
| **Product Owner (Sarah)** | 2 | 3 | 2 | 3 | 10 |
| **Architect** | 2 | 0 | 3 | 25+ | 30+ |
| **Dev (Amelia)** | 0 | 0 | 1 | 0 | 1 |

### By Timeline

| Timeline | Files | Description |
|----------|-------|-------------|
| **T+0 to T+2** (IMMEDIATE) | 4 | CRITICAL: Epic 2 redefinition, PRD index, Tech Stack, Phases |
| **T+1 to T+3** (SHORT-TERM) | 3 | HIGH: Epic List, Requirements, Deprecate old Epic 2 |
| **T+2 to T+10** (MEDIUM-TERM) | 5 | MEDIUM: Repo Structure, Reference Impl, Epic 3, Stories |
| **T+10+** (LONG-TERM) | 28+ | LOW: Archive audit, Epic 4-5 reviews, Index updates |

---

## 🎯 Recommended Update Sequence

### Phase 1: Critical Path (BLOCKS DEV) - T+0 to T+2

**Day 1 (T+0 to T+1)**:
1. ✅ PO (Sarah): Rewrite `epic-2-advanced-rag-enhancements.md` (COMPLETE)
2. ✅ Architect: Update `5-technology-stack-definitive.md` (ADD pypdfium, conditional entries)
3. ✅ Architect: Rewrite `8-phased-implementation-strategy-v11-simplified.md` (Phase 1-3)

**Day 2 (T+1 to T+2)**:
4. ✅ PO (Sarah): Update `prd/index.md` (Epic 2 title + story list)
5. ✅ PO (Sarah): Update `epic-list.md` (Epic 2 description + priority)
6. ⚠️ PO (Sarah): Delete or archive `epic-2-advanced-document-understanding.md` (old file)

**GATE**: Dev (Amelia) can start Phase 1 implementation after Day 2 complete

---

### Phase 2: High Priority (SUPPORTS CLARITY) - T+2 to T+3

**Day 3-4**:
7. ✅ PO (Sarah): Update `requirements.md` (FR6-FR8 conditional, NFR6 milestone)
8. ✅ Architect: Add NOTE to `3-repository-structure-monolithic.md` (conditional layers)

---

### Phase 3: Medium Priority (QUALITY) - T+3 to T+10

**Week 2-3**:
9. ✅ Architect or Dev: Update `6-complete-reference-implementation.md` (chunking examples)
10. ✅ PO (Sarah): Review `epic-3-ai-intelligence-orchestration.md` (Epic 2 dependencies)
11. ✅ PO (Sarah): Create new story files in `docs/stories/` (Stories 2.1-2.5)
12. ✅ Architect: Update `architecture/index.md` (if Phase 2 section renamed)

---

### Phase 4: Low Priority (CLEANUP) - T+10+

**Future Sprints**:
13. ✅ Architect: Audit 28+ architecture files (identify ACTIVE vs ARCHIVE)
14. ✅ Architect: Move archive files to `docs/archive/`
15. ✅ PO (Sarah): Review `checklist-results-report.md`, `next-steps.md` (Epic 2 refs)

---

## ✅ Quality Checklist

**Before declaring "handoff complete", verify**:

### Critical Path Complete
- [ ] `epic-2-advanced-rag-enhancements.md` - Epic 2 redefinition complete
- [ ] `prd/index.md` - Epic 2 title and story list updated
- [ ] `5-technology-stack-definitive.md` - pypdfium + conditional tech added
- [ ] `8-phased-implementation-strategy-v11-simplified.md` - Phase 1-3 rewrite complete

### High Priority Complete
- [ ] `epic-list.md` - Epic 2 description + priority updated
- [ ] `epic-2-advanced-document-understanding.md` - OLD file deleted or archived
- [ ] `requirements.md` - FR6-FR8 conditional, NFR6 milestone added

### Validation
- [ ] No broken links in PRD (test all Epic 2 story links)
- [ ] No references to "Advanced Document Understanding" (use "Advanced RAG Architecture Enhancement")
- [ ] No references to Stories 2.1-2.7 OLD (use Stories 2.1-2.5 NEW)
- [ ] GraphRAG NOT deprecated (Phase 2C contingency documented)

---

## 📝 Notes for Owners

### For Product Owner (Sarah)

**Priority Focus**:
1. **CRITICAL**: Epic 2 redefinition + PRD index update (Day 1-2)
2. **HIGH**: Epic list, requirements, old file deletion (Day 3-4)
3. **MEDIUM**: Epic 3 review, new story files (Week 2-3)

**Quality Standards**:
- Use exact story titles from `HANDOFF-TO-PO-AND-ARCHITECT.md`
- Maintain consistency: "Advanced RAG Architecture Enhancement" (not "Advanced RAG" or variations)
- Link to new Epic 2 file: `epic-2-advanced-rag-enhancements.md` (NOT old `epic-2-advanced-document-understanding.md`)

### For Architect

**Priority Focus**:
1. **CRITICAL**: Tech stack + phases rewrite (Day 1-2)
2. **MEDIUM**: Repository structure note, reference implementation update (Week 2-3)
3. **LOW**: Archive audit (future sprints)

**Quality Standards**:
- Un-deprecate GraphRAG explicitly (add "Phase 2C contingency" note)
- Document ALL conditional technologies with decision gate triggers
- Maintain technology stack LOCKED policy (user approval required)

---

## 🔗 Reference Documents

**For This Audit**:
- `SPRINT-CHANGE-PROPOSAL.md` - Comprehensive formal proposal (APPROVED)
- `HANDOFF-TO-PO-AND-ARCHITECT.md` - Detailed handoff instructions

**For Updates**:
- Use exact wording from Sprint Change Proposal Section 2 (Epic redefinition)
- Use exact story titles from Handoff document "Priority 1: Epic 2 Redefinition"

---

**Audit Date**: 2025-10-19
**Audit By**: PM (John)
**Audit Scope**: ALL PRD + Architecture documentation
**Status**: COMPLETE - Ready for Owner Execution
