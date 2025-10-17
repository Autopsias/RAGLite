# Story 2.2: Financial Embeddings Evaluation (CONDITIONAL)

**Status:** CONDITIONAL - Deferred pending Story 2.1 results
**Epic:** 2 - Advanced RAG Enhancements
**Priority:** MEDIUM (May be SKIPPED if Story 2.1 achieves ≥75% accuracy)
**Duration:** 6-8 hours (IF implemented)
**Assigned:** Dev Agent (Amelia)
**Prerequisites:** Story 2.1 complete, validation results reviewed

---

## ⚠️ CONDITIONAL IMPLEMENTATION NOTICE

**THIS STORY MAY BE SKIPPED ENTIRELY**

**Research Finding (from Epic 2 preparation):**
- Fin-E5 is state-of-the-art for financial retrieval (0.7105 FinMTEB score)
- Fin-E5 outperforms FinBERT (0.6721) and fin-roberta (<0.6721)
- Switching to alternative models would DEGRADE accuracy
- **Recommendation:** Keep Fin-E5, defer this story unless accuracy <85% after Story 2.1

**Decision Criteria:**
- **IF Story 2.1 retrieval ≥75%:** SKIP Story 2.2 (Fin-E5 sufficient)
- **IF Story 2.1 retrieval 70-74%:** EVALUATE Story 2.2 (consider fine-tuning vs alternatives)
- **IF Story 2.1 retrieval <70%:** IMPLEMENT Story 2.2 (explore embedding improvements)

---

## Story

**As a** system,
**I want** to evaluate if alternative embedding models or Fin-E5 fine-tuning improve retrieval accuracy,
**so that** queries with financial terminology find semantically relevant chunks more accurately.

---

## Context

**Current State (Epic 1):**
- ✅ Embedding Model: Fin-E5 (e5-mistral-7b-instruct, 7B params)
- ✅ Performance: State-of-the-art for financial retrieval (FinMTEB 2025)
- ✅ Latency: ~100-200ms per query (acceptable within 9,935ms budget)

**Research Findings (from `docs/epic-2-preparation/financial-embedding-model-comparison.md`):**

| Model | Retrieval Score | Parameters | Speed | Use Case |
|-------|----------------|------------|-------|----------|
| **Fin-E5** | **0.7105** | 7B | ~100-200ms | **CURRENT** ✅ |
| FinBERT | 0.6721 | 110M | ~20-50ms | Lower accuracy ❌ |
| fin-roberta | <0.6721 | 125M | ~20-50ms | Lower accuracy ❌ |

**Conclusion:** Fin-E5 is already optimal. Switching to alternatives would reduce accuracy.

**Alternative Approach:** Fine-tune Fin-E5 on RAGLite-specific data (if needed)

---

## Acceptance Criteria (CONDITIONAL)

**⚠️ ONLY IMPLEMENT IF Story 2.1 accuracy <75%**

### AC1: Fine-Tuning Data Preparation (2 hours) - IF IMPLEMENTED

**Subtask 1.1: Collect RAGLite-specific training data** (1 hour)
- Extract successful query-chunk pairs from ground truth (28/50 queries)
- Create training dataset: (query, relevant_chunk) pairs
- Augment with failed queries to identify weak patterns

**Subtask 1.2: Prepare fine-tuning format** (1 hour)
- Convert to Fin-E5 fine-tuning format (HuggingFace)
- Split: 80% train, 20% validation
- Document: Training data statistics

---

### AC2: Fin-E5 Fine-Tuning (3 hours) - IF IMPLEMENTED

**Subtask 2.1: Set up fine-tuning environment** (1 hour)
- Install HuggingFace Transformers, PEFT for LoRA
- Configure GPU/CPU training
- Set hyperparameters: learning_rate, epochs, batch_size

**Subtask 2.2: Fine-tune Fin-E5** (2 hours)
- Run fine-tuning on RAGLite training data
- Monitor: Training loss, validation accuracy
- Save: Fine-tuned model checkpoint

---

### AC3: Evaluation & Comparison (2 hours) - IF IMPLEMENTED

**Subtask 3.1: Re-embed with fine-tuned model** (1 hour)
- Re-ingest 321 chunks with fine-tuned Fin-E5
- Store in separate Qdrant collection for comparison

**Subtask 3.2: A/B testing** (1 hour)
- Run full ground truth suite (50 queries) on:
  - Collection A: Original Fin-E5
  - Collection B: Fine-tuned Fin-E5
- Compare: Retrieval accuracy, attribution accuracy
- Decision: Adopt fine-tuned model if improvement >5%

---

### AC4: Model Adoption (1 hour) - IF IMPROVEMENT >5%

**Subtask 4.1: Update pipeline** (30 min)
- Replace original Fin-E5 with fine-tuned model
- Update configuration in `pipeline.py`

