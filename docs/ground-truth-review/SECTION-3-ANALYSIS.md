# Section 3 Data Inventory & Ground Truth Analysis
## Pages 41-60: Financial Operations Report

**Analysis Date:** October 26, 2025
**Report Period:** August 2025 Year-To-Date
**Report Type:** Operational & Financial Analysis
**Currency:** EUR (thousands)

---

## Executive Summary

### Scope
Section 3 of the financial report spans **20 pages (41-60)** and contains **8 major data tables** with comprehensive operational metrics for:
- Personnel and Headcount tracking
- Capital Expenditure analysis
- Cement operations (3 plants: Outão, Maceira, Pataias)
- Ready-Mix concrete operations (5 regions)
- Margin analysis by business unit

### Data Structure
- **Total Tables:** 8
- **Sample Data Points:** 39
- **Ground Truth Queries:** 15
- **Business Entities:** 7 major units + 17 sub-entities
- **Geographic Coverage:** 5 countries, 5 regional markets
- **Key Metrics:** 50+ operational KPIs

---

## Tables Inventory

### Table 1: Personnel Expenses (Page 41)
**ID:** T3-001
**Type:** Financial Statement (Monthly vs Budget vs Prior Year)
**Dimensions:** 17 entities × 6 period columns

**Business Entities:**
- Portugal (consolidated)
- Cement Division (Outão, Maceira, Pataias, Distribution, Sales)
- International (Madeira, Cape Verde, Netherlands, Spain)
- Other divisions (Unibetão, Betotrans, Ready Mix, Aggregates, Mortars, Precast)

**Metrics:**
- Monthly expense amount
- Budget variance %
- Prior year variance %
- YTD accumulated expense
- YTD budget variance
- YTD prior year variance

**Sample Values:**
| Entity | Period | Value | Unit |
|--------|--------|-------|------|
| Portugal | Aug-25 YTD | 38,599 | 1000 EUR |
| Portugal Cement | Aug-25 YTD | 10,317 | 1000 EUR |
| Portugal Cement - Outão | Aug-25 YTD | 4,295 | 1000 EUR |
| Total Cement and Terminals | Aug-25 YTD | 12,393 | 1000 EUR |

**Data Quality Notes:**
- Standard rectangular format (entities as rows, periods as columns)
- Consistent negative values (expenses shown as negative)
- Variance calculations available for budget and prior year comparisons

---

### Table 2: Headcount Evolution (Page 42)
**ID:** T3-002
**Type:** Transposed Timeline Table ⚠️
**Dimensions:** 17 entities × 17 time periods (2020-2025)

**Key Characteristic:**
**⚠️ TRANSPOSED TABLE** - This table has **months/years as COLUMNS** and **entities as ROWS**. A standard row-oriented parser expecting entity headers in the first row will struggle with this structure.

**Time Coverage:**
- Historical: 2020 FY, 2021 FY, 2022 FY, 2023 FY, 2024 FY
- Current Year Monthly: Jan-25 through Aug-25 (Actual)
- Future Periods: Sep-25, Oct-25, Nov-25, Dec-25 Budget (not yet recorded)

**Metrics:**
- FTE Count (Full-Time Equivalents)

**Sample Values:**
| Entity | Period | Value | Unit |
|--------|--------|-------|------|
| Portugal | Aug-25 Actual | 1,164 | FTEs |
| Portugal | Dec-25 Budget | 1,281 | FTEs |
| Portugal Cement | Aug-25 Actual | 266 | FTEs |
| Total Cement and Terminals | Aug-25 Actual | 355 | FTEs |
| Portugal Ready Mix | Aug-25 Actual | 387 | FTEs |

**Data Quality Notes:**
- Historical trend data available back to 2020
- Year-over-year headcount growth visible
- Budget plan extends to December 2025
- Some entity rows have incomplete historical data (e.g., Portugal Precast)

---

### Table 3: Capex Total / per Type (Page 43)
**ID:** T3-003
**Type:** Multi-Level Capital Expenditure Analysis
**Dimensions:** 16 entities × 6 period columns + 8 capex type breakdowns

**Primary Metrics:**
- Capex amount by entity (monthly and YTD)
- Budget variance %
- Prior year variance %

**Capex Categories:**
1. Recurring investments
2. Development projects
3. Land acquisitions
4. Equipment replacement
5. Health & Safety investments
6. Other expansion
7. Energy infrastructure
8. Other improvements

