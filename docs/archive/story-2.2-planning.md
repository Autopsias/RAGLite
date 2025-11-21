# Story 2.2 - Implement Page-Level Parallelism for PDF Ingestion

**Epic:** Epic 2 Phase 1 - PDF Ingestion Performance Optimization
**Status:** PLANNING
**Priority:** P0 (Critical Path to Phase 2)
**Estimated Effort:** 4-6 hours

---

## Context

**Story 2.1 Results:**
- PyPdfium backend implemented successfully ✅
- Speedup achieved: 1.08x (7.2% faster)
- **Gap to target:** Expected 1.7-2.5x, achieved 1.08x

**Root Cause Analysis:**
PDF parsing is only ~53% of total ingestion time (7.1 min out of 13.3 min). Remaining time:
- Embedding generation: ~6% (51 seconds)
- Chunking/processing: ~4% (30 seconds)
- Model loading/overhead: ~35% (254 seconds)
- Qdrant operations: ~2% (12 seconds)

**Solution:** Parallelize PDF parsing across pages to reduce wall-clock time

---

## Story Goal

Implement page-level parallelism in PDF ingestion to achieve 1.7-2.5x total speedup over baseline.

**Target Performance (160-page PDF):**
- Current: 13.3 minutes (799 seconds)
- Target: 5.3-7.8 minutes (320-470 seconds)
- Speedup: 1.7x-2.5x

---

## Acceptance Criteria

### AC1: Parallel Page Processing Implementation
- [ ] Implement concurrent page processing using Python's `concurrent.futures.ThreadPoolExecutor`
- [ ] Configure batch size (e.g., 40 pages per batch for 160-page PDF = 4 batches)
- [ ] Maintain element extraction quality (no degradation)
- [ ] Pass unit tests validating parallel extraction

**Success:** Pages processed in parallel batches, reducing PDF parsing time

---

### AC2: Thread-Safe Element Merging
- [ ] Implement thread-safe merging of extracted elements from parallel batches
- [ ] Preserve page order in final merged document
- [ ] Validate element count matches sequential processing
- [ ] Pass integration test comparing sequential vs parallel output

**Success:** Merged elements identical to sequential processing

---

### AC3: 10-Page Performance Validation
- [ ] Run parallel ingestion on 10-page sample PDF
- [ ] Measure ingestion time (target: <20 seconds, down from 30.3s)
- [ ] Verify table accuracy maintained (≥97.9%)
- [ ] Compare speedup vs Story 2.1 baseline

**Success:** 10-page PDF ingestion ≤20 seconds, table accuracy ≥97.9%

---

### AC4: 160-Page Comprehensive Validation
- [ ] Run parallel ingestion on 160-page production PDF
- [ ] Measure total ingestion time (target: 5.3-7.8 minutes)
- [ ] Validate 1.7-2.5x speedup over Story 2.1 baseline (799 seconds)
- [ ] Verify memory usage remains <3 GB
- [ ] Verify table accuracy maintained at 100%
- [ ] Pass comprehensive integration test

**Success:** 160-page PDF ingestion in 5.3-7.8 minutes (1.7-2.5x speedup), table accuracy 100%

---

## Technical Design

### Approach 1: Page-Level ThreadPoolExecutor (RECOMMENDED)

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List
import asyncio

async def ingest_pdf_parallel(
    pdf_path: Path,
    batch_size: int = 40,
    max_workers: int = 4
) -> IngestionResult:
    """Ingest PDF with page-level parallelism."""

    # Step 1: Get page count
    page_count = get_page_count(pdf_path)

    # Step 2: Create page batches
    batches = create_page_batches(page_count, batch_size)
    # Example: 160 pages, batch_size=40 → [[0-39], [40-79], [80-119], [120-159]]

    # Step 3: Process batches in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for batch_pages in batches:
            future = executor.submit(
                process_page_batch,
                pdf_path,
                batch_pages,
                backend=PyPdfiumDocumentBackend
            )
            futures.append(future)

        # Step 4: Collect results as they complete
        batch_results = []
        for future in as_completed(futures):
            batch_result = future.result()
            batch_results.append(batch_result)

    # Step 5: Merge results (maintaining page order)
    all_elements = merge_batch_results(batch_results, preserve_order=True)

    # Step 6: Continue with existing pipeline (chunking, embedding, Qdrant)
    chunks = await create_chunks(all_elements)
    embeddings = await generate_embeddings(chunks)
    await store_in_qdrant(chunks, embeddings)

    return IngestionResult(pages=page_count, chunks=len(chunks))
```

**Benefits:**
- Uses Python's built-in `ThreadPoolExecutor` (no new dependencies)
- GIL-friendly for I/O-bound operations (PDF parsing is I/O-heavy)
- Easy to configure worker count
- Graceful degradation if parallelism fails (fallback to sequential)

**Challenges:**
- Docling converter may not be thread-safe (need to test)
- Need to handle page ordering correctly
- Memory usage might increase temporarily (4 batches in memory)

---

### Approach 2: Process-Level Multiprocessing (ALTERNATIVE)

```python
from multiprocessing import Pool
from functools import partial

def ingest_pdf_multiprocess(
    pdf_path: Path,
    batch_size: int = 40,
    num_processes: int = 4
) -> IngestionResult:
    """Ingest PDF with process-level parallelism."""

    page_count = get_page_count(pdf_path)
    batches = create_page_batches(page_count, batch_size)

    with Pool(processes=num_processes) as pool:
        process_func = partial(
            process_page_batch,
            pdf_path=pdf_path,
            backend=PyPdfiumDocumentBackend
        )
        batch_results = pool.map(process_func, batches)

    all_elements = merge_batch_results(batch_results)
    # ... rest of pipeline
