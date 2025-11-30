# RAGLite Accuracy Troubleshooting Guide

This guide helps diagnose and fix common accuracy issues in RAGLite.

---

## Quick Diagnostics

### 1. Check System Health

```bash
# Verify Qdrant is running
docker ps | grep qdrant

# Check if embeddings model is loaded
uv run python -c "from raglite.shared.clients import get_embedding_model; m = get_embedding_model(); print('✓ Model loaded')"

# Verify ground truth test set
python -c "from tests.fixtures.ground_truth import GROUND_TRUTH_QA; print(f'✓ {len(GROUND_TRUTH_QA)} test queries loaded')"
```

### 2. Run Quick Accuracy Check

```bash
# Run 10-query subset to identify issues
uv run python scripts/run-accuracy-tests.py --subset 10 --verbose
```

---

## Common Issues & Solutions

### Issue 1: Low Retrieval Accuracy (<70%)

**Symptoms:**
- Queries not finding relevant information
- Expected keywords missing from returned chunks
- Low similarity scores

**Investigation Checklist:**

1. **Check Docling Extraction Quality**
   ```bash
   # Verify page numbers are correctly extracted
   uv run python scripts/test_page_extraction.py
   ```
   - **Fix:** If page numbers wrong, check Docling version and document structure

2. **Review Chunking Strategy**
   - Current: 512-token chunks, 50-token overlap
   - **Too small?** May split context across chunks → increase chunk size
   - **Too large?** May dilute relevance → decrease chunk size
   - **Test:** Try 768-token chunks or 100-token overlap

3. **Test Embedding Quality**
   ```bash
   # Verify Fin-E5 model loaded correctly
   # Check if embeddings are semantically meaningful
   ```
   - **Fix:** Clear model cache, reload Fin-E5

4. **Check Qdrant Search Parameters**
   - **HNSW config:** `m=16, ef_construct=100` (current)
   - **Try:** Increase `ef_construct=200` for better recall
   - **top_k:** Currently 5, try increasing to 10

### Issue 2: Low Attribution Accuracy (<95%)

**Symptoms:**
- Citations pointing to wrong pages
- Page numbers off by >1
- Missing page metadata

**Investigation Checklist:**

1. **Verify Page Metadata Preservation**
   ```bash
   # Check if page_number stored in Qdrant
   # Inspect first chunk in Qdrant collection
   ```

2. **Check Chunking Boundaries**
   - Chunks spanning page boundaries may have ambiguous page numbers
   - **Fix:** Adjust chunk overlap or chunking strategy

3. **Validate Ground Truth Expectations**
   - Are expected page numbers correct in ground truth?
   - **Action:** Manually verify 5-10 test queries against source PDF

### Issue 3: High Latency (p50 >5s, p95 >15s)

**Symptoms:**
- Slow query response times
- Timeout errors

**Investigation Checklist:**

1. **Profile Query Execution**
   - Embedding generation: ~1-2s (Fin-E5)
   - Qdrant search: ~10-50ms
   - Citation generation: ~1-10ms
   - **Bottleneck?** Likely embedding generation

2. **Optimization Options**
   - **Cache embeddings:** Store query embeddings for repeated queries
   - **Connection pooling:** Already implemented (singleton pattern)
   - **Batch processing:** Not needed for single queries
   - **Qdrant HNSW:** Already optimized

3. **Check Resource Constraints**
   ```bash
   # Check Qdrant memory usage
   docker stats qdrant

   # Check disk space for model caching
   df -h ~/.cache/huggingface
   ```

### Issue 4: Specific Category Failures

**Symptoms:**
- One category has <70% accuracy
- Other categories performing well

**Investigation:**

1. **Analyze Failure Patterns**
   ```bash
   # Run category-specific tests
   uv run python scripts/run-accuracy-tests.py --category cost_analysis --verbose
   ```

2. **Check Document Coverage**
   - Does the ingested document contain this category's information?
   - **Fix:** Verify document ingestion, check for extraction errors

3. **Review Query Phrasing**
   - Are test queries using domain-specific terminology?
   - **Fix:** Adjust ground truth queries to match document language

---

## Debugging Workflow

### Step 1: Identify the Problem

```bash
# Run full test suite to establish baseline
uv run python scripts/run-accuracy-tests.py --output baseline.json

# Analyze results by category/difficulty
```

### Step 2: Isolate the Root Cause

```bash
# Test a single failing query
uv run python scripts/run-accuracy-tests.py --subset 1 --verbose

# Manually inspect returned chunks
# Check if expected information is in the chunks
# Verify page numbers are correct
```

### Step 3: Test Fixes

```bash
# After making changes, re-run tests
uv run python scripts/run-accuracy-tests.py --subset 10

# Compare results to baseline
```

### Step 4: Validate Fix

```bash
# Run full test suite
uv run python scripts/run-accuracy-tests.py

# Verify no regressions in other categories
```

---

## Performance Optimization Tips

### 1. Embedding Model

- **Current:** Fin-E5 (financial domain adaptation)
- **Alternative:** Standard E5-large-v2 (faster, less domain-specific)
- **Trade-off:** Speed vs. financial terminology accuracy

### 2. Qdrant Configuration

- **Collection settings:**
  ```python
  VectorParams(
      size=1024,
      distance=Distance.COSINE,
      hnsw_config=HnswConfigDiff(
          m=16,              # Number of bi-directional links
          ef_construct=100   # Quality of index construction
      )
  )
  ```
- **Tuning:** Increase `m` to 32 or `ef_construct` to 200 for better recall at cost of speed

### 3. Chunking Strategy

- **Current:** 512 tokens, 50 overlap
- **Alternatives:**
  - Larger chunks (768): Better context, may dilute relevance
  - Smaller chunks (256): More precise, may lose context
  - Larger overlap (100): Better boundary handling, more storage

---

## When to Escalate

### Trigger GraphRAG (Phase 2) if:

1. **Multi-hop queries failing consistently**
   - Queries requiring information from multiple documents
   - Queries needing relationship traversal (e.g., "Which subsidiaries increased revenue?")

2. **Accuracy <80% after optimization**
   - Tried all troubleshooting steps above
   - No significant improvement

3. **Complex financial analysis queries**
   - Queries requiring chain-of-thought reasoning
   - Queries needing temporal relationships

### Reassess Technology Stack if:

1. **Accuracy <70% on simple queries**
   - Even easy single-fact lookups failing
   - Suggests fundamental extraction or embedding issues

2. **Persistent page attribution errors**
   - Page numbers consistently wrong despite fixes
   - Suggests Docling extraction issues

---

## Additional Resources

- **Accuracy Tracking:** `docs/accuracy-tracking-log.jsonl`
- **Test Results:** `docs/qa/epic-1-final-validation-report-*.md`
- **Architecture:** `docs/architecture/`
- **PRD:** `docs/prd/epic-1-foundation-accurate-retrieval.md`

---

**Last Updated:** 2025-10-13
**Story:** 1.12B (Continuous Accuracy Tracking & Final Validation)
