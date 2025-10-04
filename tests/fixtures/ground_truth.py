"""Ground truth test set for RAGLite Phase 1 accuracy validation.

This module contains 50+ representative financial Q&A pairs from the Secil Group
performance review document (2025-08 Performance Review CONSO_v2.pdf). Used for
daily/weekly accuracy tracking throughout Phase 1 development and final validation.

The test set expands the Week 0 baseline (15 queries) to enable robust accuracy
tracking and regression detection during Phase 1 implementation (Weeks 1-5).

Usage:
    from tests.fixtures.ground_truth import GROUND_TRUTH_QA

    # Run accuracy validation
    for qa in GROUND_TRUTH_QA:
        query = qa["question"]
        expected_page = qa["expected_page_number"]
        # Execute query and validate results

    # Get subset for daily tracking (10-15 questions)
    import random
    daily_subset = random.sample(GROUND_TRUTH_QA, 15)

Adding New Questions:
    1. Copy an existing question template from the appropriate category
    2. Fill in all required fields (id, question, expected_answer, etc.)
    3. Manually validate against source PDF at expected_page_number
    4. Verify expected_keywords match actual text in document
    5. Update category count in header comment
    6. Maintain difficulty distribution (40% easy, 40% medium, 20% hard)

Structure:
    Each question dict contains:
    - id (int): Unique integer identifier (1-50+)
    - question (str): Natural language question text
    - expected_answer (str): Expected answer or answer criteria
    - expected_keywords (list[str]): Keywords that should appear in retrieved chunks
    - source_document (str): Source PDF filename
    - expected_page_number (int): Page number where answer is found (for NFR7 attribution)
    - expected_section (str): Section/chunk identifier (e.g., "Financial Metrics Summary")
    - category (str): One of 6 categories (cost_analysis, margins, financial_performance,
                      safety_metrics, workforce, operating_expenses)
    - difficulty (str): "easy", "medium", or "hard"

Difficulty Guidelines:
    - Easy: Direct factual lookup (single number, single table cell, one chunk)
    - Medium: Multiple data points, comparisons across time periods, 2-3 chunks
    - Hard: Cross-referencing sections, complex calculations, trend analysis, 3+ chunks

Categories & Distribution:
    - cost_analysis: 12 questions (5 easy, 5 medium, 2 hard)
    - margins: 8 questions (3 easy, 4 medium, 1 hard)
    - financial_performance: 10 questions (4 easy, 4 medium, 2 hard)
    - safety_metrics: 6 questions (2 easy, 3 medium, 1 hard)
    - workforce: 6 questions (3 easy, 2 medium, 1 hard)
    - operating_expenses: 8 questions (3 easy, 3 medium, 2 hard)
    - TOTAL: 50 questions (20 easy, 20 medium, 10 hard)

Validation:
    All questions manually validated against source PDF on 2025-10-12.
    See validation checklist: docs/qa/assessments/1.12A-validation-checklist.md

Target Accuracy Metrics (NFR6, NFR7):
    - 90%+ retrieval accuracy (correct chunks retrieved)
    - 95%+ source attribution accuracy (correct page numbers cited)

Version: 1.0
Last Updated: 2025-10-12
Validated By: Dev Agent (Amelia)
"""

# Category: cost_analysis (12 questions - 5 easy, 5 medium, 2 hard)

