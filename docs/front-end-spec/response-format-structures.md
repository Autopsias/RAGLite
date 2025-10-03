# Response Format Structures

## Response Format: Simple Factual Answer

**Purpose:** Deliver concise, accurate information with verifiable sources

**Structure:**
```
[2-3 paragraph synthesized answer addressing the query directly]

**Sources:**
- [Document Name], page [X], [Section Name]
- [Additional sources if multi-document]
```

**Example:**
```
Q3 2024 revenue was $6.2M, representing a 15% increase from Q2 2024 ($5.4M).
The primary drivers were increased enterprise contract renewals (up 25%) and
new customer acquisitions in the healthcare vertical.

The revenue breakdown shows: Enterprise segment $4.1M (66%), SMB segment $1.8M
(29%), and Professional Services $0.3M (5%).

**Sources:**
- Q3_2024_Financial_Report.pdf, page 3, Revenue Summary section
- Q3_2024_Financial_Report.pdf, page 8, Segment Analysis table
```

**Key Requirements:**
- Answer the question in first paragraph
- Provide relevant context/details in subsequent paragraphs
- Maximum 3 paragraphs (concise over comprehensive)
- Source attribution must include: document name, page number, section name
- Use bullet points for sources if multiple documents
- Financial figures always include units ($, %, etc.)

---

## Response Format: Multi-Document Comparison

**Purpose:** Clearly compare information across documents/time periods

**Structure:**
```
[1-2 paragraph summary of comparison highlighting key findings]

**Comparison:**
| Metric | [Period 1] | [Period 2] | Change |
|--------|------------|------------|--------|
| [Metric 1] | [Value] | [Value] | [+/- %] |
| [Metric 2] | [Value] | [Value] | [+/- %] |

[1 paragraph explaining variance or patterns]

**Sources:**
- [Period 1]: [Document Name], page [X], [Section]
- [Period 2]: [Document Name], page [X], [Section]
```

**Example:**
```
Marketing spend increased 30% from Q2 to Q3 2024 ($800K to $1.04M), but revenue
only grew 15%, suggesting potential efficiency concerns worth investigating.

**Comparison:**
| Metric | Q2 2024 | Q3 2024 | Change |
|--------|---------|---------|--------|
| Marketing Spend | $800K | $1.04M | +30% |
| Revenue | $5.4M | $6.2M | +15% |
| Customer Acquisition Cost | $1,200 | $1,850 | +54% |

The disproportionate increase in CAC suggests that while marketing spend increased,
conversion efficiency declined. Q3 campaigns focused on new vertical expansion which
typically has higher initial acquisition costs.

**Sources:**
- Q2 2024: Q2_Financial_Report.pdf, page 12, Marketing Analysis section
- Q3 2024: Q3_Financial_Report.pdf, page 15, Marketing Metrics table
```

