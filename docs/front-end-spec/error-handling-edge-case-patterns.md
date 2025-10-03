# Error Handling & Edge Case Patterns

## Error Pattern: Ambiguous Query

**Trigger:** Query lacks specificity (time period, entity, or metric unclear)

**User Experience:** System asks clarifying question rather than guessing

**Response Format:**
```
I need clarification to provide an accurate answer:

**Your question:** "[User's original query]"

**What I need to know:**
- [Clarifying question 1] (e.g., "Which quarter did you mean?")
- [Clarifying question 2 if applicable]

**Suggestions:** [Provide 2-3 example specific questions they could ask]
```

**Example:**
```
I need clarification to provide an accurate answer:

**Your question:** "What was the marketing spend?"

**What I need to know:**
- Which time period? (Q1, Q2, Q3, or Q4 2024?)
- Which marketing category? (Digital, Events, Content, or Total?)

**Suggestions:**
- "What was Q3 2024 total marketing spend?"
- "Compare Q2 vs Q3 2024 digital marketing spend"
- "Show all Q3 2024 marketing categories"
```

**Key Requirements:**
- Never guess when ambiguous - always ask
- Repeat user's question to confirm understanding
- Provide specific examples of how to rephrase
- Limit clarifying questions to 2-3 (not overwhelming)

---

## Error Pattern: No Relevant Data Found

**Trigger:** Vector search returns no relevant chunks OR required document missing

**User Experience:** Explain what's missing and suggest alternatives

**Response Format:**
```
I couldn't find information to answer your question.

**What I searched for:** [Interpretation of user's query]

**Why no results:**
- [Reason 1: e.g., "No documents contain Q4 2024 data yet"]
- [Reason 2: e.g., "The metric you asked about isn't tracked in available documents"]

**What you can do:**
- [Alternative 1: e.g., "Try asking about Q3 2024 instead"]
- [Alternative 2: e.g., "I can show you related metrics: [list]"]

**Available data:** [Brief summary of what IS available that's related]
```

**Example:**
```
I couldn't find information to answer your question.

**What I searched for:** Q4 2024 revenue forecasts

**Why no results:**
- Q4 2024 hasn't completed yet, so no actual revenue data is available
- Forecast data for Q4 hasn't been generated (requires historical trend analysis setup)

**What you can do:**
- Ask about Q3 2024 actual revenue instead
- I can analyze Q1-Q3 2024 revenue trends to discuss likely Q4 patterns
- Request a revenue forecast (this will trigger forecast generation if data is sufficient)

**Available data:** I have complete financial data through Q3 2024, including revenue,
expenses, and segment performance across all quarters of 2024.
```

**Key Requirements:**
- Be specific about what's missing (don't just say "no data")
- Explain WHY data isn't available (timing, scope, etc.)
- Provide actionable alternatives (2-3 options)
- Show what IS available to help user pivot

---

## Error Pattern: Insufficient Historical Data (Forecast/Trend)

**Trigger:** User requests forecast/trend but insufficient data points exist

**User Experience:** Explain data requirements and provide partial analysis if possible

**Response Format:**
```
I cannot generate a reliable [forecast/trend analysis] due to insufficient historical data.

**Requirements:**
- **Needed:** [X data points / Y time periods]
- **Available:** [What we actually have]
- **Gap:** [What's missing]

**Partial Analysis Available:**
[Provide whatever analysis IS possible with available data]

**How to improve:**
- [Action to get better results, e.g., "Add historical documents from 2023"]
- [Timeline info, e.g., "After 2 more quarters, forecasting will be more reliable"]
```

**Example:**
```
I cannot generate a reliable revenue forecast due to insufficient historical data.

**Requirements:**
- **Needed:** Minimum 6 quarters of revenue data for seasonal pattern analysis
- **Available:** 3 quarters (Q1-Q3 2024)
- **Gap:** Missing 3+ quarters of historical data

**Partial Analysis Available:**
Based on available Q1-Q3 2024 data, I can observe:
- Sequential growth averaging 12% per quarter
- Q3 showed acceleration to 15% growth vs Q2
- Enterprise segment driving majority of growth (60%+ contribution)

**How to improve:**
- Add 2023 financial reports to enable year-over-year analysis and seasonal patterns
- After Q4 2024 completes (4 quarters total), I can provide directional forecasts
- For now, I can extrapolate simple trend: Q4 likely $6.8-7.4M if Q3 growth continues
```

