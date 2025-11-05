# Section 1 Quick Reference
## Pages 1-20 Data Extraction Guide

---

## Table Overview

### Pages 1-19: Traditional Tables (Phase 2.6 Ready)

| Page | Title | Use Case |
|--|--|--|
| **4** | Health & Safety KPI's | Safety metric queries (Frequency Ratio) |
| **5** | Currency Exchange Impact | FX impact analysis on financials |
| **6-7** | Main Financial Indicators | Core KPI queries (Revenue, EBITDA, Net Debt) |
| **8** | EBITDA Monthly Evolution | Monthly trend analysis |
| **9-11** | P&L Statement | Income statement queries |
| **10** | P&L Detail (Costs) | Cost component analysis |
| **11** | Cash Flow & Net Debt | Treasury and liquidity analysis |
| **14** | Turnover by Segment | Revenue by business unit |
| **15** | EBITDA by Segment | Profitability by business unit |
| **16** | Headcount Evolution | Employee count and HR metrics |
| **17-19** | CAPEX Analysis | Capital expenditure tracking |

### Page 20: TRANSPOSED Table (Phase 2.7 Required)

| Metric | Structure | Challenge |
|--|--|--|
| **Cost per Ton** | **Metrics in rows, Entities in columns** | **Requires inverted extraction logic** |

---

## Key Data Points (Sample Values)

### Consolidated Group (Aug-25 YTD)
```
Turnover:         496.6 M EUR
EBITDA:           128.8 M EUR  (+27.8% vs LY)
Net Debt:         344.4 M EUR
Headcount:        2,891 employees
Safety (Freq):    6.35 injuries/1M hours
```

### Regional Rankings (EBITDA YTD)
```
1. Portugal:      104.6 M EUR  (81.2% of total)
2. Brazil:         26.9 M EUR
3. Tunisia:         8.2 M EUR
4. Lebanon:         1.9 M EUR
5. Angola:          0.3 M EUR
```

### Cost per Ton Analysis (Page 20 - Transposed)
```
Portugal   Variable Cost: -23.4 EUR/ton (best)
Tunisia    Variable Cost: -29.1 EUR/ton (5.7 worse)
Lebanon    Variable Cost: -50.9 EUR/ton (worst)
Brazil     Variable Cost: -20.7 EUR/ton
```

---

## 10 Ground Truth Queries

### Easy Queries (Point Lookups)
```
Q1: What is Group EBITDA in August 2025?
    Answer: 128.8 M EUR (+27.8% vs LY)

Q2: What is Portugal's YTD turnover?
    Answer: 312.2 M EUR (+1.1% vs LY)

Q3: What is Brazil's variable cost per ton?
    Answer: -20.7 EUR/ton (transposed table)
```

### Medium Queries (Comparisons & Budget)
```
Q4: Compare variable costs - Portugal vs Tunisia
    Portugal: -23.4 EUR/ton
    Tunisia:  -29.1 EUR/ton (5.7 worse)

Q5: How did EBITDA compare to budget?
    Actual:   104.6 M EUR
    Budget:   108.9 M EUR
    Variance: -4.3 M EUR (-3.9%)

Q6: Which region had highest EBITDA?
    1. Portugal (104.6)
    2. Brazil (26.9)
    3. Tunisia (8.2)
```

### Hard Queries (Trends & Calculations)
```
Q7: What is Group EBITDA margin percentage?
    Calculation: 15.693 / 59.522 = 26.4%

Q8: What is EBITDA per employee for Portugal?
    11.442 / 1.164 = 9.83 K EUR per employee

Q9: What is the YoY EBITDA growth trend?
    Aug-24: 11.8 M EUR
    Aug-25: 15.7 M EUR
    Growth: +32.8%

Q10: Which entity has best unit EBITDA efficiency?
    Brazil: 25.1 EUR/ton (cement)
```

---

## Critical Issues to Avoid

### Entity Confusion
```
WRONG: "What is Portugal EBITDA?"
RIGHT: "What is Portugal Cement EBITDA?" or "Portugal total EBITDA YTD?"

Clarify level:
- Group (consolidated total)
- Region (Portugal, Angola, Tunisia, Lebanon, Brazil)
- Business (Cement, Ready-Mix, Aggregates, etc.)
```

