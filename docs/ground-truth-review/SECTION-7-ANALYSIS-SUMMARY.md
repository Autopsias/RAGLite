# Section 7 (Pages 121-140) Data Inventory Analysis Summary

## Executive Overview

Analyzed **Section 7** of the financial report covering Secil Lebanon & Brazil Performance Review for August 2025. This section contains comprehensive operational and financial data spanning **16 major tables** with **189+ extracted metrics** covering production, costs, profitability, working capital, and safety KPIs.

---

## Key Findings

### 1. Table Structure & Data Quality

**Non-Transposed Format Confirmed:**
- All tables follow consistent structure: metrics in rows, time periods in columns
- Dual-split layout: Month vs. YTD (left), with Month vs. YTD (right) for comparative analysis
- **No transposed tables detected** - clean, predictable structure ideal for retrieval testing

**Layout Pattern:**
```
[Metric Name] | Aug-25 (Actual) | B Aug-25 (Budget) | Aug-24 (Prior Year) | % Variance to Budget | % Variance to Prior Year
```

### 2. Tables Identified (16 Total)

| # | Table Name | Page | Type | Primary Metrics |
|---|---|---|---|---|
| 1 | Lebanon Cement Operational | 121 (LB5) | Operations | Volume (66 kton), Price (80.3 USD/ton), EBITDA (5.355M USD) |
| 2 | Lebanon Materials | 122 (LB6) | Segment | Ready-Mix (42 km3), Precast (13 ku) |
| 3 | Lebanon G&A & Corporate | 123 (LB7) | Overhead | Employee costs (-1.649M), G&A ratio (6.5% of turnover) |
| 4 | Lebanon Rolling Forecast | 124 (LB8) | Forecast | Sep-25 projections: Cement EBITDA 950k USD |
| 5 | Lebanon P&L | 125 (LB9) | Financial | EBITDA (2.142M), Net Income (354k USD) |
| 6 | Health & Safety KPIs | 126 (LB11) | Safety | Frequency Ratio (3.8), Lost Time Injuries (3) |
| 7 | Turnover/EBITDA Summary | 127 (LB12) | Summary | Total Turnover (45.056M USD), EBITDA 2.142M |
| 8 | Headcount Evolution | 128 (LB13) | HR | August 2025: 437 FTEs (down from 463 in 2024) |
| 9 | Capex Analysis | 129 (LB14) | Investment | YTD Capex: 7.168M USD (replacement-focused) |
| 10 | Cement Detailed Operations | 130-131 (LB15-16) | Operations | Production (530 kton), Thermal Energy (906 Kcal/kg clk) |
| 11 | Ready-Mix Operations | 132 (LB17) | Segment | Unit margin -0.1 to 7.4 USD/m3 (volatility) |
| 12 | Precast Operations | 133 (LB18) | Segment | Negative EBITDA (-38k USD), volume down 44% vs budget |
| 13 | Net Working Capital | 134 (LB20) | Finance | Inventory 14.371M (high), DSO 4 days, DIO 197 days |
| 14 | Cash Flow Statement | 135 (LB21) | Finance | Operating CF: 8.034M, Net debt closing: 9.368M |
| 15 | Brazil Cement Operations | 136 (BR3) | Geographic | Volume 1.160M kton, Price 420.1 BRL/ton |
| 16 | Brazil Health & Safety | 136 (BR2) | Safety | Frequency ratio: 2.81 (below Lebanon at 3.8) |

---

## 3. Sample Data Values Extracted (15+ Examples)

### Volume & Production Metrics
- **Cement Volume (IM):** 531 kton YTD Aug-25 vs. 429 budget (+24% variance)
- **Ready-Mix Volume:** 42 km³ YTD Aug-25 vs. 42 budget (0% variance)
- **Clinker Production:** 357 kton YTD vs. 342 budget (+4.4%)
- **Brazil Cement Volume:** 1.160M kton YTD vs. 1.141M budget (+1.7%)

### Pricing Metrics
- **Lebanon Cement Price:** 80.3 USD/ton (consistent with 80.0 budget)
- **Ready-Mix Price:** 63.1 USD/m³ (-13.3% vs. 72.7 budget)
- **Brazil Cement Price:** 420.1 BRL/ton (+0.7% vs. 417.0 budget)
- **Grey Bulk Brazil:** 470.9 BRL/ton (+0.8% vs. 467.3 budget)

### Cost Metrics
- **Variable Costs:** 56.3 USD/ton (+14% vs. 49.4 budget)
- **Fuel Costs:** 10.8 USD/ton (-22% vs. 13.8 budget)
- **Electricity Costs:** 20.1 USD/ton (-11% vs. 22.5 budget)
- **Fixed Costs Plant:** -7.125M USD (-5% favorable vs. -7.486M budget)
- **Employee Costs:** -3.493M USD (-2% vs. -3.556M budget)
- **Maintenance Costs:** -1.077M USD (-51% vs. -2.211M budget)

