# User Guide: Understanding Graceful Degradation

**For:** End users of RAGLite's analytical query tools via MCP (Model Context Protocol)
**Last Updated:** 2025-11-18 (Story 3.7)

---

## What is Graceful Degradation?

RAGLite's analytical query system uses advanced AI agents to analyze your financial documents. Sometimes, these agents may experience delays or temporary issues. **Graceful degradation** means RAGLite will automatically adjust to provide you with the best possible answer, even if not all features are available.

**You'll always get a response** — RAGLite never fails silently.

---

## How It Works: The 4-Tier Response System

RAGLite uses a 4-tier system to ensure you always get useful information:

### ✅ Tier 1: Full Analysis (Best Experience)

**What you get:**
- Complete AI-powered analysis of your financial documents
- Synthesized answer with proper citations
- High confidence in accuracy
- Reasoning steps showing how the answer was derived

**Example:**
```
Query: "Compare Q3 revenue to Q4 and explain the variance"

Answer: "Q3 revenue was €5.2M compared to Q4's €6.1M, representing a 17%
         increase. This variance is primarily due to seasonal holiday sales
         in Q4 (per Annual Report, page 12) and the launch of Product X
         in November (per Earnings Call Transcript, page 5)."

Confidence: High
Sources: Annual_Report_2024.pdf (page 12), Earnings_Call_Q4.pdf (page 5)
```

---

### ⚠️ Tier 2: Partial Analysis (Good Experience)

**What you get:**
- Retrieved documents and key facts
- Basic analysis without full synthesis
- Medium confidence
- Helpful error message explaining what happened

**When it happens:**
- AI analysis service experiences delays
- Synthesis step times out (>15 seconds)
- Temporary API issues

**Example:**
```
Query: "Calculate YoY revenue growth from 2023 to 2024"

Answer: "We found relevant financial data:
         - 2023 Revenue: €18.5M (Annual_Report_2023.pdf, page 8)
         - 2024 Revenue: €22.1M (Annual_Report_2024.pdf, page 8)

         Our analysis system experienced delays, but based on these figures,
         you can calculate a 19.5% YoY growth."

Confidence: Medium
Limitations: "Unable to complete full synthesis due to processing delays"
Suggestion: "Try a simpler query like 'What was Q3 revenue?' or break into smaller questions"
```

---

### ⚠️ Tier 3: Document Search Only (Acceptable Experience)

**What you get:**
- Raw document excerpts from your query
- No AI analysis or synthesis
- Low confidence
- Essentially the same as Epic 2 simple search

**When it happens:**
- Multiple AI agents timeout
- Retrieval succeeds but analysis fails
- Analysis service completely unavailable

**Example:**
```
Query: "Show financial metrics for 2024"

Answer: "Found 5 relevant documents:

1. Annual_Report_2024.pdf (page 8):
   'Total Revenue: €22.1M, EBITDA: €5.8M, Operating Margin: 26.2%'

2. Q4_Results_2024.pdf (page 3):
   'Q4 Revenue: €6.1M, representing 27.6% of annual revenue'

[... 3 more excerpts ...]"

Confidence: Low
Limitations: "Unable to provide analysis, showing raw documents"
```

---

### ❌ Tier 4: Basic Search (Minimal Experience)

**What you get:**
- Simple search results (fallback to basic RAG)
- No AI orchestration or analysis
- Helpful error message
- Alternative query suggestions

**When it happens:**
- Complete system timeout (>30 seconds)
- Database connection issues
- All AI agents fail
- Critical system errors

**Example:**
```
Query: "Analyze revenue trends and forecast next quarter"

Answer: "Our advanced analysis system is currently experiencing issues.
         Here are the documents we found related to your query:

         - Annual_Report_2024.pdf
         - Q4_Results_2024.pdf
         - Revenue_Forecast_Model.xlsx"

Confidence: None
Limitations: "Advanced analysis unavailable, using basic search"
Suggestion: "Please wait a moment and try again, or try a simpler query like
             'What was Q4 revenue?'"
```

---

## Common Error Messages (User-Friendly)

You'll never see technical error messages like `asyncio.TimeoutError` or `ConnectionError`. Instead, RAGLite provides clear, actionable messages:

### Processing Delays
**What you'll see:**
> "Our analysis system is experiencing delays, but we found some results."

**What it means:** The AI agents took longer than expected (>15 seconds per agent)

**What to do:**
- Your partial results are still useful
- Try breaking your query into simpler parts
- Example: Instead of "Calculate YoY revenue growth with variance explanation", try "What was 2024 revenue?" then "What was 2023 revenue?"