### Period Mismatches
```
WRONG: Using Aug-25 month value = 11.4 M EUR
RIGHT: Using YTD Aug-25 = 104.6 M EUR

Always specify: Month? YTD? Budget? LY?
```

### Transposed Table Handling (Page 20)
```
WRONG: Treating "Variable Cost" as column header
RIGHT: Recognizing it as row label with entity columns

Table 13 uses inverted structure:
  Rows = Metrics (Variable Cost, Fixed Cost, etc.)
  Cols = Entities (Portugal, Tunisia, Lebanon, Brazil)
```

### Currency Issues
```
WRONG: Mixing EUR/ton with LCU/ton
RIGHT: Specifying currency in both query and answer

Page 20 shows both EUR and local currency versions:
  Portugal:  EUR/ton (1,000 EUR = 1)
  Tunisia:   TND/ton (×3.35 conversion)
  Lebanon:   LCU/ton (×1,000 conversion)
  Brazil:    BRL/ton (×6.32 conversion)
```

---

## Query Patterns

### Pattern 1: Simple Point Query
```
Query:  "What is [ENTITY] [METRIC] in [PERIOD]?"
Answer: [VALUE] [UNIT]

Example:
Q: "What is Portugal EBITDA YTD August 2025?"
A: "104,647 thousand EUR (104.6 M EUR)"
```

### Pattern 2: Comparison Query
```
Query:  "Compare [METRIC] between [ENTITY1] and [ENTITY2]"
Answer:
  Entity1: X
  Entity2: Y
  Difference: Y-X (better/worse/analysis)

Example:
Q: "Compare variable costs per ton, Portugal vs Tunisia"
A: "Portugal -23.4 EUR/ton, Tunisia -29.1 EUR/ton.
    Tunisia costs 5.7 EUR/ton higher (worse)."
```

### Pattern 3: Budget Variance Query
```
Query:  "[ENTITY] [METRIC] actual vs budget [PERIOD]"
Answer:
  Actual:     X
  Budget:     Y
  Variance:   X-Y (amount & %)
  Assessment: Better/Worse/On-target

Example:
Q: "How did Portugal EBITDA compare to budget?"
A: "Actual 104.6 M EUR vs Budget 108.9 M EUR,
    Variance -4.3 M EUR (-3.9%) WORSE than budget"
```

### Pattern 4: Transposed Table Query
```
Query:  "[METRIC] for [ENTITY] [PERIOD] from cost analysis"
Answer: [VALUE] [UNIT]
Note:   Requires Phase 2.7 detection

Example:
Q: "What is Tunisia's variable cost per ton in August?"
A: "-29.1 EUR/ton (from Cost per Ton table, page 20)"
```

---

## Data Extraction Checklist

### Before Extraction
- [ ] Confirm table location (page, row/column)
- [ ] Identify table type (Traditional or Transposed?)
- [ ] Note entity hierarchy level needed
- [ ] Specify time period precisely
- [ ] Check currency requirements

### During Extraction
- [ ] Verify header parsing (especially nested/complex)
- [ ] Confirm value source cell location
- [ ] Validate value format (integer, decimal, percentage)
- [ ] Check for negative values (especially costs)
- [ ] Note any null/missing data markers

### After Extraction
- [ ] Cross-reference against template data
- [ ] Validate calculation accuracy
- [ ] Confirm period matches query intent
- [ ] Check unit consistency
- [ ] Document any anomalies

---

## File References

**YAML Inventory:**
```
/Users/ricardocarvalho/DeveloperFolder/RAGLite/docs/ground-truth-review/section-1-inventory.yaml
```

**Analysis Summary:**
```
/Users/ricardocarvalho/DeveloperFolder/RAGLite/docs/ground-truth-review/section-1-analysis-summary.md
```

**PDF Source:**
```
/Users/ricardocarvalho/DeveloperFolder/RAGLite/docs/sample pdf/sections/section-01_pages-1-20.pdf
```

---

## Quick Stats

- **Pages Analyzed:** 1-20
- **Tables Found:** 13 total
- **Traditional Tables:** 12 (Pages 1-19)
- **Transposed Tables:** 1 (Page 20)
- **Sample Values:** 15 extracted
- **Ground Truth Queries:** 10 proposed
- **Entities:** 22+ business units
- **Time Periods:** 15+ period types
- **Coverage:** 85% estimated

---

*Quick Reference Guide - Section 1 Pages 1-20*
*Created: 2025-10-26*