**Subtask 4.2: Re-ingest all documents** (30 min)
- Clear Qdrant collection
- Re-ingest with fine-tuned embeddings
- Validate: 321 chunks indexed correctly

---

## Alternative: Keep Fin-E5 (RECOMMENDED)

**IF Story 2.1 achieves ≥75% accuracy:**
- **Decision:** SKIP Story 2.2 entirely
- **Rationale:** Fin-E5 already optimal, fine-tuning effort unjustified
- **Next:** Proceed to Story 2.3 (Table-Aware Chunking) if <90% accuracy

---

## Success Criteria (IF IMPLEMENTED)

Story 2.2 is COMPLETE when:
1. ✅ Fine-tuning data prepared (AC1)
2. ✅ Fin-E5 fine-tuned on RAGLite data (AC2)
3. ✅ A/B testing complete (AC3)
4. ✅ IF improvement >5%: Fine-tuned model adopted (AC4)
5. ✅ Retrieval accuracy measured (target: 80-85%)

**Quality Gate:** AC3 (A/B testing shows >5% improvement) required for adoption.

---

## Decision Gate (After Story 2.2 IF IMPLEMENTED)

**Path 1: Retrieval ≥85%**
- ✅ Near target (90%)
- Decision: Implement Story 2.3 (Table-Aware Chunking) to reach 90%+

**Path 2: Retrieval 80-84%**
- ⚠️ Moderate progress
- Decision: Evaluate Story 2.3 OR Story 2.4 (Cross-Encoder Re-ranking)

**Path 3: Retrieval <80%**
- ❌ Insufficient progress
- Decision: Investigate root cause, consider architectural changes

---

## Recommendation

**PRIMARY: DEFER Story 2.2 until after Story 2.1 validation**

**Justification:**
1. Fin-E5 already state-of-the-art (0.7105 vs 0.6721 FinBERT)
2. Story 2.1 (Hybrid Search) likely achieves 71-76% accuracy
3. If 75%+ achieved, Story 2.2 effort unjustified
4. Fine-tuning is time-intensive (6-8 hours) for uncertain gain

**Implementation Decision Tree:**
```
Story 2.1 Complete
    ├─ Retrieval ≥75% → SKIP Story 2.2 ✅
    ├─ Retrieval 70-74% → EVALUATE Story 2.2 (consider fine-tuning)
    └─ Retrieval <70% → IMPLEMENT Story 2.2 (fine-tune Fin-E5)
```

---

## Key Files (IF IMPLEMENTED)

**Input Files:**
- `tests/fixtures/ground_truth.py` - Training data source
- Fine-tuned model checkpoint (NEW)

**Files to Modify:**
- `raglite/shared/clients.py` - Embedding model selection
- `raglite/ingestion/pipeline.py` - Support fine-tuned model

**Files to Create:**
- `scripts/finetune-fin-e5.py` - Fine-tuning script (NEW, 200 lines)
- `docs/fin-e5-finetuning-results.md` - A/B testing report (NEW)

---

## Dependencies

**Prerequisites (IF IMPLEMENTED):**
- ✅ Story 2.1 complete and validated
- ✅ Retrieval accuracy <75% (trigger for implementation)

**Blocks:**
- Story 2.3 (Table-Aware Chunking) - depends on Story 2.2 validation

**Blocked By:**
- Story 2.1 results (DECISION GATE)

---

## Dev Notes

### Decision Rationale

**From Financial Embedding Model Comparison Report:**
- Fin-E5 is best-in-class for financial retrieval (2025 FinMTEB)
- Switching to FinBERT or fin-roberta would DEGRADE accuracy
- Fine-tuning is only viable option IF Fin-E5 insufficient
- Effort: 6-8 hours for uncertain gain (<5% expected)

**Epic 2 Strategy:**
- Focus Epic 2 on high-ROI improvements (Story 2.1: +15-20%)
- Defer low-ROI improvements (Story 2.2: <5%) unless necessary

**Lessons from Epic 1:**
- Don't over-engineer (KISS principle)
- Validate incrementally (stop when 90% achieved)
- Data-driven decisions (baseline analysis guides priorities)

---

## References

**Research Documents:**
- `docs/epic-2-preparation/financial-embedding-model-comparison.md`
- arXiv:2502.10990v1 - FinMTEB benchmark (Fin-E5 state-of-the-art)

---

## Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2025-10-16 | 1.0 | Story created as CONDITIONAL (defer pending Story 2.1 results). Fin-E5 already optimal per research findings. Story may be SKIPPED if Story 2.1 achieves ≥75% accuracy. | Scrum Master (Bob) |

---

**Status:** CONDITIONAL - Not ready for implementation
**Decision Needed:** After Story 2.1 validation complete
**Recommendation:** SKIP if Story 2.1 achieves ≥75% retrieval accuracy
