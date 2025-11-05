# Section 7 (Pages 121-140) - Quick Reference Guide

## File Organization

- **Primary YAML:** `section-7-inventory.yaml` (1,685 lines)
  - Complete structured data for all 16 tables
  - 189+ metrics with variance analysis
  - 15 ground truth Q&A pairs

- **Analysis Summary:** `SECTION-7-ANALYSIS-SUMMARY.md` (288 lines)
  - Executive overview
  - Key findings and challenges
  - Retrieval difficulty assessment

---

## 16 Tables at a Glance

### Financial Core (5 tables)

1. **Lebanon Cement Operations (LB 5)**
   - 45 metrics, 531k volume, 5.355M EBITDA
   - Comprehensive: Price, Costs, Margin, Production
   - Primary for volume/pricing/cost queries

2. **Lebanon P&L Statement (LB 9)**
   - EBITDA: 2.142M, Net Income: 354k
   - Profitability chain: EBITDA → EBIT → PBT → NI
   - Test margin calculation, tax impact

3. **Turnover/EBITDA Summary (LB 12)**
   - Total revenue: 45.056M, segment breakdown
   - Cement: 43.114M, Materials: 3.204M
   - Test segment aggregation, margin ratios

4. **Cash Flow Statement (LB 21)**
   - Operating CF: 8.034M, Capex: -7.168M
   - Working capital changes: +9.374M
   - Test cash dynamics, debt metrics

5. **Net Working Capital (LB 20)**
   - Inventory: 14.371M (126% over budget!)
   - DSO: 4, DIO: 197, DPO: 69
   - Critical for inventory/receivables queries

### Operational Detail (5 tables)

6. **Lebanon Cement Detailed Ops (LB 15-16)**
   - Market share: 27.4%, Energy: 906 Kcal/kg
   - Production efficiency: 39% utilization
   - Deep dive: raw materials, energy mix, emissions

7. **Lebanon Ready-Mix (LB 17)**
   - Volume: 42 km³, Margin: -6% (negative!)
   - Unit cost 55.7 USD/m³, margin 7.4 USD/m³
   - Challenge: High volatility in this segment

8. **Lebanon Precast (LB 18)**
   - Volume: 13 ku (down 44% vs budget)
   - EBITDA: -38k (negative margin -8%)
   - Worst performer - critical query topic

9. **Lebanon Materials Overview (LB 6)**
   - Combines Ready-Mix + Precast
   - Ready-Mix: -6% margin, Precast: -8% margin
   - Test segment hierarchy understanding

10. **Cement Detailed Production (LB 15)**
    - Clinker: 357 kton, Utilization: 39%
    - Reliability: 82%, Performance: 57% (declining)
    - Energy consumption detail (thermal, electricity)

### Overhead & Support (4 tables)

11. **Lebanon G&A & Corporate (LB 7)**
    - G&A: 2.921M (6.5% of turnover)
    - Employee costs: -1.649M
    - Corporate costs breakdown detailed

12. **Lebanon Headcount Evolution (LB 13)**
    - Total: 437 FTEs (down from 463)
    - Cement: 308, Ready-Mix: 49, Precast: 21
    - Historical trend 2020-2025

13. **Health & Safety KPIs (LB 11)**
    - Frequency ratio: 3.8 (above 2.3 budget)
    - Lost time injuries: 3 total
    - Non-cement very high: 16.1 (critical alert)

14. **Capex Analysis (LB 14)**
    - Total: 7.168M (-23% vs budget)
    - Replacement-focused: 4.597M
    - Development: 4.456M by segment

### Geographic & Forward-Looking (2 tables)

15. **Lebanon Rolling Forecast (LB 8)**
    - Sep-25 projections
    - Cement EBITDA: 950k (vs 836k Aug actual)
    - Test forward-looking vs actuals

16. **Brazil Cement Operations (BR 3)**
    - Volume: 1.160M kton, Price: 420.1 BRL/ton
    - Secondary geography - smaller scope
    - Good for geographic comparison queries

---

## Critical Data Points (17 Sample Values)

### Volume Leaders
- Cement: 531 kton YTD (+24% vs budget)
- Ready-Mix: 42 km³ (at budget)
- Clinker: 357 kton (+4% vs budget)

### Pricing Stable
- Cement: 80.3 USD/ton (consistent with budget)
- Ready-Mix: 63.1 USD/m³ (down 13%)
- Brazil Cement: 420.1 BRL/ton (stable)

### Cost Pressures
- Variable costs: 56.3 USD/ton (+14% vs budget)
- Electricity: 20.1 USD/ton (-11% improvement)
- Fuel: 10.8 USD/ton (-22% improvement)

### Profitability Mixed
- Cement EBITDA: 5.355M (+4%)
- Ready-Mix EBITDA: -171k (-718% vs budget!)
- Precast EBITDA: -38k (-131% vs budget!)
- Total EBITDA: 2.142M (-17% vs budget)

### Efficiency Concerning
- Thermal energy: 906 Kcal/kg (+4.5% vs budget, bad)
- Utilization: 39% (+30pp improvement vs prior year)
- Reliability: 82% (-17pp vs prior year, declining)
- Performance: 57% (-42pp vs prior year, concerning)

