# Performance Considerations

## Response Time Targets (from PRD)

**Critical Performance Goals:**

| Query Type | p50 Target | p95 Target | Notes |
|------------|------------|------------|-------|
| Simple factual query | <5 seconds | <10 seconds | Direct retrieval + synthesis |
| Multi-document synthesis | <8 seconds | <15 seconds | Multiple vector searches |
| Complex analytical workflow | <20 seconds | <30 seconds | Multi-agent orchestration |
| Forecast generation | <10 seconds | <20 seconds | Historical data extraction + prediction |
| Proactive insights | <15 seconds | <30 seconds | Anomaly detection + trend analysis |

## UX Impact of Performance

**Response Time Psychology:**

- **<2 seconds:** Feels instant, ideal for simple queries
- **2-5 seconds:** Acceptable, maintain user engagement with "thinking" indicator
- **5-10 seconds:** Requires feedback - show progress ("Retrieving data...", "Analyzing...")
- **10-30 seconds:** Critical threshold - must show detailed progress or risk abandonment
- **>30 seconds:** Workflow timeout - graceful degradation to simpler response

**Performance-Driven UX Patterns:**

1. **Progressive Response Delivery**
   - For long-running workflows, consider streaming partial results
   - Show retrieval results first, then analysis, then synthesis
   - User sees value immediately, full answer builds progressively

2. **Transparent Processing Indicators**
   - Simple queries: No indicator needed if <3 seconds
   - Complex workflows: Show steps ("Step 1/4: Retrieving Q3 data...")
   - Agentic workflows: Indicate which agent is active ("Analysis Agent calculating...")

3. **Caching Strategy** (for Architect)
   - Cache frequent queries (e.g., "What was Q3 revenue?")
   - Cache embeddings for common query patterns
   - Invalidate cache on document updates

4. **Graceful Degradation on Timeout**
   - 30-second hard timeout for workflows
   - Return partial results with explanation rather than complete failure
   - Offer retry or simplified alternative

## Design Decisions for Performance

**Conciseness Drives Speed:**
- 3-paragraph maximum for simple answers (less LLM token generation)
- Limit comparison tables to 5 rows (focused, faster to generate)
- Top 3-5 insights only (not exhaustive lists)

**Structured Formats Optimize Processing:**
- Consistent response templates reduce LLM "thinking" time
- Bullet points faster to generate than narrative paragraphs
- Tables pre-structured (less formatting decisions for LLM)

**Source Attribution Placement:**
- Sources at end of response (doesn't slow initial answer delivery)
- Allows synthesis to complete before citation lookup in some architectures

---
