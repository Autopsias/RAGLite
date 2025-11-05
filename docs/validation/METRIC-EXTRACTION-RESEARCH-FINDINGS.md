# METRIC EXTRACTION - RESEARCH FINDINGS

**Date:** 2025-10-26
**Session:** Metric Extraction Best Practices Research
**Status:** ✅ **RESEARCH COMPLETE**

## Executive Summary

Completed comprehensive deep research on extracting metric names (row headers) from financial PDF tables. This research was conducted to inform the implementation strategy for fixing the root cause of AC4 validation failures: **metric extraction not capturing row headers like "variable costs", "EBITDA", "production volumes" from tables**.

**Research Method:** MCP Exa Deep Researcher (exa-research-pro model)
**Research Duration:** 152.4 seconds
**Task ID:** 01k8h0ndt50j8gxap8171r7nr0

---

## 1. Production Systems for Financial Table Extraction

### 1.1 FinRAG: Retrieval-Augmented Financial Analysis (EMNLP 2024)

**Architecture:**
- Two-stage retrieval-augmented generation framework
- Grounded in financial knowledge graph (FKG)
- Structured retrieval pipeline extracts facts (triples) from tables
- Cell role classification: header vs. data cells
- Cell cluster mapping to FKG entities via clustering + dense retrieval

**Key Limitation:** FinRAG assumes pre-extracted triples, does not explicitly address PDF table parsing

**Relevant to Our Problem:**
- ✅ Cell role classification (header detection)
- ✅ Knowledge graph enrichment for metric normalization
- ❌ No PDF parsing implementation details

### 1.2 TableRAG: Hybrid RAG for Heterogeneous Documents (arXiv 2506.10380)

**Architecture:**
- Unifies textual retrieval with SQL-based table manipulation
- **Offline database construction:**
  1. Parse PDF tables into relational tables and markdown chunks
  2. Chunk text and table slices
  3. Map chunks to table schema metadata via mapping function f
- **Iterative online reasoning:**
  1. Decompose user queries to subqueries
  2. Context-sensitive modality identification
  3. Retrieve text and relevant table schema
  4. Program-and-execute SQL against constructed DB
  5. Generate intermediate & final answers

**Key Insight:** TableRAG's table parsing pipeline:
- Detects table regions
- Renders markdown representations
- Ingests into relational DB
- Uses external PDF-to-table extractor (Tabula or in-house)

**Relevant to Our Problem:**
- ✅ SQL-based validation approach
- ✅ RDBMS ingestion for verification
- ✅ Modular parsing pipeline

---

## 2. Challenges in Row Header Extraction

### 2.1 Merged Cells & Multi-Row Headers

**Problem:**
- Merged cells spanning multiple rows/columns for multi-row headers
- Break uniform grid structure
- Require segment detection and header hierarchy reconstruction

**Traditional Approaches:**
- Rule-based extractors (Camelot, Tabula) detect cell span using heuristics
- Struggle when borders or whitespace cues are inconsistent

