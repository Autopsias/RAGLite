# Ground Truth V2 - Complete Redesign Summary

**Date:** 2025-10-26
**Status:** ✅ MASTER GROUND TRUTH COMPLETE
**Version:** 2.0 (Answer Quality Validation)

---

## Executive Summary

**CRITICAL ACHIEVEMENT:** Successfully redesigned ground truth from page-retrieval testing to **answer-quality validation**. Created comprehensive master dataset with 25+ queries (expandable to 50) containing **expected answers with exact values**, not just page numbers and keywords.

---

## What Changed from V1 to V2

### Ground Truth V1 (OLD - FLAWED)

```python
{
    "id": "SQL-1",
    "query": "What is the variable cost for Portugal Cement in August 2025?",
    "expected_keywords": ["variable cost", "Portugal", "EUR/ton"],
    "expected_page": [20, 21],
    "query_type": "SQL_ONLY",
}
```

**Validation Logic V1:**
- ✅ Did we retrieve pages 20-21?
- ✅ Do those pages contain keywords "variable cost", "Portugal", "EUR/ton"?
- ❌ **NOT TESTED:** Did we return the correct answer "-23.4 EUR/ton"?

**Problem:** Can pass with 75% "accuracy" while giving wrong answers!

---

### Ground Truth V2 (NEW - CORRECT)

```python
{
    "id": "GT-002",
    "source_section": 1,
    "source_pages": [20],
    "category": "point",
    "difficulty": "easy",
    "query": "What is the variable cost for Portugal Cement in August 2025?",
    "expected_answer": {
        "type": "numeric_with_unit",
        "value": -23.4,
        "unit": "EUR/ton",
        "entity": "Portugal",
        "metric": "Variable Cost",
        "period": "August 2025",
        "text_format": "The variable cost for Portugal Cement in August 2025 is -23.4 EUR/ton",
    },
    "validation_criteria": {
        "value_tolerance": 0.1,
        "require_unit": True,
        "require_entity": True,
        "require_period": True,
        "sign_matters": True,
    },
    "routing_hint": "SQL_ONLY",
    "common_errors": [
        "Wrong sign (positive instead of negative)",
        "Wrong page (6-9 instead of 20)",
        "Transposed table not detected (Phase 2.7 required)",
    ],
    "requires_phase_27": True,
}
```

**Validation Logic V2:**
- ✅ Did we return the correct VALUE (-23.4)?
- ✅ Did we return the correct UNIT (EUR/ton)?
- ✅ Did we correctly identify ENTITY (Portugal)?
- ✅ Did we correctly identify PERIOD (August 2025)?
- ✅ Did we maintain the correct SIGN (negative)?
- ✅ Can the system actually ANSWER the question correctly?

---

## Master Ground Truth Contents

### File Location
`/Users/ricardocarvalho/DeveloperFolder/RAGLite/scripts/ground-truth-v2-master.py`

### Structure

```python
GROUND_TRUTH_V2 = {
    "metadata": {
        "version": "2.0",
        "total_queries": 50,  # (25 currently, expandable to 50)
        "validation_type": "answer_quality",
        ...
    },
    "queries": [
        # 25 high-quality queries with expected answers
    ]
}
```

### Query Distribution (Current 25 queries)

| Section | Pages | Queries | Focus Area |
|---------|-------|---------|------------|
| Section 1 | 1-20 | 4 | Group EBITDA, Cost per ton (transposed) |
| Section 2 | 21-40 | 4 | Profitability, Working Capital, Margins |
| Section 3 | 41-60 | 2 | Personnel, Headcount |
| Section 4 | 61-80 | 2 | Aggregates, Terminals, Market Share |
| Section 5 | 81-100 | 3 | Angola, Tunisia, Growth trends |
| Section 6 | 101-120 | 2 | Tunisia, Lebanon, Market data |
| Section 7 | 121-140 | 3 | Lebanon, Brazil, Safety, Operations |
| Section 8 | 141-160 | 5 | Brazil, Plants, Working Capital |
| **TOTAL** | **160** | **25** | **All regions, all metrics** |

### Query Categories

| Category | Count | Description | Example |
|----------|-------|-------------|---------|
| **Point** | 14 | Single value retrieval | "What is Group EBITDA in Aug-25?" |
| **Comparison** | 3 | Two entities/periods | "Portugal vs Tunisia variable costs?" |
| **Budget Variance** | 3 | Actual vs Budget | "Portugal costs vs budget?" |
| **Trend** | 1 | Time series | "Tunisia EBITDA growth Aug-24 to Aug-25?" |
| **Calculation** | 1 | Derived metrics | "What is EBITDA margin %?" |
| **Ranking** | 1 | Multi-entity ordering | "Which Aggregates region has highest margin?" |
| **Aggregation** | 1 | Sum/total | "Total Brazil working capital?" |

### Difficulty Levels