**Sample Values:**
| Entity | Metric | Period | Value | Unit |
|--------|--------|--------|-------|------|
| Portugal | Capex YTD | Aug-25 | 33,059 | 1000 EUR |
| Portugal | Budget Variance | Aug-25 YTD | -37% | % |
| Portugal Cement | Capex YTD | Aug-25 | 19,766 | 1000 EUR |
| Portugal Ready Mix | Capex YTD | Aug-25 | 5,244 | 1000 EUR |
| Portugal Bags | Capex YTD | Aug-25 | 886 | 1000 EUR |

**Data Quality Notes:**
- Bottom section contains capex type breakdown with sub-headers
- Mixed currency and percentage columns
- Multi-level hierarchy requires careful parsing

---

### Table 4: Portugal Cement - Internal Market Metrics (Page 44)
**ID:** T3-004
**Type:** Operational Performance Metrics
**Dimensions:** 14 metrics × 4 period columns

**Business Context:** Portugal's cement segment
- Total market size tracking
- Company market share position
- Sales volume and pricing
- Product mix analysis

**Metrics:**
1. Cement Market - kton
2. Population - Mpeople
3. Cement per Capita
4. Market Share - %
5. Sales Cement IM - EUR 1000
6. Sales Volume - kton
7. % Grey Cement Bulk
8. % Grey Cement Bagged
9. % White Cement
10. Price per ton (EUR/ton)
11. Grey Cement Bulk Price
12. Grey Cement Bagged Price
13. White Cement Price
14. Net Transport Costs

**Sample Values:**
| Metric | Period | Value | Unit |
|--------|--------|-------|------|
| Cement Market | Aug-25 YTD | 3,078 | kton |
| Market Share | Aug-25 YTD | 36.0 | % |
| Sales Volume | Aug-25 YTD | 1,107 | kton |
| Price Cement | Aug-25 YTD | 132.5 | EUR/ton |
| Net Transport Costs | Aug-25 YTD | -7,585 | 1000 EUR |

**Data Quality Notes:**
- Mix of absolute values and percentages requires unit awareness
- Market share calculation implies competitive market analysis
- Transport costs shown as negative (cost reduction from revenue)

---

### Table 5: Portugal Cement - Operational Costs (Pages 46-50)
**ID:** T3-005
**Type:** Detailed Cost Analysis
**Dimensions:** 6 cost categories × 18+ individual cost metrics × 4 period columns

**Cost Categories:**
1. **Variable Costs** (total and per ton)
   - Amount: 30,447 (1000 EUR) YTD
   - Per unit: 23.2 EUR/ton

2. **Termic Energy** (with fuel breakdown)
   - Petcoke: 49% (by month)
   - Fuel Oil: 1%
   - Alternative Fuel: 50%
   - Specific consumption: 835 Kcal/kg clinker

3. **Electricity**
   - Amount: 10,265 (1000 EUR) YTD
   - Per unit: 7.8 EUR/ton
   - Specific consumption: 119 Kwh/ton
   - Budget variance: +56% (significant overrun)

4. **Raw Materials**
   - Amount: 2,363 (1000 EUR) YTD
   - Per unit breakdown available

5. **Fixed Costs**
   - Labor, depreciation, facility costs

6. **Other Operating Costs**
   - Maintenance, supplies, logistics

**Plant Breakdown (Pages 47-50):**
Individual detailed sheets for each cement plant:
- **Outão:** 798 kton capacity
- **Maceira:** 495 kton capacity
- **Pataias:** 44 kton capacity (small specialty plant)

**Unit Economics by Plant (Outão Plant Example):**
| Metric | Value | Unit |
|--------|-------|------|
| Production Volume | 798 | kton |
| Price Cement MI | 125.6 | EUR/ton |
| Variable Cost | -21.4 | EUR/ton |
| Fixed Cost | -23.7 | EUR/ton |
| Unit EBITDA MI | 80.5 | EUR/ton |

**Data Quality Notes:**
- Rich operational detail enables process cost analysis
- Energy mix percentages indicate fuel strategy
- Specific consumption metrics enable benchmarking
- Multi-page breakdown allows plant-level deep dives
- Budget variances highlight cost control issues (electricity +56%)

---

### Table 6: Ready-Mix Consolidated Operational Performance (Page 51)
**ID:** T3-006
**Type:** Operational & Financial Performance
**Dimensions:** Sales, Income, Variable Costs, Fixed Costs × 4 period columns

**Business Segment:** SECIL BETÃO (Concrete Division)

**Sales Section:**
- Sales Amount: 89,951 (1000 EUR) YTD
- Sales Volume: 1,055 km3 YTD
- Sales Price: 85.2 EUR/m3 YTD
- Prior Year Variance: +7%
- Budget Variance: +1%