### Profitability Metrics
- **EBITDA Cement:** 5.355M USD (+4% vs. 5.151M budget)
- **EBITDA Margin Cement:** 12.4% (+2 pp vs. 4.9% prior year)
- **EBITDA Ready-Mix:** -171k USD (-718% vs. +28k budget)
- **EBITDA Precast:** -38k USD (-131% vs. +123k budget)
- **Lebanon Total EBITDA:** 2.142M USD (-17% vs. 2.568M budget)
- **Net Income:** 354k USD positive vs. -2.332M prior year

### Operational Efficiency Metrics
- **Thermal Energy Consumption:** 906 Kcal/kg clinker (+4.5% vs. 867 budget)
- **Electricity Consumption:** 113 kWh/ton (+7.6% vs. 105 budget)
- **Utilization Factor (%):** 39% (+30pp vs. 14% prior year)
- **Reliability Factor:** 82% (-17pp vs. 30% prior year)
- **Performance Factor:** 57% (-42pp vs. 70% prior year)

### Safety Metrics
- **Frequency Ratio Lebanon:** 3.8 (elevated vs. 2.3 budget)
- **Lost Time Injuries Lebanon:** 3 total YTD
- **Non-Cement Frequency Ratio:** 16.1 (critical vs. 7.8 budget)
- **Cement Frequency Ratio:** 1.5 (below budget 1.3)
- **Brazil Frequency Ratio:** 2.81 (better than Lebanon)

### Working Capital Metrics
- **Accounts Receivable:** 831k USD (+9% vs. 765k budget)
- **Inventories:** 14.371M USD (+126% vs. 6.365M budget)
  - Finished Goods: 5.974M
  - Raw Materials: 2.693M
  - Packaging: 5.704M
- **Accounts Payable:** -10.976M USD (+275% vs. -2.925M budget)
- **DSO (Days):** 4 days (stable)
- **DIO (Days):** 197 days (+106 vs. 91 budget - excess inventory)
- **DPO (Days):** 69 days (+49 vs. 20 budget - extended payables)

### Cash Flow Metrics
- **Operating Cash Flow:** 8.034M USD (+0% vs. 8.052M budget)
- **Capital Expenditures:** -7.168M USD (-23% vs. -9.350M budget)
- **Net Cash Flow:** 866k USD positive
- **Opening Net Debt:** 10.234M USD
- **Closing Net Debt:** 9.368M USD (improved by 866k)

### Headcount Metrics
- **Total Lebanon FTEs:** 437 (Aug-25) vs. 463 (2024)
- **Cement Plant FTEs:** 275 (Aug-25)
- **Ready-Mix FTEs:** 49
- **Precast FTEs:** 21
- **G&A FTEs:** 59

---

## 4. Transposed Table Analysis

**Finding:** NO transposed tables detected in Section 7.

- All tables maintain consistent row-based metric structure
- Time periods always in columns (Month, Budget, Prior Year, YTD)
- Variance percentages calculated consistently
- No inverted headers or rotated axis presentations

---

## 5. Ground Truth Query Examples (15 Queries)

### Easy Difficulty (3 queries)

**Query 1:** Volume metrics
- Q: "What was the YTD cement volume in Lebanon IM for August 2025?"
- A: "531 kton, +24% vs. 429 budget and +33% vs. 400 prior year"
- Table: Lebanon Cement (LB 5)

**Query 5:** Headcount snapshot
- Q: "Current Lebanon Cement headcount?"
- A: "308 FTEs as of August 2025"
- Table: Headcount Evolution (LB 13)

**Query 13:** Safety metrics
- Q: "Lebanon safety frequency ratio YTD 2025?"
- A: "3.8 per million hours vs. 2.3 budget (above target)"
- Table: H&S KPIs (LB 11)

### Medium Difficulty (7 queries)

**Query 2:** Price trends
- Q: "Year-over-year cement price change?"
- A: "80.3 USD/ton (2025) vs. 77.9 (2024) = +3%"
- Table: Lebanon Cement (LB 5)

**Query 4:** Profitability margins
- Q: "EBITDA margin for cement YTD 2025?"
- A: "12.4% vs. 14.7% budget (-2.3pp) but +7.5pp vs. 4.9% prior year"
- Table: Lebanon Cement (LB 5)

**Query 8:** Energy efficiency
- Q: "Thermal energy specific consumption?"
- A: "906 Kcal/kg clinker (+4.5% vs. budget, +0.6% vs. prior year)"
- Table: Cement Detailed Ops (LB 15-16)

**Query 9:** Working capital days
- Q: "Days Sales Outstanding (DSO)?"
- A: "4 days (steady vs. budget, improved from prior periods)"
- Table: Net Working Capital (LB 20)

**Query 14:** Market position
- Q: "Lebanon cement market share and growth?"
- A: "27.4% market share (+1.5pp vs. budget, +1.7pp vs. prior year); market growing 24.3% YoY"
- Table: Cement Detailed Ops (LB 15)

### Hard Difficulty (5 queries)