**Key Requirements:**
- Lead with comparison summary (what's most important)
- Use tables for numerical comparisons (3-5 rows maximum)
- Include percentage changes or deltas in comparison
- Explain variance/patterns after presenting data
- Differentiated source citations per data point

---

## Response Format: Analytical Workflow Result

**Purpose:** Show multi-step analysis with transparent reasoning

**Structure:**
```
[1-2 paragraph executive summary of analysis findings]

**Analysis Process:**
1. [Step 1 description] → [Result]
2. [Step 2 description] → [Result]
3. [Step 3 description] → [Result]

**Key Findings:**
- [Finding 1 with supporting data]
- [Finding 2 with supporting data]
- [Finding 3 with supporting data]

**Interpretation:** [1-2 paragraphs explaining what findings mean and why they matter]

**Sources:**
- [List all documents/sections used across workflow steps]
```

**Example:**
```
YoY revenue growth from Q3 2023 to Q3 2024 was 45% ($4.3M to $6.2M), driven
primarily by enterprise segment expansion and improved retention rates.

**Analysis Process:**
1. Retrieved Q3 2023 revenue: $4.3M → Found in historical reports
2. Retrieved Q3 2024 revenue: $6.2M → Current quarter data
3. Calculated growth rate: ($6.2M - $4.3M) / $4.3M = 44.2% ≈ 45%
4. Analyzed variance drivers → Enterprise +65%, SMB +15%, Services +10%

**Key Findings:**
- Enterprise segment grew 65% YoY ($2.5M to $4.1M) - primary growth driver
- Customer retention improved from 88% to 93% - reduced churn impact
- New customer acquisition up 40% - expansion into healthcare vertical

**Interpretation:** The exceptional growth is sustainable based on strong enterprise
pipeline (3.2x coverage for Q4) and improved retention metrics. However, SMB growth
is lagging and may require focused attention in 2025 planning.

**Sources:**
- Q3_2023_Financial_Report.pdf, page 3, Revenue Summary
- Q3_2024_Financial_Report.pdf, page 3, Revenue Summary
- Q3_2024_Financial_Report.pdf, page 8, Segment Analysis
- Q3_2024_Financial_Report.pdf, page 22, Customer Metrics
```

**Key Requirements:**
- Executive summary first (busy users may not read full analysis)
- Numbered analysis steps show reasoning transparency
- Key findings as bullets (scannable, actionable)
- Interpretation explains business impact, not just math
- Comprehensive source list covering all workflow steps

---

## Response Format: Proactive Insight

**Purpose:** Surface strategic insights requiring attention

**Structure:**
```
**[Insight Category]: [Concise headline describing the insight]**

[1-2 paragraphs explaining the insight with supporting data and context]

**Impact:** [Severity/Priority level] - [Why this matters for business]

**Recommended Action:** [Specific next step or area to investigate]

**Supporting Data:**
- [Data point 1 with source]
- [Data point 2 with source]
```

**Example:**
```
**🚨 Risk Alert: Cloud Infrastructure Costs Trending 40% Over Budget**

Cloud infrastructure spending in Q3 2024 reached $420K against a budgeted $300K,
representing a 40% overrun. The trend has accelerated over the past 3 months
(July: +15%, August: +28%, September: +40%) while user growth only increased 12%
in the same period, suggesting inefficient resource allocation.

**Impact:** High Priority - If trend continues, FY2024 will exceed budget by $480K
and impact EBITDA margins by 3 percentage points.

**Recommended Action:** Conduct immediate infrastructure audit focusing on: (1) unused
compute resources in production environment, (2) data storage optimization opportunities,
(3) review of auto-scaling configurations.

**Supporting Data:**
- Q3 actual spend: $420K vs budget $300K (+40%) - Q3_Financial_Report.pdf, page 18
- Monthly trend: July +15%, Aug +28%, Sept +40% - Monthly_Expense_Tracker.xlsx
- User growth: 12% in Q3 - Q3_Product_Metrics.pdf, page 4
```

**Key Requirements:**
- Lead with category and compelling headline (risk/opportunity/anomaly)
- Use emoji indicators sparingly for severity (🚨 high risk, ⚠️ moderate, 💡 opportunity)
- Impact statement must quantify business consequence
- Recommended action must be specific and actionable
- Supporting data bullets with inline citations

---

## Response Format: Forecast Response

**Purpose:** Provide predictions with uncertainty and methodology transparency

**Structure:**
```
**Forecast: [Metric] for [Time Period]**

**Predicted Value:** [Value] ± [Confidence Interval]

[1-2 paragraphs explaining forecast basis and key assumptions]

**Forecast Methodology:**
- **Approach:** [LLM-based / Statistical / Hybrid]
- **Historical Data:** [Time range and data points used]
- **Confidence Level:** [High/Medium/Low] - [Reasoning]

**Key Assumptions:**
- [Assumption 1]
- [Assumption 2]

**How to Verify:** [Guidance on validating forecast when actuals available]

**Sources:**
- [List historical documents used for forecast]
```

**Example:**
```
**Forecast: Q4 2024 Revenue**

**Predicted Value:** $7.1M ± $1.1M (range: $6.0M - $8.2M)

Based on 6-month historical trend analysis, Q4 2024 revenue is forecasted at $7.1M,
representing 15% sequential growth from Q3. The forecast incorporates seasonal patterns
(Q4 historically 10-20% stronger due to enterprise year-end purchasing) and current
pipeline coverage of 2.8x target.

**Forecast Methodology:**
- **Approach:** Hybrid (Statistical trend + LLM pipeline analysis)
- **Historical Data:** Q1 2023 - Q3 2024 (7 quarters)
- **Confidence Level:** Medium - Wide range due to macro uncertainty and new vertical expansion

**Key Assumptions:**
- Enterprise pipeline converts at historical 35% rate
- No major customer churn events (retained top 10 customers)
- Healthcare vertical (new in Q3) contributes $500K-$800K
- Macro environment remains stable (no recession impact)

**How to Verify:** Compare against Q4 actuals when available in January 2025. Track
pipeline conversion rates weekly to validate assumption 1.

**Sources:**
- Historical revenue: Q1_2023 through Q3_2024 financial reports
- Pipeline data: Q3_2024_Sales_Pipeline.xlsx
- Seasonal patterns: FY2023_Annual_Report.pdf, page 34
```

**Key Requirements:**
- Lead with clear prediction and confidence interval (± value)
- Explain forecast basis in plain language
- Methodology transparency (approach, data, confidence reasoning)
- Assumptions must be testable/observable
- Verification guidance enables user to validate later
- Wide confidence intervals acceptable if uncertainty is high (honest prediction > false precision)

---