### Safety Red Flags
- Lebanon frequency ratio: 3.8 (above 2.3 budget)
- Non-cement frequency: 16.1 (critical! 2.5x budget)
- Cement frequency: 1.5 (below 1.3 budget, good)

### Working Capital Bloated
- Inventory: 14.371M (+126% vs budget)
- DIO: 197 days (+106 vs budget, 2x normal)
- Payables extended: 69 days (+49 vs budget)

---

## Ground Truth Query Distribution

| Difficulty | Count | Examples |
|---|---|---|
| EASY | 3 | Volume (531 kton), Headcount (437), Safety ratio (3.8) |
| MEDIUM | 7 | Price trends, Margin %, Energy efficiency, DSO metric, Market share |
| HARD | 5 | Cost structure, Segment performance, G&A ratios, Cost components, Inventory |

---

## Retrieval Challenge Hotspots

### 1. Ready-Mix Segment Volatility (Medium)
- Unit margin ranges: -0.9 to 15.9 USD/m³
- Price compression: 74.2 → 63.1 USD/m³ (-15%)
- EBITDA swings from +27k to -108k monthly

### 2. Precast Collapse (Hard)
- Volume down 44% (13 vs 24 budget)
- Negative margins across all metrics
- Can system understand semantic "bad performance"?

### 3. Inventory Mystery (Hard)
- 14.371M is 226% over budget
- Breakdown: FG 42%, RM 19%, PKG 40%
- DIO 197 days - why? Slow demand? Production mismatch?

### 4. Negative Values (Medium)
- All costs shown as negatives (-1058, -462, etc.)
- Sign interpretation critical for cost/benefit analysis
- Easy to flip wrong sign in synthesis

### 5. Percentage Point vs. Percentage (Medium)
- EBITDA margin variance: -2 pp (not -2%)
- Frequency ratio variance: +1.5pp vs 3% (different scales)
- Requires unit precision

---

## Testing Recommendations by Difficulty

### START HERE: Easy (Test Basic Retrieval)

Q: "What was the August 2025 YTD cement volume in Lebanon?"
A: "531 kton" (single number from Table 1, row 1)

Q: "How many FTEs did Lebanon have in August 2025?"
A: "437" (single number from Table 8)

Q: "What is the Lebanon safety frequency ratio YTD?"
A: "3.8 per million hours" (single number from Table 6)

### INTERMEDIATE: Medium (Test Synthesis & Context)

Q: "Why did cement prices remain flat vs budget?"
A: "Prices stable at 80.3 USD/ton despite cost increases" (requires Table 1 data + context)

Q: "How efficient is Lebanon's thermal energy use?"
A: "906 Kcal/kg clinker, +4.5% vs budget (worsening)" (Table 10 + interpretation)

Q: "Is DSO improving?"
A: "4 days stable vs budget, up from -4 in Dec-24" (Table 13 + time series)

### ADVANCED: Hard (Test Multi-Table & Semantic)

Q: "Why are Building Materials (Ready-Mix + Precast) unprofitable?"
A: "Ready-Mix -171k + Precast -38k = -209k total. Volume shortfalls (down 44% precast) cannot absorb fixed costs. Pricing pressure (Ready-Mix down 15%) adds to margin compression." (Tables 2, 7, 11, 12 + causal reasoning)

Q: "What is driving the inventory explosion?"
A: "Inventory 14.371M (+126% vs budget). DIO 197 days suggests 2x normal stock levels. Possible causes: production ahead of demand (Cement output +24%) or demand weakness (volumes generally up but not enough to consume stock)." (Table 13 + cross-validation with Table 1)

Q: "Is Lebanon getting safer?"
A: "No. Frequency ratio 3.8 > budget 2.3. Non-cement critically high at 16.1 vs 7.8 budget. Only cement segment (1.5) is below budget (1.3). Immediate intervention needed in non-cement operations." (Table 6 + segmentation)

---

## File Paths for Reference

**Full YAML Inventory:**
`/Users/ricardocarvalho/DeveloperFolder/RAGLite/docs/ground-truth-review/section-7-inventory.yaml`

**Analysis Summary:**
`/Users/ricardocarvalho/DeveloperFolder/RAGLite/docs/ground-truth-review/SECTION-7-ANALYSIS-SUMMARY.md`

**This Quick Reference:**
`/Users/ricardocarvalho/DeveloperFolder/RAGLite/docs/ground-truth-review/SECTION-7-QUICK-REFERENCE.md`

---

## Key Insights for RAG Testing

1. **Consistent Table Structure** - All tables follow same pattern, good for systematic testing
2. **Rich Variance Context** - Budget, Prior Year, Month/YTD comparisons provide multiple validation angles
3. **Mixed Difficulty** - Easy single-metric to hard multi-table/semantic queries available
4. **Real Business Issues** - Negative margins, inventory bloat, safety concerns add realistic complexity
5. **Clear Attribution** - Every number has specific table/page reference for accuracy validation