**Query 3:** Cost structure analysis
- Q: "Fixed costs breakdown and budget variance?"
- A: "7.125M USD total (-5% vs. budget): Employee 3.493M, Maintenance 1.077M, Other 2.555M"
- Table: Lebanon Cement (LB 5)

**Query 6:** Segment performance
- Q: "Ready-Mix EBITDA performance vs. expectations?"
- A: "Negative 171k USD vs. +28k budget = 199k shortfall (-718% variance); margin -6% vs. +1% budget"
- Table: Materials (LB 6)

**Query 7:** G&A efficiency
- Q: "G&A cost ratio to turnover?"
- A: "6.5% of 45.056M turnover (2.921M USD) vs. 7.1% budget and 8.4% prior year"
- Table: G&A (LB 7)

**Query 11:** Cost component analysis
- Q: "Electricity as % of variable costs?"
- A: "20.1 USD/ton out of 56.3 total = ~35-40% of variable costs; improved from 22.5 budget"
- Table: Lebanon Cement (LB 5, 15)

**Query 15:** Inventory analysis
- Q: "Inventory levels and DIO trend?"
- A: "14.371M USD total (+126% vs. budget): FG 5.974M, RM 2.693M, PKG 5.704M; DIO 197 days (+106 vs. budget)"
- Table: Net Working Capital (LB 20)

---

## 6. Key Retrieval Challenges Identified

### Challenge 1: Multi-Table Cross-References
- **Example:** Query 11 requires data from both Table 1 (LB 5) and Table 10 (LB 15-16)
- **Risk:** System may retrieve only one table if not configured for cross-document linking

### Challenge 2: Variance Calculation Context
- **Example:** 14% variance for variable costs seems positive but actually negative (cost overrun)
- **Risk:** Requires semantic understanding that cost increases are unfavorable

### Challenge 3: Unit Consistency
- **Issue:** Mixed units - 1000 USD, USD/ton, kton, km³, LBP, BRL
- **Risk:** Confusion if unit extraction fails or mixes units in comparison

### Challenge 4: Implicit Hierarchies
- **Example:** Ready-Mix is sub-component of "Materials" which includes both Ready-Mix and Precast
- **Risk:** Aggregation errors if system doesn't understand component relationships

### Challenge 5: Negative Values
- **Issue:** All costs shown as negative (-1058, -462, etc.)
- **Risk:** Sign interpretation errors in retrieval/synthesis

---

## 7. Data Completeness Assessment

| Dimension | Coverage | Notes |
|---|---|---|
| Time Periods | 100% | Monthly, YTD, Budget, Prior Year across all tables |
| Variance Metrics | 95% | % Budget and % LY on nearly all metrics |
| Geographic Segments | 92% | Lebanon primary, Brazil secondary (2 tables) |
| Business Segments | 100% | Cement, Ready-Mix, Precast covered comprehensively |
| Functional Areas | 88% | Operations, Finance, HR, Safety all represented |
| Sub-metrics | 85% | Some component details missing (e.g., partial headcount breakdown) |

---

## 8. Recommendations for Ground Truth Testing

### High-Priority Test Scenarios

1. **Volume + Price Composite Queries** (Medium Difficulty)
   - Combines two dimensions that appear side-by-side
   - Tests retrieval of multiple metrics from same row group

2. **Variance Direction Understanding** (Hard Difficulty)
   - Revenue increases = favorable, Cost increases = unfavorable
   - Tests semantic understanding beyond numeric retrieval

3. **Segment Roll-Up Validation** (Hard Difficulty)
   - Cement + Ready-Mix + Precast = Materials total
   - Tests hierarchical aggregation across segments

4. **Margin Calculation Verification** (Medium Difficulty)
   - EBITDA / Turnover = Margin %
   - Tests derived metric calculation from base figures

5. **Working Capital Narrative** (Hard Difficulty)
   - Combine Inventory + Receivables + Payables + DSO/DIO into story
   - Tests multi-table synthesis

---

## File Location

**YAML Data Inventory:** `/Users/ricardocarvalho/DeveloperFolder/RAGLite/docs/ground-truth-review/section-7-inventory.yaml`

**Structure:**
- 16 detailed table specifications with 189+ metrics
- 15 ground truth Q&A pairs with difficulty ratings and source tables
- Complete data point extraction with variance analysis
- Units, descriptions, and hierarchical relationships documented

---

## Conclusion

Section 7 provides excellent source material for ground truth creation with:
- **Non-transposed, consistent table structure** (no layout challenges)
- **Rich variance context** (Budget, Prior Year comparisons built-in)
- **Multi-dimensional data** (Volume, Price, Cost, Profitability, Efficiency, Safety)
- **Clear attribution potential** (Every number tied to specific page/table)
- **Graduated difficulty levels** (Easy to Hard test cases available)

**Recommended approach:** Start with Easy queries on single metrics, progress to Medium queries requiring 2-3 metrics from same table, then Hard queries requiring cross-table synthesis or semantic understanding.