**Variable Cost Breakdown:**
- Cement: 41,231 (1000 EUR) - 59% of variable costs
  - Cement per m3: 39.1 kg/m3
  - Consumption: 272.8 kg/m3
  - Average price: 143.2 EUR/ton

- Aggregates: 11,838 (1000 EUR) - 17% of variable costs
  - Price: 11.2 EUR/m3

- Sand: 11,385 (1000 EUR) - 16% of variable costs
  - Price: 10.8 EUR/m3

- Ashes: 1,311 (1000 EUR) - 2% of variable costs
  - Price: 1.2 EUR/m3

- Other Raw Materials: 3,751 (1000 EUR)

**Fixed Costs:**
- Employee costs
- Facility/equipment costs
- Maintenance and depreciation

**Sample Values:**
| Metric | Period | Value | Unit |
|--------|--------|-------|------|
| Sales Ready Mix | Aug-25 YTD | 89,951 | 1000 EUR |
| Volume | Aug-25 YTD | 1,055 | km3 |
| Price | Aug-25 YTD | 85.2 | EUR/m3 |
| Cement Consumption | Aug-25 YTD | 272.8 | kg/m3 |
| Variable Costs | Aug-25 YTD | 69,516 | 1000 EUR |
| EBITDA | Aug-25 YTD | 20,435 | 1000 EUR |

---

### Table 7: Ready-Mix Margin by Region (Page 52)
**ID:** T3-007
**Type:** Regional Margin Analysis
**Dimensions:** 5 regions × 6 margin metrics

**Regions & Unit Economics:**

| Region | Sales Vol | Price | Var Cost | Fixed Cost | EBITDA | Avg $ Margin |
|--------|-----------|-------|----------|------------|--------|--------------|
| **North** | 415 km3 | 82.0 | -74.9 | -6.3 | 2.6 | EUR/m3 |
| **Center** | 194 km3 | 79.1 | -62.0 | -7.6 | 10.2 | EUR/m3 |
| **Lisbon** | 259 km3 | 85.2 | -68.3 | -9.7 | 9.2 | EUR/m3 |
| **Alentejo** | 96 km3 | 102.6 | -77.1 | -8.9 | 18.4 | EUR/m3 |
| **Algarve** | 91 km3 | 94.7 | -73.5 | -9.2 | 13.3 | EUR/m3 |

**Key Insights:**
- **Alentejo** has highest margin (18.4 EUR/m3) despite lower volume (96 km3)
- **Lisbon** has strong volume (259 km3) but lower margin (9.2 EUR/m3)
- **North** has lowest margin (2.6 EUR/m3) - potential optimization opportunity
- **Center** region shows good balance (10.2 EUR/m3 margin, 194 km3 volume)
- Price variation: 102.6 (Alentejo) vs 79.1 (Center) suggests market segmentation

**Regional Performance Details (Pages 53-57):**
Each region has detailed operational breakdown including:
- Cement consumption per region
- Logistics costs
- Pump service offerings
- Regional profitability analysis

**Data Quality Notes:**
- Clear regional profitability comparison
- Mix of high-price/high-margin (Alentejo) and high-volume/mid-margin (Lisbon)
- Enables product optimization by region

---

### Table 8: Margin by Plant - Cement (Page 47)
**ID:** T3-008
**Type:** Plant-Level Margin Analysis
**Dimensions:** 3 cement plants × 9 margin metrics

**Plant Comparison (August 2025):**

| Plant | Volume | Price MI | Price ME | Var Cost | Fixed Cost | EBITDA MI |
|-------|--------|----------|----------|----------|-----------|-----------|
| **Outão** | 798 kton | 125.6 | 60.2 | -21.4 | -23.7 | 80.5 |
| **Maceira** | 495 kton | 125.6 | 60.2 | -23.8 | -26.8 | 75.0 |
| **Pataias** | 44 kton | 125.6 | 60.2 | -60.6 | -59.8 | 65.4 |

**Key Metrics (All EUR/ton):**
- **Price Cement Internal Market (MI):** 125.6 (same for all plants)
- **Price Cement Export (ME):** 60.2 (same for all plants)
- **Variable Costs:** -21.4 to -60.6 (Pataias significantly higher due to small scale)
- **Fixed Costs:** -23.7 to -59.8 (Pataias high fixed cost burden)
- **Unit EBITDA MI:** 80.5 → 75.0 → 65.4 (Pataias significantly lower)

**Data Quality Notes:**
- Consistent pricing across plants (centralized pricing)
- Scale economies evident (Pataias much smaller and less efficient)
- Outão is most efficient plant
- Maceira mid-tier performance
- Pataias appears to be specialty/small production plant