**Key Requirements:**
- Be transparent about minimum data requirements
- Show exactly what's missing (numerical gap)
- Provide whatever partial analysis IS possible (don't just refuse)
- Give roadmap to better results (what data to add, when it'll improve)

---

## Error Pattern: Conflicting Information

**Trigger:** Multiple sources provide contradictory information

**User Experience:** Flag conflict, present all versions with sources, explain discrepancy if possible

**Response Format:**
```
⚠️ I found conflicting information across documents.

**Your question:** "[User's query]"

**Conflicting Data:**
- **Version 1:** [Value/statement] (Source: [Document], page [X])
- **Version 2:** [Value/statement] (Source: [Document], page [X])

**Possible reasons for discrepancy:**
- [Reason 1, e.g., "Different time periods or calculation methods"]
- [Reason 2, e.g., "One may be preliminary, other final"]

**Recommendation:** [Suggest which version to trust or how to resolve]
```

**Example:**
```
⚠️ I found conflicting information across documents.

**Your question:** "What was Q3 2024 marketing spend?"

**Conflicting Data:**
- **Version 1:** $1.04M (Source: Q3_Financial_Report.pdf, page 15)
- **Version 2:** $980K (Source: Q3_Budget_Variance.xlsx, Marketing tab)

**Possible reasons for discrepancy:**
- Budget variance report may show budgeted amount ($980K) vs. actual spend ($1.04M)
- Timing difference: report dated Oct 15, variance sheet dated Sept 30
- Different expense categorization (some costs may be allocated differently)

**Recommendation:** The official financial report ($1.04M) is likely the authoritative
actual spend. The variance sheet shows you exceeded budget by $60K (+6%). Verify with
the document dates and confirm if $980K was the budget vs. $1.04M actual.
```

**Key Requirements:**
- Use warning indicator (⚠️) to flag conflicts
- Present ALL conflicting versions with equal prominence
- Provide sources for each version
- Hypothesize WHY conflict exists (help user resolve)
- Recommend most authoritative source when possible

---

## Error Pattern: Agentic Workflow Failure

**Trigger:** Multi-step workflow times out or agent fails

**User Experience:** Graceful degradation with partial results or simpler answer

**Response Format:**
```
⚠️ Complex analysis workflow encountered an issue. Providing simplified response instead.

[Simpler retrieval-based answer to original question]

**What happened:**
- Attempted: [Description of complex workflow that failed]
- Issue: [Brief explanation of failure]
- Fallback: [Explanation of simpler approach used]

**Limited scope:**
[Note any limitations of the simplified response vs. intended analysis]

**Try instead:** [Suggest simpler question or manual approach]
```

**Example:**
```
⚠️ Complex analysis workflow encountered an issue. Providing simplified response instead.

Q3 2024 revenue was $6.2M, up 15% from Q2 ($5.4M). Enterprise segment contributed
$4.1M (66% of total), SMB $1.8M (29%), and Services $0.3M (5%).

**What happened:**
- Attempted: Multi-step variance analysis comparing Q2 vs Q3 with driver decomposition
- Issue: Analysis agent timeout after 30 seconds during variance calculation step
- Fallback: Retrieved basic revenue data using direct search instead

**Limited scope:**
This response includes revenue figures but lacks the detailed variance driver analysis
(why enterprise grew 25%, SMB only 10%, etc.) that the full workflow would provide.

**Try instead:**
- Ask specific questions: "Why did enterprise revenue grow in Q3?"
- Manual analysis: Review Q3 report pages 8-12 for segment details
- Retry workflow: Complex analysis may succeed on retry or with narrower scope
```

**Key Requirements:**
- Always provide SOME answer (never complete failure)
- Explain what was attempted and why it failed
- Be transparent about limitations of fallback response
- Offer alternatives (retry, manual approach, narrower question)
- Log failures for system improvement

---

## Error Pattern: LLM API Failure

**Trigger:** LLM synthesis fails (API error, timeout, rate limit)

**User Experience:** Return raw retrieved chunks with sources, explain synthesis unavailable

**Response Format:**
```
⚠️ Answer synthesis temporarily unavailable. Showing raw document excerpts instead.

**Relevant excerpts from documents:**

**Excerpt 1:**
[Raw chunk text from document]
(Source: [Document], page [X], [Section])

**Excerpt 2:**
[Raw chunk text from document]
(Source: [Document], page [X], [Section])

**Note:** I retrieved relevant information but couldn't synthesize it into a cohesive
answer due to a temporary processing issue. Please review the excerpts above, or retry
your question in a moment.
```

**Example:**
```
⚠️ Answer synthesis temporarily unavailable. Showing raw document excerpts instead.

**Relevant excerpts from documents:**

**Excerpt 1:**
"Q3 2024 total revenue reached $6.2M, representing 15% sequential growth from Q2.
Enterprise segment performance exceeded expectations with $4.1M contribution..."
(Source: Q3_Financial_Report.pdf, page 3, Executive Summary)

**Excerpt 2:**
"YoY comparison shows 45% growth from Q3 2023 ($4.3M) to Q3 2024 ($6.2M), primarily
driven by enterprise contract renewals and healthcare vertical expansion..."
(Source: Q3_Financial_Report.pdf, page 7, Year-over-Year Analysis)

**Note:** I retrieved relevant information but couldn't synthesize it into a cohesive
answer due to a temporary processing issue. Please review the excerpts above, or retry
your question in a moment.
```

**Key Requirements:**
- Provide the retrieved data even without synthesis
- Clearly mark as "raw excerpts" not polished answer
- Include full source attribution for each excerpt
- Suggest retry after brief wait
- Log failures for monitoring/debugging

---