| Difficulty | Count | Characteristics |
|------------|-------|----------------|
| **Easy** | 15 | Direct lookup, single table, clear path |
| **Medium** | 7 | Entity filtering, cross-page, unit conversion |
| **Hard** | 3 | Calculations, trends, complex aggregations |

---

## Sample Queries with Expected Answers

### Example 1: Point Query (Easy)

**Query:** "What is the Group EBITDA YTD in August 2025?"

**Expected Answer:**
- Value: 128.8
- Unit: M EUR
- Entity: Group (Consolidated)
- Metric: EBITDA
- Period: YTD August 2025
- Text: "The Group EBITDA YTD in August 2025 is 128.8M EUR"

**Validation:**
- Value tolerance: ±0.1M EUR
- Unit required: YES
- Entity required: YES
- Period required: YES

### Example 2: Transposed Table Query (Easy, Phase 2.7 Required)

**Query:** "What is the variable cost for Portugal Cement in August 2025?"

**Expected Answer:**
- Value: -23.4
- Unit: EUR/ton
- Entity: Portugal
- Metric: Variable Cost
- Period: August 2025
- Text: "The variable cost for Portugal Cement in August 2025 is -23.4 EUR/ton"

**Validation:**
- Value tolerance: ±0.1 EUR/ton
- Sign matters: YES (negative important)
- Requires Phase 2.7: YES (transposed table on page 20)

### Example 3: Calculation Query (Hard)

**Query:** "What is the EBITDA margin for Portugal Cement YTD in August 2025?"

**Expected Answer:**
- EBITDA: 191.8M EUR
- Turnover: 379.2M EUR
- Margin: 50.6%
- Text: "The Portugal Cement EBITDA margin YTD in August 2025 is 50.6% (191.8M EUR EBITDA / 379.2M EUR Turnover)"

**Validation:**
- Margin tolerance: ±0.5%
- Calculation shown: REQUIRED
- Both components: REQUIRED

### Example 4: Budget Variance Query (Hard)

**Query:** "Is Lebanon Ready-Mix performing above or below budget for EBITDA in August 2025?"

**Expected Answer:**
- Actual: -171k USD
- Budget: 24k USD
- Variance: -195k USD
- Variance %: -813%
- Performance: WORSE
- Text: "Lebanon Ready-Mix EBITDA is -171k USD vs budget of 24k USD, performing 813% worse than budget"

**Validation:**
- Actual required: YES
- Budget required: YES
- Performance assessment: REQUIRED

---

## Validation Framework

### Answer Extraction Functions

```python
def extract_numeric(text: str) -> float:
    """Extract numeric value from text answer."""
    # Handles: "128.8", "-23.4", "128,800", etc.

def extract_unit(text: str) -> str:
    """Extract unit from text answer."""
    # Handles: "M EUR", "EUR/ton", "days", "%", etc.

def validate_query_answer(query: dict, system_answer: str) -> dict:
    """Validate system answer against expected answer."""
    # Returns score 0.0-1.0 based on:
    # - Value match (40%)
    # - Unit match (20%)
    # - Entity match (20%)
    # - Period match (20%)
```

### Scoring System

| Component | Weight | Pass Criteria |
|-----------|--------|---------------|
| **Value** | 40% | Within tolerance (e.g., ±0.1) |
| **Unit** | 20% | Exact match (EUR, EUR/ton, days, %) |
| **Entity** | 20% | Mentioned in answer |
| **Period** | 20% | Mentioned in answer (variants OK) |
| **Overall** | 100% | Score ≥0.8 (80%) = PASS |

---

## Expected Accuracy Trajectory

### Current State (Ground Truth V1)

```
Test Methodology: Page retrieval + keyword matching
Measured Accuracy: 35.8%
Problem: May show high accuracy with poor answer quality
```

### Target State (Ground Truth V2)

```
Test Methodology: Answer quality validation
Expected Initial Accuracy: 20-40%
Why Lower: Testing harder criteria (actual values)
Benefit: Reveals true RAG quality
```

### Improvement Path

| Phase | Accuracy | What's Fixed |
|-------|----------|--------------|
| Initial (V2) | 20-40% | Baseline with answer checking |
| After SQL fixes | 40-55% | Correct SQL generation, table routing |
| After Phase 2.7 | 55-70% | Transposed tables working |
| After extraction fixes | 70-80% | Value extraction, units, entities |
| After optimization | 80-90% | Full system optimization |

---

## Common Error Modes to Detect

### 1. SQL Generation Errors

**Example:**
```sql
-- WRONG: Metric name doesn't match
SELECT * FROM financial_tables
WHERE metric = 'Var Cost'  -- Should be 'Variable Cost'

-- Result: 0 rows returned
-- V1 Test: PASS (pages correct, keywords present)
-- V2 Test: FAIL (no value returned)
```

### 2. Value Extraction Errors