---

### Service Temporarily Unavailable
**What you'll see:**
> "Our AI service is temporarily unavailable. We've provided partial results based on available data."

**What it means:** Claude or Mistral API is experiencing issues

**What to do:**
- Wait 30-60 seconds and try again
- The issue is usually temporary
- Your query will work normally once service resumes

---

### Database Connectivity Issues
**What you'll see:**
> "We're experiencing database connectivity issues, but retrieved some results."

**What it means:** Qdrant vector database is temporarily unreachable

**What to do:**
- Wait a moment and retry
- Use simpler queries that require fewer database lookups
- Contact support if the issue persists

---

### System Taking Longer Than Usual
**What you'll see:**
> "Our advanced analysis system is taking longer than usual. Here are basic search results."

**What it means:** Workflow exceeded 30-second timeout

**What to do:**
- Your query may be too complex for quick processing
- Simplify your query or break it into parts
- Example: Instead of "Compare revenue, EBITDA, and margins across Q1-Q4 with explanations", ask "What was Q3 EBITDA?" first

---

## Tips for Better Results

### 1. Start Simple, Then Add Complexity
```
❌ Complex: "Analyze YoY revenue growth trends from 2020-2024 with seasonal
            adjustments and explain variance drivers for each quarter"

✅ Simple:   "What was revenue in 2024?"
            "What was revenue in 2023?"
            "Calculate the YoY growth percentage"
```

### 2. One Question at a Time
```
❌ Multiple: "Show Q3 revenue, EBITDA, operating margin, and compare to Q4"

✅ Focused:  "What was Q3 revenue?"
            (then) "What was Q4 revenue?"
            (then) "Compare Q3 and Q4 revenue"
```

### 3. Use Specific Terms
```
❌ Vague:    "Show me financial data"

✅ Specific: "What was Q3 2024 revenue?"
```

### 4. If You Get a Timeout, Simplify
When you see "experiencing delays" or "taking longer than usual":
- Remove qualifiers like "explain why" or "show trends"
- Ask for raw numbers first, then ask for analysis
- Break multi-step questions into separate queries

---

## What RAGLite Tracks Behind the Scenes

To ensure quality service, RAGLite tracks workflow performance:

- **Tier 1 Success Rate:** Target ≥95% (full orchestration works)
- **Tier 2 Fallback Rate:** Target <5% (partial results)
- **Tier 4 Failure Rate:** Target <0.1% (complete degradation)

If you frequently see Tier 3 or Tier 4 responses, please contact support — this helps us identify and fix systemic issues.

---

## FAQ

### Q: Will my query fail if AI agents have issues?
**A:** No. RAGLite's graceful degradation ensures you always get a response, even if some features are unavailable.

### Q: What's the difference between Tier 2 and Tier 3?
**A:**
- **Tier 2:** You get analyzed facts and key information (partial analysis)
- **Tier 3:** You get raw document excerpts without analysis

### Q: Why do I sometimes get "experiencing delays"?
**A:**
- Complex queries require more processing time
- AI services (Claude, Mistral) may have temporary slowdowns
- Large document sets take longer to analyze

### Q: How can I avoid timeouts?
**A:**
1. Start with simpler queries
2. Break complex questions into parts
3. Use specific terminology
4. Avoid asking for multiple metrics in one query

### Q: What if I keep getting Tier 4 responses?
**A:** Contact support. Persistent Tier 4 responses indicate a systemic issue we need to investigate.

### Q: Can I disable graceful degradation and just get errors?
**A:** No. Graceful degradation is built-in to ensure you always get useful information, even during system issues.

---

## Getting Help

If you experience persistent issues or have questions:

1. **Check your query complexity** — Try simplifying first
2. **Retry after 30-60 seconds** — Many issues are transient
3. **Review error messages** — They include actionable suggestions
4. **Contact support** — Especially if seeing frequent Tier 3/4 responses

---

## Technical Details (Optional)

For users interested in the technical implementation:

- **Workflow Timeout:** 30 seconds total
- **Per-Agent Timeout:** 15 seconds each (Retrieval, Analysis, Synthesis)
- **Error Classification:** Automatic detection of timeout, connection, API, and unexpected errors
- **Metrics Tracking:** All degradation events logged for quality monitoring

See `docs/architecture/epic-3-orchestration-design.md` for full technical documentation.

---

**Last Updated:** 2025-11-18
**Story:** 3.7 - Graceful Degradation for Workflow Failures
**Version:** 1.0
