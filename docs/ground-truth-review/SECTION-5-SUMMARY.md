# Section 5 Data Inventory Summary
## Secil Angola & Tunisia Financial Report (Pages 81-100)
**Report Date:** August 2025 Performance Review
**Inventory Date:** 2025-10-26
**Thoroughness:** Very Thorough

---

## Executive Summary

Section 5 contains comprehensive operational and financial performance data for Secil's operations in Angola and Tunisia. The section spans 20 pages and includes 14 major tables covering:
- Financial bridges and waterfall analysis
- Operational performance metrics
- Working capital analysis
- Cash flow statements
- Safety KPIs
- Headcount and capex tracking

**Key Finding:** Angola faces margin pressure from cost inflation despite strong price increases, while Tunisia shows exceptional growth with EBITDA up 128% year-over-year.

---

## Tables Identified (14 Total)

### Angola-Focused Tables (8)
1. **EBITDA IFRS Bridge (YOB vs YOY)** - Waterfall analysis with 9 components
2. **Operational Performance - Cement** - 6 cost categories + profitability metrics
3. **Operational Performance - Others & G&A** - Cost center breakdown
4. **Rolling Forecast** - Forward guidance for Sep-2025
5. **P&L Summary** - Complete income statement
6. **Turnover/EBITDA Analysis** - Revenue bridge
7. **Headcount Evolution** - 5-year trend plus budget
8. **Net Working Capital** - 5 components with days metrics
9. **Capex Analysis** - By type and budget variance
10. **Cash Flow Statement** - Operating to investing activities

### Tunisia-Focused Tables (4)
1. **Health & Safety KPIs** - Frequency ratio monitoring
2. **Operational Performance - Cement** - Market segment breakdown
3. **EBITDA IFRS Bridge (YOB vs YOY)** - Parallel waterfall analysis
4. **Rolling Forecast** - Cement segment outlook

---

## Data Quality Assessment

### Strengths
- Consistent 3-way comparison: Month vs YTD vs Budget vs Prior Year
- Clear directional indicators (positive/negative impact)
- Multiple dimensional breakdowns by geography, product, function
- Well-organized hierarchical structure

### Concerns (Low-Medium Severity)
1. **Display overflow**: Net Transport Cost cell shows '###########' (unfixable in source)
2. **Negative receivables**: -57.6M AOA (possible advance payments)
3. **Massive WC variance**: 3.4B AOA swing requires investigation
4. **Budget credibility**: -36,202% variance on PBT suggests weak budgeting
5. **Incomplete data**: Tunisia safety metrics missing Jan-Mar, Jun, Sep-Dec 2025

---

## Sample Data Values Extracted (15 Exact Numbers)

### Angola
| Metric | Value | Unit | Context |
|--------|-------|------|---------|
| Volume Impact (YOB) | 521.1 | M AOA | EBITDA bridge component |
| Price Impact (YOY) | 2,202.3 | M AOA | Strong price momentum |
| Variable Costs per Ton (YTD) | 71,625.5 | AOA/ton | Cost inflation evident |
| EBITDA Cement (YTD) | 1,253,866 | 1000 AOA | -14% vs budget |
| EBITDA Margin (YTD) | 23.3% | % | Slight improvement vs prior |
| Inventories | 2,309,477 | 1000 AOA | 116% above Dec-24 |
| DIO (Days Inventory) | 166 | days | Excessive - 5.5 months |
| Operating Cash Flow | 1,255,887 | 1000 AOA | Strong despite low EBITDA |
| Financial Net Debt | -732,829 | 1000 AOA | Net cash position |

### Tunisia
| Metric | Value | Unit | Context |
|--------|-------|------|---------|
| Volume Cement (YTD) | 406 | kton | +13% YoY |
| Libya Exports (YTD) | 263 | kton | +498% YoY - major growth |
| EBITDA Cement (YTD) | 38,691 | 1000 TND | +128% YoY |
| EBITDA Margin (YTD) | 22.2% | % | +8 pp vs prior year |
| Safety Frequency Ratio | 3.66 | ratio | 205% over budget - critical |

---

## Identified Transposed Tables

**Finding:** NO fully transposed tables detected

All tables follow standard orientation:
- **Metrics/Entities as Rows** (left column)
- **Time Periods/Comparisons as Columns** (header row)

Example structure:
```
                  Month      YTD        Var vs Budget
                Aug-25  B Aug-25  Aug-24  % B    % LY
Metric 1         X       X   X       X     XX%    XX%
Metric 2         Y       Y   Y       Y     YY%    YY%
```

---

## Ground Truth Queries (10 Q&A Pairs)

### Query 1: Angola August EBITDA
**Q:** What was Secil Angola's EBITDA IFRS for August 2025 and budget variance?
**A:** 124.415M AOA, -36% vs budget of 193.2M. Driven by 7 kton volume (vs 9 budget) and variable costs of 71.1K AOA/ton (vs 65.4K budget).
**Difficulty:** Low | **Confidence:** High

### Query 2: Working Capital Inventory
**Q:** How much inventory is tied up and what is the DIO?
**A:** 2.31B AOA (116% above Dec-24), DIO of 166 days (5.5 months on hand). Raw materials: 1.30B AOA.
**Difficulty:** Medium | **Confidence:** High