```

**Benefits:**
- True parallelism (bypasses GIL)
- Better CPU utilization for CPU-bound operations

**Challenges:**
- Requires picklable objects (Docling objects may not be picklable)
- Higher memory overhead (4 separate processes)
- More complex error handling
- Slower startup time (process creation overhead)

**Recommendation:** Start with Approach 1 (ThreadPoolExecutor), fall back to Approach 2 if GIL becomes bottleneck

---

## Implementation Plan

### Phase 1: Core Parallelization (2-3 hours)
1. Implement `create_page_batches()` function
2. Implement `process_page_batch()` with ThreadPoolExecutor
3. Implement `merge_batch_results()` with page order preservation
4. Add logging for parallel execution tracking

### Phase 2: Integration & Testing (1-2 hours)
5. Update `ingest_pdf()` to support `parallel=True` parameter
6. Add unit tests for batch creation and merging
7. Add integration test comparing sequential vs parallel output
8. Verify element count and order match

### Phase 3: Performance Validation (1-2 hours)
9. Run AC3: 10-page performance test
10. Run AC4: 160-page comprehensive test
11. Compare speedup vs Story 2.1 baseline
12. Document performance improvements

---

## Expected Performance Improvements

### Baseline (Story 2.1)
- **160-page PDF:** 13.3 minutes (799 seconds)
- **Breakdown:**
  - PDF parsing: ~7.1 min (426s)
  - Embedding: ~0.9 min (51s)
  - Chunking: ~0.5 min (30s)
  - Qdrant: ~0.2 min (12s)
  - Overhead: ~4.2 min (254s)

### With Page-Level Parallelism (4 workers, 40-page batches)

**Optimistic (2.5x target):**
- PDF parsing: 7.1 min / 4 workers = 1.8 min (108s)
- Embedding (unchanged): 0.9 min (51s)
- Chunking (unchanged): 0.5 min (30s)
- Qdrant (unchanged): 0.2 min (12s)
- Overhead (reduced): 2.0 min (120s) - parallelized model loading
- **Total:** ~5.3 minutes (320 seconds) - **2.5x speedup** ✅

**Conservative (1.7x target):**
- PDF parsing: 7.1 min / 3 workers = 2.4 min (143s) - accounting for overhead
- Embedding (unchanged): 0.9 min (51s)
- Chunking (unchanged): 0.5 min (30s)
- Qdrant (unchanged): 0.2 min (12s)
- Overhead (reduced): 3.0 min (180s)
- **Total:** ~7.0 minutes (416 seconds) - **1.9x speedup** ✅

**Both scenarios meet target:** 1.7-2.5x speedup ✅

---

## Risks & Mitigation

### Risk 1: Docling Converter Not Thread-Safe
**Impact:** High - parallelization won't work
**Probability:** Medium
**Mitigation:**
- Test with simple concurrent calls to `converter.convert()`
- If not thread-safe, create separate converter instance per thread
- Fallback: Use process-level parallelism (Approach 2)

### Risk 2: Memory Usage Spike
**Impact:** Medium - might exceed 3 GB target
**Probability:** Low-Medium
**Mitigation:**
- Monitor peak memory during parallel execution
- Reduce batch size if memory spikes (e.g., 40 → 20 pages)
- Process batches sequentially if memory exceeds 2.5 GB

### Risk 3: Page Order Not Preserved
**Impact:** High - chunking quality degrades
**Probability:** Low
**Mitigation:**
- Add explicit page ordering in merge function
- Unit test to verify page order matches sequential
- Integration test comparing chunk boundaries

### Risk 4: Overhead from Thread Creation
**Impact:** Low - minor performance hit
**Probability:** Medium
**Mitigation:**
- Use thread pool reuse (ThreadPoolExecutor default behavior)
- Benchmark thread creation overhead
- Adjust worker count based on benchmarks

---

## Success Criteria

**Story 2.2 is complete when:**
1. ✅ Page-level parallelism implemented and tested
2. ✅ 10-page PDF ingestion ≤20 seconds
3. ✅ 160-page PDF ingestion 5.3-7.8 minutes (1.7-2.5x speedup)
4. ✅ Table accuracy maintained at ≥97.9% (ideally 100%)
5. ✅ Memory usage <3 GB (ideally similar to Story 2.1 ~433 MB)
6. ✅ All integration tests passing

---

## Dependencies

- **Story 2.1:** ✅ COMPLETE (PyPdfium backend)
- **Python 3.11+:** ✅ Available
- **concurrent.futures:** ✅ Available (Python stdlib)

**No new dependencies required** ✅

---

## Next Steps After Story 2.2

**If Story 2.2 achieves 1.7-2.5x:**
- ✅ Epic 2 Phase 1 COMPLETE
- → Proceed to Epic 2 Phase 2A (Fixed Chunking + Metadata)

**If Story 2.2 falls short (<1.7x):**
- Investigate additional optimizations:
  - Parallel embedding generation
  - Batch Qdrant uploads
  - Reduce model loading overhead
- Consider alternative parallelization strategies

---

## Files to Modify

1. `raglite/ingestion/pipeline.py` - Add parallel processing logic
2. `tests/integration/test_pypdfium_ingestion.py` - Add parallel tests
3. `tests/integration/test_ac4_comprehensive.py` - Update for parallel validation
4. `docs/stories/story-2.2-completion-summary.md` - Document results (after completion)

---

**Status:** PLANNING
**Ready to Start:** ✅ YES (Story 2.1 complete)
**Estimated Duration:** 4-6 hours
**Target Completion:** Within 1 day

---

**Next Action:** Begin Phase 1 implementation (Core Parallelization)