**Reference:** [Upstage Blog - Table Structure Extraction Challenges](https://upstage.ai/blog/en/why-table-structure-extraction-fails-a-deep-dive-into-real-world-challenges)

### 2.2 Hierarchical Header Structures

**Problem:**
- Multi-level hierarchies:
  - Broad sections: "Operating Costs"
  - Subcategories: "Variable Costs"
  - Detailed metrics: "Raw Materials"

**Required Capabilities:**
1. Header cell grouping by spanning relationships
2. Assigning header depth levels
3. Linking header paths to data rows

**Proven Approaches:**
- **Graph-based interpretation:** Construct adjacency graph of cells based on spatial proximity and text alignment, infer hierarchies via graph clustering (GFTE, arXiv 2003.07560)
- **Rectangle mining:** Detect header regions, segment semantic rectangles, build tree structures via spatial containment

### 2.3 Section Context for Disambiguation

**Problem:**
- Generic metric names (e.g., "Cost") need disambiguation
- Table captions and surrounding text provide context

**Solution:**
- Embed table extraction in document context
- Link table captions or section titles as context features
- FinRAG's FKG retrieval augments cell text with domain knowledge

---

## 3. Best Practices for Table Structure Understanding

### 3.1 Cell Role Classification

**Approach:**
- Assign each cell as header or data via supervised models
- **Models:** LayoutLMv3 fine-tuned on annotated table datasets
- **Features:** Font size, style, position, adjacency to table boundaries
- **Combined with:** Heuristic rules for merged cells

### 3.2 Header Detection & Hierarchy Extraction

**Multi-Row Header Detection:**
- Identify header rows by top-of-table rows with fewer filled cells
- Detect row spans by cell width relative to column width

**Hierarchical Relationships:**
- Tree induction over header rows
- Parent-child assignment based on spatial containment and span indices
- **Reference:** TRH2TQA, WACV 2025

**Post-Structure Extraction Validation:**
- Enforce Cartesian product consistency between header combinations and data columns

### 3.3 Proven Approaches Summary

1. **SQL-based pipeline (TableRAG):**
   - Ingest cleaned tables into RDBMS
   - Use SQL queries to validate header-data alignment
   - Extract metrics by querying distinct header values per row

2. **RAG + KG enrichment (FinRAG):**
   - Cluster extracted header texts to KG nodes
   - Resolve synonyms and normalize metric names

3. **Graph neural networks:**
   - Model tables as graphs (cells as nodes, edges for adjacency)
   - Predict header-data relations (GFTE)

---

## 4. Open-Source Tools & Libraries

### 4.1 Recommended Tools

| Tool | Type | Strengths | Weaknesses |
|------|------|-----------|------------|
| **Camelot** | Python PDF extractor | Border + whitespace detection, span detection via lattice flavor | Struggles with inconsistent borders |
| **Tabula** | Java PDF extractor | Continuous whitespace detection, CSV output | Limited hierarchy support |
| **pdfplumber** | Low-level PDF parser | Raw cell bounding boxes, custom heuristics | Requires manual logic |
| **Excalibur** | Web interface | UI for Camelot/Tabula | Not programmatic |
| **CycloneBoy/pdf_table** | Deep learning toolkit | Layout analysis, cell detection via ML | Newer, less proven |
| **PDF-Extract-Kit** | Comprehensive framework | OCR + ML, text and table extraction | Heavy dependency |

### 4.2 Current Stack: Docling

**Our Current Tool:** Docling (from DS4SD)
- Advanced table structure understanding
- 97.9% table accuracy baseline
- **Question:** Are we leveraging Docling's full capabilities for row header extraction?

---

## 5. Common Pitfalls & Solutions

| Pitfall | Impact | Solution |
|---------|--------|----------|
| **Inconsistent borders** | Failed cell detection | Fallback to whitespace-based + ML cell segmentation |
| **False header detection** | Data rows marked as headers | Refine with textual features (uppercase ratio, stopwords) + positional priors |
| **Hierarchy collapse** | Merged headers flattened | Post-hoc consistency checks, reassemble via bbox clustering |
| **Merged cell flattening** | Context loss | Cluster identical bbox text spans to reconstruct merged headers |

---

## 6. Code Patterns & Architectural Recommendations

### 6.1 Modular Pipeline (Recommended)

**Stages:**
1. **PDF Parsing** - Extract raw table regions
2. **Table Detection** - Identify table boundaries
3. **Cell Role Classification** - Header vs. data cells
4. **Hierarchy Reconstruction** - Build header tree
5. **Post-Processing** - Validation and normalization

### 6.2 Database Ingestion (TableRAG Approach)

**Benefits:**
- Load parsed tables into SQL database
- Verification via SQL queries
- Flexible querying of header structures

**Implementation:**
- Use PostgreSQL (already in our stack)
- Validate header-data alignment with SQL
- Query distinct header values per row

### 6.3 RAG Augmentation (FinRAG Strategy)

**Benefits:**
- Integrate external domain knowledge (KG)
- Normalize header text
- Resolve ambiguities

**Implementation:**
- Use entity normalization (already implemented in Story 2.13)
- Extend to metric normalization
- Leverage LLM for contextual enrichment

### 6.4 Iterative Refinement

**Approach:**
- Layout model-based extraction (LayoutLM/TableFormer)
- Rule-based correction for merged cells
- Iterative improvement based on validation results

---

## 7. Implementation Strategy for RAGLite

### 7.1 Current State Analysis

**What We Know:**
- Database has entities: ✅ "Portugal", "Portugal Cement" correctly extracted
- Database lacks metrics: ❌ "variable cost", "EBITDA" missing
- Only generic metrics found: "Cost", "All-in cost", "Average cost"
- Fiscal year extraction issues: Many NULL values

**Root Cause:**
Table extraction pipeline (`raglite/ingestion/pipeline.py`) not correctly extracting metric names from table row headers.

### 7.2 Recommended Approach: Multi-Phase Implementation

#### Phase 1: Diagnostic Analysis (2-4 hours)
**Goal:** Understand current Docling extraction behavior

**Tasks:**
1. Extract sample tables from test PDF
2. Inspect Docling's raw table structures
3. Identify where row header information is available but not extracted
4. Document Docling's table model and available attributes

**Success Criteria:**
- Clear understanding of Docling's TableCell/TableRow structure
- Identification of row header extraction gap
- Sample tables with known metrics for testing

#### Phase 2: Row Header Extraction Enhancement (1-2 days)
**Goal:** Implement proper row header extraction

**Approach Options:**

**Option A: Leverage Docling's Native Capabilities (RECOMMENDED)**
- Investigate Docling's `TableCell.cell_type` or similar attributes
- Extract row headers using Docling's built-in header classification
- Minimal code changes, leverages proven library

**Option B: Heuristic-Based Row Header Detection**
- Detect leftmost column as row headers
- Use positional + styling heuristics (bold, left-aligned)
- Implement header hierarchy reconstruction for multi-level headers

**Option C: LLM-Based Header Extraction**
- Pass table structure to Claude
- Request metric identification and normalization
- High accuracy but slower and more expensive

**Recommendation:** Start with Option A (Docling native), fall back to Option B if needed

**Success Criteria:**
- Row headers extracted and stored in `metric` field
- Test on 20-page sample: <25% NULL metrics (vs. current 77.5%)

#### Phase 3: Section Context Integration (1 day)
**Goal:** Use document context to disambiguate metrics

**Tasks:**
1. Extract section headings and table captions
2. Store as additional context metadata
3. Use context to normalize generic metric names

**Success Criteria:**
- Context stored in database
- Ambiguous metrics (e.g., "Cost") clarified via context

#### Phase 4: Validation & Tuning (1-2 days)
**Goal:** Verify improvements and tune extraction

**Tasks:**
1. Re-ingest test dataset (20-page sample)
2. Measure NULL metric reduction
3. Run AC4 validation subset
4. Tune extraction heuristics based on failures

**Success Criteria:**
- NULL metrics <25% (target)
- AC4 accuracy improvement (35.8% → >50%)

#### Phase 5: Full Dataset Re-ingestion (2-3 hours)
**Goal:** Apply improvements to full 160-page PDF

**Tasks:**
1. Clear existing data
2. Re-ingest with improved extraction
3. Full AC4 validation

**Success Criteria:**
- AC4 overall accuracy ≥70%

### 7.3 Code Modifications Required

**Primary File:** `raglite/ingestion/pipeline.py`

**Expected Changes:**
- Enhance `extract_financial_table_rows()` function
- Add row header detection logic
- Integrate section context extraction
- Add validation and normalization

**Estimated LOC:** 100-150 lines of new code

### 7.4 Testing Strategy

**Unit Tests:**
- Test row header extraction on sample tables
- Test hierarchy reconstruction for multi-level headers
- Test context integration

**Integration Tests:**
- Re-ingestion scripts with before/after comparison
- NULL field statistics tracking
- Sample query validation

**Validation Tests:**
- AC4 subset validation (10 queries)
- Full AC4 validation (50 queries)

---

## 8. Decision Tree

```
START
  │
  ├─ Phase 1: Diagnostic Analysis (2-4 hours)
  │   ├─ Can Docling provide row headers natively?
  │   │   ├─ YES → Use Docling native (Option A)
  │   │   └─ NO → Implement heuristic detection (Option B)
  │   │
  │   └─ Test on 5 sample tables
  │       ├─ Success? → Proceed to Phase 2
  │       └─ Fail? → Consider LLM-based (Option C)
  │
  ├─ Phase 2: Row Header Extraction (1-2 days)
  │   └─ Test on 20-page sample
  │       ├─ NULL metrics <25%? → Proceed to Phase 3
  │       └─ Still high? → Add section context (Phase 3)
  │
  ├─ Phase 3: Section Context (1 day)
  │   └─ Retest 20-page sample
  │       ├─ Improvement? → Proceed to Phase 4
  │       └─ No change? → Review and debug
  │
  ├─ Phase 4: Validation & Tuning (1-2 days)
  │   └─ AC4 subset validation
  │       ├─ Accuracy >50%? → Proceed to Phase 5
  │       └─ Still low? → Deep debugging required
  │
  └─ Phase 5: Full Re-ingestion (2-3 hours)
      └─ Full AC4 validation
          ├─ Accuracy ≥70%? → ✅ COMPLETE
          └─ Still low? → Consider Phase 2B (cross-encoder)
```

---

## 9. Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Docling doesn't provide row headers | Medium | High | Implement heuristic fallback (Option B) |
| Multi-level headers too complex | Medium | Medium | Start with single-level, iterate |
| Context integration insufficient | Low | Medium | Add LLM-based metric normalization |
| Performance degradation | Low | Low | Optimize after correctness validated |
| Re-ingestion time too long | Low | Low | Use 20-page sample for iteration |

---

## 10. Success Metrics

**Immediate (Phase 2):**
- NULL metric field: 77.5% → <25%
- Row headers extracted for 75%+ of tables

**Short-term (Phase 4):**
- AC4 accuracy: 35.8% → >50%
- Test query "variable cost for Portugal Cement": Returns results

**Final (Phase 5):**
- AC4 overall accuracy: ≥70% ✅
- AC4 SQL_ONLY accuracy: ≥75% ✅
- AC4 HYBRID accuracy: ≥65% ✅

---

## 11. Key Learnings from Research

1. **Production systems exist:** FinRAG and TableRAG provide proven patterns
2. **Modular pipelines win:** Separate concerns (parsing, detection, classification, reconstruction)
3. **Database validation is critical:** Use SQL to verify header-data alignment
4. **Context matters:** Section headings and captions disambiguate generic metrics
5. **Iterative refinement works:** Start simple, add complexity based on validation failures
6. **Tools available:** Camelot, Tabula, pdfplumber, but Docling may already have what we need

---

## Next Steps

1. ✅ **Research Complete** - Findings documented
2. **Proceed to Phase 1:** Diagnostic analysis of Docling's row header capabilities
3. **Create implementation plan:** Based on Phase 1 findings
4. **Implement Phase 2:** Row header extraction enhancement
5. **Validate and iterate:** Phases 3-5 based on results

---

## References

- **FinRAG:** [ACL Anthology EMNLP 2024](https://aclanthology.org/2024.emnlp-industry.90.pdf)
- **TableRAG:** [arXiv 2506.10380](https://arxiv.org/html/2506.10380v1)
- **GFTE:** [arXiv 2003.07560](https://arxiv.org/abs/2003.07560)
- **Upstage Table Extraction:** [Blog Post](https://upstage.ai/blog/en/why-table-structure-extraction-fails-a-deep-dive-into-real-world-challenges)
- **Camelot:** [Documentation](https://camelot-py.readthedocs.io)
- **Docling:** [GitHub DS4SD](https://github.com/DS4SD/docling)

---

**Conclusion:** The research provides a clear, production-validated roadmap for fixing metric extraction. The multi-phase approach balances speed (using Docling's native capabilities first) with robustness (heuristic and LLM fallbacks if needed). Expected timeline: 4-7 days total from diagnostic to full validation.