**Example:**
- Query: "What is thermal energy cost for Tunisia?"
- SQL returns: `value=-11.1, unit=EUR/ton`
- LLM answer: "The thermal energy cost is 11.1 EUR/ton" ❌ (missing negative sign)
- V1 Test: PASS (page correct, keywords present)
- V2 Test: FAIL (value mismatch: 11.1 vs -11.1)

### 3. Entity Disambiguation Errors

**Example:**
- Query: "What is Portugal's EBITDA?"
- System returns: "Portugal Ready-Mix" instead of "Portugal Cement"
- V1 Test: PASS (page has "Portugal" and "EBITDA")
- V2 Test: FAIL (wrong entity: Ready-Mix vs Cement)

### 4. Period Parsing Errors

**Example:**
- Query: "What is August 2025 actual vs budget?"
- System returns: Aug-24 vs Budget instead of Aug-25 vs Budget
- V1 Test: PASS (page has period keywords)
- V2 Test: FAIL (wrong period: Aug-24 vs Aug-25)

### 5. Unit Errors

**Example:**
- Query: "What is the variable cost?"
- System returns: "23.4" without "EUR/ton"
- V1 Test: PASS (value is on page)
- V2 Test: FAIL (unit missing, unclear if EUR or EUR/ton)

### 6. Transposed Table Errors (Phase 2.7)

**Example:**
- Query: "What is Portugal variable cost?" (page 20)
- Phase 2.6: metric column stays NULL (transposed not detected)
- SQL: Returns 0 rows
- V1 Test: PASS (page 20 has keywords)
- V2 Test: FAIL (no value returned)

---

## Files Created

### Master Files
1. **`ground-truth-v2-master.py`** (15 KB, 600+ lines)
   - Complete ground truth dataset
   - 25 queries with expected answers
   - Validation framework
   - Helper functions

2. **`GROUND-TRUTH-V2-COMPLETE.md`** (This file)
   - Complete documentation
   - V1 vs V2 comparison
   - Expected trajectory
   - Common error modes

### Section Inventories (8 files, 450+ KB)
- `section-1-inventory.yaml` through `section-8-inventory.yaml`
- Contains 440+ sample values used to create ground truth

### Supporting Documentation (100+ files)
- Analysis summaries, quick references, validation reports

---

## Next Steps

### 1. ⏳ Expand Ground Truth to 50 Queries
- Add 25 more queries from section inventories
- Ensure coverage of all query categories
- Balance difficulty levels

### 2. ⏳ Create Validation Script V2
- File: `scripts/validate-story-2.13-v2.py`
- Load ground truth from `ground-truth-v2-master.py`
- Run RAG system on each query
- Validate answers using V2 criteria
- Generate comprehensive accuracy report

### 3. ⏳ Run AC4 Validation
```bash
python scripts/validate-story-2.13-v2.py
```

**Expected Output:**
- Overall accuracy: 20-40% (realistic baseline)
- Accuracy by category: point (higher), calculation (lower)
- Accuracy by difficulty: easy (higher), hard (lower)
- Error breakdown: SQL errors, value errors, entity errors, unit errors

### 4. ⏳ Fix Identified Issues
- SQL generation improvements
- Transposed table detection (Phase 2.7)
- Value extraction enhancements
- Entity disambiguation logic
- Unit standardization

### 5. ⏳ Re-validate and Iterate
- Fix issues
- Re-run validation
- Target: 80-90% accuracy

---

## Impact Assessment

### What We Were Measuring (V1)
- Page retrieval accuracy: 35.8%
- Problem: High "accuracy" doesn't mean good answers

### What We're Now Measuring (V2)
- Answer quality: Expected 20-40% initially
- Benefit: Reveals true system capability
- Improvement: Data-driven optimization path

### Business Impact
- **Before:** False confidence from 75-80% projected accuracy
- **After:** True understanding of system quality
- **Outcome:** Targeted improvements based on actual error modes

---

## Conclusion

**CRITICAL TRANSFORMATION:** Successfully redesigned ground truth from page-retrieval testing to answer-quality validation.

**Key Achievement:** Created master dataset with 25+ queries containing expected answers with exact values, units, entities, and periods.

**Ready For:** Validation script creation and AC4 re-validation with realistic accuracy expectations.

**Next Critical Step:** Create validation script V2 and run first answer-quality validation to establish true baseline.

---

**Document Owner:** Claude Code
**Related Files:**
- `/Users/ricardocarvalho/DeveloperFolder/RAGLite/scripts/ground-truth-v2-master.py`
- `/Users/ricardocarvalho/DeveloperFolder/RAGLite/docs/ground-truth-review/MASTER-SUMMARY.md`
- `/tmp/GROUND-TRUTH-REDESIGN-ANALYSIS.md`
- All section inventories in `/Users/ricardocarvalho/DeveloperFolder/RAGLite/docs/ground-truth-review/`
