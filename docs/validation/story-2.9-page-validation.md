# Story 2.9: Ground Truth Page Reference Validation Worksheet

**Date:** 2025-10-25
**Validator:** Dev Agent (Amelia)
**Source PDF:** 2025-08 Performance Review CONSO_v2.pdf (160 pages)
**Ground Truth File:** tests/fixtures/ground_truth.py (50 queries)

## Validation Methodology

**Page Number Definition:**
- Use **PDF page number** (visible in PDF footer), NOT document internal page number
- For multi-page answers, record **primary page** (where majority of data appears)
- For table-based answers, record page with **complete table** or **table header**

**Validation Process:**
1. Read question text and keywords
2. Search PDF using Cmd+F with keywords from `expected_keywords`
3. Locate answer content and note PDF page number
4. Compare to current `expected_page_number` value
5. Record status: `correct`, `incorrect`, or `missing`
6. Add notes for ambiguous cases (multi-page, duplicate content)

---

## Validation Results

| Q# | Category | Question (Truncated) | Current Page | Actual Page | Status | Notes |
|----|----------|----------------------|--------------|-------------|--------|-------|
| 1 | cost_analysis | Variable cost per ton Portugal Cement | 46 | | | |
| 2 | cost_analysis | Thermal energy cost per ton | 46 | | | |
| 3 | cost_analysis | Electricity cost per ton | 46 | | | |
| 4 | cost_analysis | Raw materials costs per ton | 46 | | | |
| 5 | cost_analysis | Packaging costs per ton | 46 | | | |
| 6 | cost_analysis | Alternative fuel rate percentage | 46 | | | |
| 7 | cost_analysis | Maintenance costs per ton | 46 | | | |
| 8 | cost_analysis | Electricity specific consumption clinker | 46 | | | |
| 9 | cost_analysis | Thermal energy specific consumption | 46 | | | |
| 10 | cost_analysis | External electricity price per MWh | 46 | | | |
| 11 | cost_analysis | Total variable costs trend analysis | 46 | | | |
| 12 | cost_analysis | Alternative fuel vs thermal energy relationship | 46 | | | |
| 13 | margins | EBITDA IFRS margin percentage | 46 | | | |
| 14 | margins | EBITDA per ton | 46 | | | |
| 15 | margins | Unit variable margin per ton | 46 | | | |
| 16 | margins | Fixed costs per ton Outão plant | 47 | | | |
| 17 | margins | Fixed costs per ton Maceira plant | 47 | | | |
| 18 | margins | Unit cement EBITDA Outão internal market | 47 | | | |
| 19 | margins | Fixed costs Pataias plant comparison | 47 | | | |
| 20 | margins | EBITDA margin improvement analysis | 46 | | | |
| 21 | financial_performance | EBITDA Portugal Aug-25 YTD | 77 | | | |
| 22 | financial_performance | Cash flow from operating activities | 77 | | | |
| 23 | financial_performance | Capital expenditures (Capex) | 77 | | | |
| 24 | financial_performance | Financial net debt closing balance | 77 | | | |
| 25 | financial_performance | Change in trade working capital | 77 | | | |
| 26 | financial_performance | Income tax payments | 77 | | | |
| 27 | financial_performance | Net interest expenses | 77 | | | |
| 28 | financial_performance | Cash set free or tied up after investments | 77 | | | |
| 29 | financial_performance | EBITDA Portugal + Group Structure growth | 77 | | | |
| 30 | financial_performance | CF operations vs working capital relationship | 77 | | | |
| 31 | safety_metrics | FTE employees Portugal Cement | 46 | | | |
| 32 | safety_metrics | Daily clinker production capacity | 46 | | | |
| 33 | safety_metrics | Reliability factor percentage | 46 | | | |
| 34 | safety_metrics | Utilization factor in tons | 46 | | | |
| 35 | safety_metrics | Performance factor percentage | 46 | | | |
| 36 | safety_metrics | CO2 emissions per ton clinker comparison | 46 | | | |
| 37 | workforce | Employee costs per ton | 46 | | | |
| 38 | workforce | FTEs in distribution | 46 | | | |
| 39 | workforce | Tunisia operations total headcount | 108 | | | |
| 40 | workforce | FTEs in sales | 46 | | | |
| 41 | workforce | Tunisia Cement employees by function | 108 | | | |
| 42 | workforce | Employee cost per ton efficiency trends | 46 | | | |
| 43 | operating_expenses | Other costs per ton | 46 | | | |
| 44 | operating_expenses | Distribution costs per ton | 46 | | | |
| 45 | operating_expenses | Sales costs per ton | 46 | | | |
| 46 | operating_expenses | Insurance costs | 46 | | | |
| 47 | operating_expenses | Rents and rentals costs | 46 | | | |
| 48 | operating_expenses | Production services costs | 46 | | | |
| 49 | operating_expenses | Specialized labour costs | 46 | | | |
| 50 | operating_expenses | Fixed costs breakdown and efficiency | 46 | | | |

---

## Summary Statistics (To Be Filled After Validation)

| Metric | Count | Percentage |
|--------|-------|------------|
| Total queries validated | 0/50 | 0% |
| Correct page references | | |
| Incorrect page references | | |
| Missing page references | | |

---

## Notes

- Validation in progress...
- Keywords used for PDF search documented in ground_truth.py
- Ambiguous cases will be documented in Notes column