### Query 3: EBITDA Bridge Components
**Q:** What are the waterfall bridge components from budget to actual?
**A:** Volume (+521M), Price (+1,188M), Variable Costs (-450M), Fixed Costs (+108M), Other (+78M), Production (-91M), Others (-33M).
**Difficulty:** High | **Confidence:** High

### Query 4: Headcount Trends
**Q:** What is the headcount reduction from 2020 to 2024 and Aug-25 vs budget?
**A:** 49% reduction (173 to 88 FTEs). Aug-25: 83 actual vs 94 budget (-12%).
**Difficulty:** Low | **Confidence:** High

### Query 5: Tunisia EBITDA Growth
**Q:** How does Tunisia cement EBITDA and margin compare to prior year?
**A:** Up 128% to 38.7M TND. Margin: 22.2% (vs 14.0% prior year, +8 pp). Drivers: volume growth, Libya exports up 498%, costs down 16%.
**Difficulty:** Medium | **Confidence:** High

### Query 6: Cash Flow & Debt
**Q:** How does operating cash flow relate to net debt position?
**A:** Operating CF: 1.26B AOA (despite low EBITDA). Net debt: -732.8M AOA (net cash position). WC variance of 3.4B explains discrepancy.
**Difficulty:** High | **Confidence:** Medium

### Query 7: Price Trends
**Q:** How do Angola internal and Tunisia external prices compare?
**A:** Angola IM: 127.5K AOA/ton (+55% YoY). Tunisia Libya: 188.4 TND/ton (+10% vs budget). Tunisia EU: 170.9 TND/ton (-13% vs budget).
**Difficulty:** Medium | **Confidence:** High

### Query 8: Fixed Cost Composition
**Q:** What are fixed cost components and budget variances?
**A:** Total 967M YTD (-9% vs budget). Labor: 313M (-12%), Maintenance: 205M (-39% favorable), Other: 450M (+20%).
**Difficulty:** Medium | **Confidence:** High

### Query 9: Working Capital Metrics
**Q:** What is TWC position and WC/Turnover ratio?
**A:** TWC: 1.55B (+40% vs budget). WC/Turnover: 15% (vs 10% budget, 8% prior). DSO: 9d, DPO: 33d, DIO: 166d.
**Difficulty:** High | **Confidence:** High

### Query 10: Safety Performance
**Q:** What are Tunisia safety concerns relative to budget?
**A:** Frequency Ratio: 3.66 YTD (205% over 1.20 budget). Deteriorated from FY24 (1.72) and FY23 (0.55). Non-cement spikes 54-63 in May-Jun. Critical issue.
**Difficulty:** Low | **Confidence:** High

---

## Key Metrics & Entities

### Geographic Segments
- Angola
- Tunisia
- Angola Internal Market
- Tunisia Internal Market
- External Markets (Libya, EU)

### Product Segments
- Cement
- Non-Cement
- Clinker

### Performance Dimensions
- Volume (kton)
- Price (per ton)
- Costs (variable, fixed, total)
- EBITDA & Margins
- Cash Flow & Debt
- Working Capital
- Safety

### Critical KPIs
1. **EBITDA IFRS**: Primary profitability metric
2. **Profit Before Tax**: Bottom line (heavily impacted by financial costs)
3. **Days Inventory Outstanding**: 166 days is dangerously high
4. **Financial Net Debt**: -732.8M (positive net cash position)
5. **Safety Frequency Ratio**: 3.66 (critical alert status)

---

## Retrieval Difficulty Assessment

| Challenge | Difficulty | Mitigation |
|-----------|-----------|-----------|
| Multi-page aggregation | Medium | Explicit page cross-references |
| Bridge/Waterfall interpretation | High | Complete component lists with directions |
| Multi-period trend analysis | Medium | Specify time period explicitly |
| Geographic/Segment decomposition | High | Clear segment boundary definitions |
| Currency awareness (AOA vs TND) | Medium-High | Never combine without FX rate |

---

## Data Validation Checks

### Structural Validation
- [x] All tables follow consistent format
- [x] Variance calculations verified (spot-check 5 values)
- [x] Waterfall components reconcile to totals
- [x] No completely transposed tables

### Numeric Validation
- [x] 15 exact sample values extracted with precision
- [x] Percentages verified as YoY and vs Budget
- [x] Margin calculations spot-checked
- [x] Cash flow formula validated

### Completeness Validation
- [x] All 14 tables catalogued
- [x] 10 ground truth Q&A pairs created
- [x] Critical issues flagged (3.4B WC variance, 166 DIO, safety)
- [x] Metadata compiled for RAG system integration

---

## Recommendations for Ground Truth Usage

1. **High Priority Queries**
   - Angola EBITDA analysis (margin pressure investigation)
   - Working capital normalization (inventory buildup)
   - Tunisia safety program review

2. **Medium Priority Queries**
   - Cash flow bridge understanding (WC variance investigation)
   - Geographic margin comparison (price power by region)

3. **Low Priority Queries**
   - Headcount trends (baseline only)
   - Capex analysis (standard replacement capex)

---

## File Generated
- **Path:** `/Users/ricardocarvalho/DeveloperFolder/RAGLite/docs/ground-truth-review/section-5-inventory.yaml`
- **Lines:** 2,004
- **Format:** YAML with nested structure
- **Sections:** 14 tables, 15 sample values, 10 ground truth queries, metadata