---

## Ground Truth Queries (15 Test Cases)

### GTQ-3-001: Portugal Total Personnel Expenses
**Question:** What was the Portugal total personnel expense for August 2025 YTD?
**Expected Answer:** 38,599 thousand EUR
**Source:** Page 41 - Personnel Expenses table
**Difficulty:** Easy (direct lookup)

### GTQ-3-002: Headcount Comparison
**Question:** How many FTEs did Portugal Cement have in August 2025 actual vs budget?
**Expected Answer:** 266 actual (Aug-25) vs 321 budgeted (Dec-25 Full Year)
**Source:** Page 42 - Headcount Evolution table
**Difficulty:** Medium (transposed table, cross-period comparison)

### GTQ-3-003: Capex and Budget Variance
**Question:** What was the total Capex for Portugal in August 2025 YTD and what was the variance vs budget?
**Expected Answer:** 33,059 thousand EUR with -37% variance vs budget
**Source:** Page 43 - Capex Total table
**Difficulty:** Medium (multi-column interpretation)

### GTQ-3-004: Cement Market Size
**Question:** What was the cement market size in Portugal in August 2025 YTD?
**Expected Answer:** 3,078 kton
**Source:** Page 44 - Portugal Cement Operational Performance
**Difficulty:** Easy (direct lookup)

### GTQ-3-005: Market Share
**Question:** What was Portugal's market share in cement in August 2025 YTD?
**Expected Answer:** 36.0%
**Source:** Page 44 - Portugal Cement Internal Market metrics
**Difficulty:** Easy (direct lookup)

### GTQ-3-006: Unit Cost Analysis
**Question:** What was the variable cost per ton for Portugal Cement in August 2025 YTD?
**Expected Answer:** 23.2 EUR/ton
**Source:** Page 46 - Portugal Cement Operational Costs
**Difficulty:** Medium (requires understanding cost structure)

### GTQ-3-007: Regional Price Comparison
**Question:** What was the Ready-Mix sales price in the Lisbon region for August 2025?
**Expected Answer:** 85.2 EUR/m3
**Source:** Page 55 - Portugal Ready-Mix Lisbon regional breakdown
**Difficulty:** Medium (requires multi-page navigation)

### GTQ-3-008: Volume by Region
**Question:** How many km3 of Ready-Mix were sold in the North region for August 2025 YTD?
**Expected Answer:** 415 km3
**Source:** Page 53 - Portugal Ready-Mix North regional breakdown
**Difficulty:** Medium (requires specific region extraction)

### GTQ-3-009: Margin Calculation
**Question:** What was the unit EBITDA for Ready-Mix in the Center region for August 2025?
**Expected Answer:** 10.2 EUR/m3
**Source:** Page 52 - Ready-Mix Margin by Region
**Difficulty:** Hard (calculated margin metric)

### GTQ-3-010: Cost Structure Analysis
**Question:** What was the variable cost per m3 for Ready-Mix in the Alentejo region?
**Expected Answer:** -77.1 EUR/m3
**Source:** Page 52 - Ready-Mix Margin by Region
**Difficulty:** Medium (negative value interpretation)

### GTQ-3-011: Absolute vs Relative Metrics
**Question:** What was the electricity cost in absolute terms for Portugal Cement in August 2025 YTD?
**Expected Answer:** 10,265 thousand EUR with 56% variance vs budget
**Source:** Page 46 - Portugal Cement Electricity costs
**Difficulty:** Hard (significant budget overrun, requires investigation)

### GTQ-3-012: Consumption Metrics
**Question:** What was the Ready-Mix cement consumption in kg/m3 for the total consolidated in August 2025 YTD?
**Expected Answer:** 272.8 kg/m3
**Source:** Page 51 - Ready-Mix Consolidated Operations
**Difficulty:** Easy (technical specification lookup)

### GTQ-3-013: Plant-Level Volume
**Question:** How many kton did Outão plant produce in cement in August 2025?
**Expected Answer:** 798 kton
**Source:** Page 47 - Portugal Cement Margin by Plant
**Difficulty:** Medium (plant-specific metric)

### GTQ-3-014: Profitability Metric
**Question:** What was the unit EBITDA margin for the Outão cement plant in August 2025?
**Expected Answer:** 80.5 EUR/ton
**Source:** Page 47 - Margin by Plant
**Difficulty:** Hard (complex calculation, plant-specific)

### GTQ-3-015: Aggregation Query
**Question:** What was the total Ready-Mix sales volume for August 2025 YTD across all regions?
**Expected Answer:** 1,055 km3
**Source:** Page 51 - Ready-Mix Consolidated Sales
**Difficulty:** Medium (requires aggregation across regions)