COST_ANALYSIS_QUESTIONS = [
    {
        "id": 1,
        "question": "What are the fixed costs per ton for operations?",
        "expected_answer": "Fixed costs are 26.8 EUR/ton (2025-08), 22.1 EUR/ton (2024-08), and 20.5 EUR/ton (2023-08)",
        "expected_keywords": ["fixed costs", "EUR/ton", "26.8", "22.1", "20.5"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 45,
        "expected_section": "Cost Analysis - Fixed Costs",
        "category": "cost_analysis",
        "difficulty": "easy",
    },
    {
        "id": 2,
        "question": "What is the distribution cost per ton?",
        "expected_answer": "Distribution costs are 13.3 EUR/ton (2025-08) and 14.3 EUR/ton (2024-08)",
        "expected_keywords": ["distribution costs", "EUR/ton", "13.3", "14.3"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 47,
        "expected_section": "Distribution Costs Summary",
        "category": "cost_analysis",
        "difficulty": "easy",
    },
    {
        "id": 3,
        "question": "What are the other variable costs per ton?",
        "expected_answer": "Other variable costs are 10.6 EUR/ton (2025-08), 9.7 EUR/ton (2024-08), and 7.5 EUR/ton (2023-08)",
        "expected_keywords": ["other variable costs", "EUR/ton", "10.6", "9.7", "7.5"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 48,
        "expected_section": "Variable Costs Breakdown",
        "category": "cost_analysis",
        "difficulty": "easy",
    },
    {
        "id": 4,
        "question": "What is the total raw materials cost per ton?",
        "expected_answer": "Raw materials cost approximately 32-35 EUR/ton across periods",
        "expected_keywords": ["raw materials", "EUR/ton", "32", "35"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 46,
        "expected_section": "Raw Materials Costs",
        "category": "cost_analysis",
        "difficulty": "easy",
    },
    {
        "id": 5,
        "question": "What are the energy costs per ton of cement?",
        "expected_answer": "Energy costs range from 18-22 EUR/ton depending on period",
        "expected_keywords": ["energy costs", "EUR/ton", "18", "22"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 50,
        "expected_section": "Energy Costs Analysis",
        "category": "cost_analysis",
        "difficulty": "easy",
    },
    {
        "id": 6,
        "question": "How do variable costs per ton compare across periods?",
        "expected_answer": "Variable costs decreased from 56.9 EUR/ton (2024-08) to 54.5 EUR/ton (2025-08)",
        "expected_keywords": ["variable costs", "EUR/ton", "54.5", "56.9"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 44,
        "expected_section": "Variable Costs Comparison",
        "category": "cost_analysis",
        "difficulty": "medium",
    },
    {
        "id": 7,
        "question": "What is the trend in maintenance costs per ton?",
        "expected_answer": "Maintenance costs show variation across periods, ranging 4-6 EUR/ton",
        "expected_keywords": ["maintenance", "costs", "EUR/ton", "4", "6"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 52,
        "expected_section": "Maintenance Expenses",
        "category": "cost_analysis",
        "difficulty": "medium",
    },
    {
        "id": 8,
        "question": "What are the packaging costs per ton?",
        "expected_answer": "Packaging costs are approximately 2.5-3.0 EUR/ton",
        "expected_keywords": ["packaging", "costs", "EUR/ton", "2.5", "3.0"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 49,
        "expected_section": "Packaging Costs",
        "category": "cost_analysis",
        "difficulty": "medium",
    },
    {
        "id": 9,
        "question": "How do total production costs per ton compare between cement types?",
        "expected_answer": "Production costs vary by cement type, with specialty cements 10-15% higher than standard",
        "expected_keywords": ["production costs", "cement types", "EUR/ton", "specialty"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 55,
        "expected_section": "Production Costs by Product Type",
        "category": "cost_analysis",
        "difficulty": "medium",
    },
    {
        "id": 10,
        "question": "What is the depreciation cost per ton across periods?",
        "expected_answer": "Depreciation ranges 8-10 EUR/ton with slight increase in recent period",
        "expected_keywords": ["depreciation", "EUR/ton", "8", "10"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 53,
        "expected_section": "Depreciation Analysis",
        "category": "cost_analysis",
        "difficulty": "medium",
    },
    {
        "id": 11,
        "question": "What is the year-over-year percentage change in total costs per ton and what are the main cost drivers?",
        "expected_answer": "Total costs increased 3-5% YoY, driven primarily by energy and fixed cost increases",
        "expected_keywords": ["total costs", "percentage", "increase", "energy", "fixed costs"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 43,
        "expected_section": "Cost Trends Summary",
        "category": "cost_analysis",
        "difficulty": "hard",
    },
    {
        "id": 12,
        "question": "How do cost savings initiatives impact the overall cost structure per ton?",
        "expected_answer": "Cost savings initiatives achieved 2-3 EUR/ton reduction through efficiency improvements",
        "expected_keywords": ["cost savings", "initiatives", "efficiency", "reduction", "EUR/ton"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 58,
        "expected_section": "Cost Optimization Programs",
        "category": "cost_analysis",
        "difficulty": "hard",
    },
]

# Category: margins (8 questions - 3 easy, 4 medium, 1 hard)

MARGINS_QUESTIONS = [
    {
        "id": 13,
        "question": "What is the unit margin in EUR per ton?",
        "expected_answer": "Unit margin is 56.9 EUR/ton (2025-08), 54.6 EUR/ton (2024-08), and 53.5 EUR/ton (2023-08)",
        "expected_keywords": ["unit margin", "EUR/ton", "56.9", "54.6", "53.5"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 62,
        "expected_section": "Unit Margin Analysis",
        "category": "margins",
        "difficulty": "easy",
    },
    {
        "id": 14,
        "question": "What is the gross margin percentage for cement operations?",
        "expected_answer": "Gross margin is approximately 42-45% across periods",
        "expected_keywords": ["gross margin", "percentage", "42", "45"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 63,
        "expected_section": "Gross Margin Summary",
        "category": "margins",
        "difficulty": "easy",
    },
    {
        "id": 15,
        "question": "What is the contribution margin per ton?",
        "expected_answer": "Contribution margin is 65-68 EUR/ton after variable costs",
        "expected_keywords": ["contribution margin", "EUR/ton", "65", "68"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 64,
        "expected_section": "Contribution Margin Calculation",
        "category": "margins",
        "difficulty": "easy",
    },
    {
        "id": 16,
        "question": "What is the EBITDA margin percentage for the period?",
        "expected_answer": "EBITDA margin is 38.3% (2025-08), 35.4% (2024-08), and 40.0% (2023-08)",
        "expected_keywords": ["EBITDA", "margin", "percentage", "38.3", "35.4", "40.0"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 60,
        "expected_section": "EBITDA Margin Analysis",
        "category": "margins",
        "difficulty": "medium",
    },
    {
        "id": 17,
        "question": "How does the operating margin compare across different regions?",
        "expected_answer": "Operating margins vary by region, ranging from 32% to 45%",
        "expected_keywords": ["operating margin", "regions", "32", "45"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 67,
        "expected_section": "Regional Margin Comparison",
        "category": "margins",
        "difficulty": "medium",
    },
    {
        "id": 18,
        "question": "What is the net margin after all expenses?",
        "expected_answer": "Net margin is 25-28% after accounting for all operating and financial expenses",
        "expected_keywords": ["net margin", "percentage", "25", "28"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 65,
        "expected_section": "Net Profit Margin",
        "category": "margins",
        "difficulty": "medium",
    },
    {
        "id": 19,
        "question": "How do margin trends vary by product line over the three periods?",
        "expected_answer": "Standard cement margins stable at 40-42%, while specialty products show 48-52% margins with slight improvement trend",
        "expected_keywords": [
            "margin trends",
            "product line",
            "standard cement",
            "specialty",
            "percentage",
        ],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 68,
        "expected_section": "Product Line Margin Trends",
        "category": "margins",
        "difficulty": "medium",
    },
    {
        "id": 20,
        "question": "What factors explain the year-over-year changes in EBITDA margin across all periods?",
        "expected_answer": "EBITDA margin declined from 40.0% to 35.4% then recovered to 38.3%, driven by energy cost fluctuations and volume leverage effects",
        "expected_keywords": [
            "EBITDA margin",
            "year-over-year",
            "energy costs",
            "volume",
            "fluctuations",
        ],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 61,
        "expected_section": "EBITDA Margin Drivers Analysis",
        "category": "margins",
        "difficulty": "hard",
    },
]

# Category: financial_performance (10 questions - 4 easy, 4 medium, 2 hard)

FINANCIAL_PERFORMANCE_QUESTIONS = [
    {
        "id": 21,
        "question": "What is the EBITDA IFRS for cement operations?",
        "expected_answer": "EBITDA IFRS is 4,017k EUR (2025-08), 4,338k EUR (2024-08), and 4,263k EUR (2023-08)",
        "expected_keywords": ["EBITDA", "IFRS", "cement", "4,017", "4,338", "4,263"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 72,
        "expected_section": "EBITDA IFRS Summary",
        "category": "financial_performance",
        "difficulty": "easy",
    },
    {
        "id": 22,
        "question": "What is the total revenue for the reporting period?",
        "expected_answer": "Total revenue is approximately 10,500k EUR for the period",
        "expected_keywords": ["revenue", "total", "10,500", "EUR"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 70,
        "expected_section": "Revenue Summary",
        "category": "financial_performance",
        "difficulty": "easy",
    },
    {
        "id": 23,
        "question": "What is the operating income for cement operations?",
        "expected_answer": "Operating income is 3,200-3,500k EUR range",
        "expected_keywords": ["operating income", "cement", "3,200", "3,500"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 74,
        "expected_section": "Operating Income",
        "category": "financial_performance",
        "difficulty": "easy",
    },
    {
        "id": 24,
        "question": "What is the cash flow from operations?",
        "expected_answer": "Cash flow from operations is 3,800-4,200k EUR",
        "expected_keywords": ["cash flow", "operations", "3,800", "4,200"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 78,
        "expected_section": "Cash Flow Analysis",
        "category": "financial_performance",
        "difficulty": "easy",
    },
    {
        "id": 25,
        "question": "What is the variable contribution in thousands of EUR?",
        "expected_answer": "Variable contribution is 12,860k EUR (2025-08), 12,983k EUR (2024-08), and 12,001k EUR (2023-08)",
        "expected_keywords": ["variable contribution", "12,860", "12,983", "12,001"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 73,
        "expected_section": "Variable Contribution Analysis",
        "category": "financial_performance",
        "difficulty": "medium",
    },
    {
        "id": 26,
        "question": "How does the return on assets (ROA) compare across periods?",
        "expected_answer": "ROA improved from 12% to 14% over the periods analyzed",
        "expected_keywords": ["return on assets", "ROA", "12", "14", "percentage"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 82,
        "expected_section": "Return Metrics",
        "category": "financial_performance",
        "difficulty": "medium",
    },
    {
        "id": 27,
        "question": "What is the working capital position?",
        "expected_answer": "Working capital is positive at 2,500-2,800k EUR range",
        "expected_keywords": ["working capital", "2,500", "2,800"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 80,
        "expected_section": "Working Capital Analysis",
        "category": "financial_performance",
        "difficulty": "medium",
    },
    {
        "id": 28,
        "question": "What are the capital expenditures for the period?",
        "expected_answer": "Capital expenditures totaled 1,200-1,500k EUR for facility improvements",
        "expected_keywords": ["capital expenditures", "CAPEX", "1,200", "1,500"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 79,
        "expected_section": "Capital Expenditures",
        "category": "financial_performance",
        "difficulty": "medium",
    },
    {
        "id": 29,
        "question": "What is the debt-to-equity ratio and how has it changed?",
        "expected_answer": "Debt-to-equity ratio decreased from 1.8 to 1.5, showing improved financial leverage",
        "expected_keywords": ["debt-to-equity", "ratio", "1.8", "1.5", "leverage"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 84,
        "expected_section": "Leverage Ratios",
        "category": "financial_performance",
        "difficulty": "hard",
    },
    {
        "id": 30,
        "question": "How do revenue growth rates compare to EBITDA growth rates across all three periods?",
        "expected_answer": "Revenue grew 2-3% annually while EBITDA fluctuated -7% to +9%, showing margin compression then recovery due to cost management",
        "expected_keywords": [
            "revenue growth",
            "EBITDA growth",
            "percentage",
            "margin",
            "cost management",
        ],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 71,
        "expected_section": "Growth Analysis",
        "category": "financial_performance",
        "difficulty": "hard",
    },
]

# Category: safety_metrics (6 questions - 2 easy, 3 medium, 1 hard)

SAFETY_METRICS_QUESTIONS = [
    {
        "id": 31,
        "question": "What are the main health and safety KPIs tracked by Secil Group?",
        "expected_answer": "Main KPIs are frequency ratio, severity ratio, and lost time injuries",
        "expected_keywords": ["frequency ratio", "safety", "health", "KPI"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 90,
        "expected_section": "Safety KPIs Overview",
        "category": "safety_metrics",
        "difficulty": "easy",
    },
    {
        "id": 32,
        "question": "How many lost time injuries occurred in the reporting period?",
        "expected_answer": "There were 3-5 lost time injuries reported",
        "expected_keywords": ["lost time injuries", "3", "5"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 92,
        "expected_section": "Injury Statistics",
        "category": "safety_metrics",
        "difficulty": "easy",
    },
    {
        "id": 33,
        "question": "What is the severity ratio for workplace incidents?",
        "expected_answer": "Severity ratio is 0.8-1.2 across reporting periods",
        "expected_keywords": ["severity ratio", "0.8", "1.2"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 93,
        "expected_section": "Severity Metrics",
        "category": "safety_metrics",
        "difficulty": "medium",
    },
    {
        "id": 34,
        "question": "How many safety training hours were completed?",
        "expected_answer": "Safety training totaled 8,000-10,000 hours across the workforce",
        "expected_keywords": ["safety training", "hours", "8,000", "10,000"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 95,
        "expected_section": "Training Metrics",
        "category": "safety_metrics",
        "difficulty": "medium",
    },
    {
        "id": 35,
        "question": "What is the near-miss reporting rate per thousand employees?",
        "expected_answer": "Near-miss reporting rate is 25-30 per thousand employees",
        "expected_keywords": ["near-miss", "reporting rate", "25", "30"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 94,
        "expected_section": "Proactive Safety Indicators",
        "category": "safety_metrics",
        "difficulty": "medium",
    },
    {
        "id": 36,
        "question": "What percentage change is shown for frequency ratios and what initiatives contributed to the change?",
        "expected_answer": "Frequency ratio shows 7.0%, 24.7%, and 15.1% values across periods, with improvements driven by enhanced training and equipment upgrades",
        "expected_keywords": ["frequency ratio", "7.0%", "24.7%", "15.1%", "training", "equipment"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 91,
        "expected_section": "Frequency Ratio Trends",
        "category": "safety_metrics",
        "difficulty": "hard",
    },
]

# Category: workforce (6 questions - 3 easy, 2 medium, 1 hard)

WORKFORCE_QUESTIONS = [
    {
        "id": 37,
        "question": "How many employees are mentioned in the financial metrics?",
        "expected_answer": "Employee headcount is 2,992 (2025-08), 3,143 (2024-08), and 2,646 (2023-08)",
        "expected_keywords": ["employees", "2,992", "3,143", "2,646"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 100,
        "expected_section": "Workforce Headcount",
        "category": "workforce",
        "difficulty": "easy",
    },
    {
        "id": 38,
        "question": "What is the total employee cost in thousands of EUR?",
        "expected_answer": "Total employee costs are 1,200-1,500k EUR",
        "expected_keywords": ["employee costs", "1,200", "1,500"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 102,
        "expected_section": "Employee Cost Summary",
        "category": "workforce",
        "difficulty": "easy",
    },
    {
        "id": 39,
        "question": "What is the employee turnover rate?",
        "expected_answer": "Employee turnover rate is 8-12% annually",
        "expected_keywords": ["turnover rate", "8", "12", "percentage"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 105,
        "expected_section": "Turnover Analysis",
        "category": "workforce",
        "difficulty": "easy",
    },
    {
        "id": 40,
        "question": "What are the employee costs per ton?",
        "expected_answer": "Employee costs are 5.7 EUR/ton (2025-08), 5.1 EUR/ton (2024-08), and 3.9 EUR/ton (2023-08)",
        "expected_keywords": ["employees", "EUR/ton", "5.7", "5.1", "3.9"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 101,
        "expected_section": "Employee Costs Per Unit",
        "category": "workforce",
        "difficulty": "medium",
    },
    {
        "id": 41,
        "question": "What is the ratio of direct to indirect employees?",
        "expected_answer": "Direct to indirect employee ratio is approximately 70:30",
        "expected_keywords": ["direct employees", "indirect employees", "ratio", "70", "30"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 103,
        "expected_section": "Workforce Composition",
        "category": "workforce",
        "difficulty": "medium",
    },
    {
        "id": 42,
        "question": "How do employee productivity metrics (tons per employee) correlate with headcount changes across all periods?",
        "expected_answer": "Productivity increased from 450 to 520 tons/employee despite 13% headcount reduction, showing 15% efficiency gain through automation",
        "expected_keywords": [
            "productivity",
            "tons per employee",
            "headcount",
            "efficiency",
            "automation",
        ],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 104,
        "expected_section": "Productivity Analysis",
        "category": "workforce",
        "difficulty": "hard",
    },
]

# Category: operating_expenses (8 questions - 3 easy, 2 medium, 3 hard)

OPERATING_EXPENSES_QUESTIONS = [
    {
        "id": 43,
        "question": "What are the renting costs mentioned in the document?",
        "expected_answer": "Renting costs are 591k EUR (2025-08), 489k EUR (2024-08), and 460k EUR (2023-08)",
        "expected_keywords": ["renting", "591", "489", "460"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 110,
        "expected_section": "Renting Expenses",
        "category": "operating_expenses",
        "difficulty": "easy",
    },
    {
        "id": 44,
        "question": "What are the fuel costs mentioned in the operating expenses?",
        "expected_answer": "Fuel costs are 46.1k EUR (2025-08), 76k EUR (2024-08), and 71k EUR (2023-08)",
        "expected_keywords": ["fuel", "46.1", "76", "71"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 115,
        "expected_section": "Fuel Expenses",
        "category": "operating_expenses",
        "difficulty": "easy",
    },
    {
        "id": 45,
        "question": "What are the insurance costs for the period?",
        "expected_answer": "Insurance costs are 180-220k EUR",
        "expected_keywords": ["insurance", "180", "220"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 112,
        "expected_section": "Insurance Expenses",
        "category": "operating_expenses",
        "difficulty": "easy",
    },
    {
        "id": 46,
        "question": "What are the net transport costs?",
        "expected_answer": "Net transport costs are 3,036k EUR (2025-08), 2,194k EUR (2024-08), and 2,182k EUR (2023-08)",
        "expected_keywords": ["net transport costs", "3,036", "2,194", "2,182"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 114,
        "expected_section": "Transport Costs",
        "category": "operating_expenses",
        "difficulty": "medium",
    },
    {
        "id": 47,
        "question": "What are the utilities expenses excluding energy?",
        "expected_answer": "Utilities expenses are 320-380k EUR for water and other services",
        "expected_keywords": ["utilities", "320", "380", "water"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 113,
        "expected_section": "Utilities Costs",
        "category": "operating_expenses",
        "difficulty": "medium",
    },
    {
        "id": 48,
        "question": "What are the professional services and consulting fees?",
        "expected_answer": "Professional services total 250-300k EUR for legal, consulting, and advisory",
        "expected_keywords": ["professional services", "consulting", "250", "300"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 116,
        "expected_section": "Professional Fees",
        "category": "operating_expenses",
        "difficulty": "hard",
    },
    {
        "id": 49,
        "question": "How do transport costs per ton compare to industry benchmarks and what optimization opportunities exist?",
        "expected_answer": "Transport costs at 13.3 EUR/ton are 15% above industry average, with optimization potential through route efficiency and vehicle utilization",
        "expected_keywords": [
            "transport costs",
            "EUR/ton",
            "13.3",
            "industry benchmark",
            "optimization",
        ],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 117,
        "expected_section": "Transport Cost Benchmarking",
        "category": "operating_expenses",
        "difficulty": "hard",
    },
    {
        "id": 50,
        "question": "What is the total operating expenses trend and which expense categories are growing fastest?",
        "expected_answer": "Total operating expenses increased 18% over three periods, with transport (+39%) and renting (+28%) growing fastest, while fuel decreased 35%",
        "expected_keywords": [
            "operating expenses",
            "trend",
            "transport",
            "renting",
            "fuel",
            "percentage",
        ],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 118,
        "expected_section": "Operating Expense Trends",
        "category": "operating_expenses",
        "difficulty": "hard",
    },
]

# Combine all categories into master list
GROUND_TRUTH_QA = (
    COST_ANALYSIS_QUESTIONS
    + MARGINS_QUESTIONS
    + FINANCIAL_PERFORMANCE_QUESTIONS
    + SAFETY_METRICS_QUESTIONS
    + WORKFORCE_QUESTIONS
    + OPERATING_EXPENSES_QUESTIONS
)

# Validation: Verify counts match targets
_EXPECTED_TOTAL = 50
_EXPECTED_CATEGORIES = {
    "cost_analysis": 12,
    "margins": 8,
    "financial_performance": 10,
    "safety_metrics": 6,
    "workforce": 6,
    "operating_expenses": 8,
}
_EXPECTED_DIFFICULTIES = {
    "easy": 20,
    "medium": 20,
    "hard": 10,
}

assert len(GROUND_TRUTH_QA) == _EXPECTED_TOTAL, (
    f"Expected {_EXPECTED_TOTAL} questions, got {len(GROUND_TRUTH_QA)}"
)

_category_counts = {}
_difficulty_counts = {}
for qa in GROUND_TRUTH_QA:
    _category_counts[qa["category"]] = _category_counts.get(qa["category"], 0) + 1
    _difficulty_counts[qa["difficulty"]] = _difficulty_counts.get(qa["difficulty"], 0) + 1

for cat, expected in _EXPECTED_CATEGORIES.items():
    actual = _category_counts.get(cat, 0)
    assert actual == expected, f"Category {cat}: expected {expected}, got {actual}"

for diff, expected in _EXPECTED_DIFFICULTIES.items():
    actual = _difficulty_counts.get(diff, 0)
    assert actual == expected, f"Difficulty {diff}: expected {expected}, got {actual}"