---

## Data Quality Analysis

### Transposed Tables ⚠️
**Issue:** Table T3-002 (Headcount Evolution) has an unusual structure where:
- **Columns:** Time periods (2020 FY, 2021 FY, ..., Aug-25, Dec-25 Budget)
- **Rows:** Business entities (Portugal, Portugal Cement, etc.)

**Impact on Parsing:**
- Standard column-based parsers may fail
- Header detection must handle year/month naming conventions
- Row extraction is correct but cell interpretation needs timeline awareness

**Recommendation:** Implement special handling for timeline-oriented tables with date/period-based column headers.

### Multi-Level Headers
**Tables:** T3-003 (Capex), T3-005 (Operational Costs)

**Issue:** Some tables have grouped headers or sub-headers that span multiple columns or rows.

**Example - Capex Breakdown:**
```
Main: Portugal
  Sub: Month Aug-25 B Aug-25 Aug-24 % B % LY
  Sub: YTD (below Month)
```

### Percentage Metrics
**Tables:** All (Personnel, Headcount, Capex, Operational)

**Metrics:**
- Budget Variance % (common across all operational tables)
- Prior Year Variance % (year-over-year comparison)
- Market Share % (competitive positioning)
- Product Mix % (cement types, energy sources)

**Format Variability:**
- Some shown as decimals: 36.0%
- Some shown with basis points: -0.5 pp (percentage points)
- Some as absolute percentages: 80.5

**Recommendation:** Standardize percentage interpretation - always capture both numeric value and unit (%, pp, decimal).

### Unit Conversions
**Volume Units:**
- Ready-Mix: km³ and m³ (1 km³ = 1,000,000 m³)
- Cement: kton and ton (1 kton = 1,000 ton)
- Market: Mpeople (millions of people)

**Currency:**
- All amounts in EUR (thousands) unless specified
- Unit prices in EUR/ton, EUR/m³

**Energy:**
- Kcal/kg clinker (thermal intensity)
- Kwh/ton (electricity intensity)

**Recommendation:** Maintain unit aware extraction - never lose unit information during chunking/retrieval.

---

## Implementation Recommendations

### For RAGLite Ground Truth Testing

1. **Test Query Difficulty Progression:**
   - Start with Easy queries (GTQ-3-001, 3-004, 3-005, 3-012)
   - Progress to Medium queries (GTQ-3-002, 3-003, 3-006, 3-007, 3-008, 3-010, 3-013, 3-015)
   - Validate with Hard queries (GTQ-3-009, 3-011, 3-014)

2. **Table-Specific Testing:**
   - **T3-001 (Personnel):** Straightforward, good baseline
   - **T3-002 (Headcount):** Test transposed table handling
   - **T3-003 (Capex):** Test multi-level header interpretation
   - **T3-004-T3-006:** Test metric naming and unit awareness
   - **T3-007 (Regional):** Test region-specific aggregations
   - **T3-008 (Plant):** Test plant-level filtering

3. **Semantic Challenge Testing:**
   - Budget variance queries (GTQ-3-003, 3-011) test interpretation of negative values
   - Regional comparisons (GTQ-3-007, 3-009, 3-010) test cross-page entity matching
   - Margin calculations (GTQ-3-009, 3-014) test derived metric understanding

4. **Data Quality Validation:**
   - Verify sum checks: Region volumes sum to consolidated (GTQ-3-015)
   - Validate percentage calculations: Budget variance consistency
   - Check unit conversions: km³ vs m³, kton vs ton

---

## File Locations

- **Inventory YAML:** `/Users/ricardocarvalho/DeveloperFolder/RAGLite/docs/ground-truth-review/section-3-inventory.yaml`
- **Analysis Document:** This file
- **Source PDF:** `/Users/ricardocarvalho/DeveloperFolder/RAGLite/docs/sample pdf/sections/section-03_pages-41-60.pdf`

---

## Summary Statistics

| Metric | Count |
|--------|-------|
| Pages Analyzed | 20 |
| Major Tables | 8 |
| Business Entities | 17+ |
| Sample Data Points | 39 |
| Ground Truth Queries | 15 |
| Key Metrics | 50+ |
| Geographic Markets | 5 |
| Regional Segments | 5 |
| Cement Plants | 3 |
| Time Periods | 17 (historical + forecast) |

---

**Document Version:** 1.0
**Last Updated:** October 26, 2025
**Prepared for:** RAGLite Ground Truth Validation
**Status:** Complete and ready for testing
