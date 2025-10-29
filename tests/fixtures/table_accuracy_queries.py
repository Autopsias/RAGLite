"""
Ground Truth Table Queries for AC3 Validation - Story 2.1

This module contains 10 validated table-specific queries for testing pypdfium backend
table extraction accuracy (AC3: ≥97.9% table accuracy requirement).

Selected from the 50-question GROUND_TRUTH_QA dataset, filtered for table-heavy queries
that test multi-column extraction, exact number matching, and complex table structures.

Usage:
    Import TABLE_ACCURACY_QUERIES for AC3 pypdfium validation:
    >>> from tests.fixtures.table_accuracy_queries import TABLE_ACCURACY_QUERIES
    >>> for query in TABLE_ACCURACY_QUERIES:
    ...     # Run table extraction test
    ...     pass

Source Document: 2025-08 Performance Review CONSO_v2.pdf (160 pages)
Validation Method: Subset of GROUND_TRUTH_QA (50 questions) filtered for table queries
Story: 2.1 - Implement pypdfium Backend for Docling
Acceptance Criteria: AC3 - Table Accuracy Maintained (≥97.9%)

Data Structure:
    Each query inherits structure from GroundTruthQuestion:
    - id: Unique identifier from GROUND_TRUTH_QA
    - question: Natural language query targeting table data
    - expected_answer: Validated answer from PDF table
    - expected_keywords: Keywords for validation (exact numbers, units)
    - source_document: Source PDF filename
    - expected_page_number: Page containing the table
    - expected_section: Table/section identifier
    - category: Query category
    - difficulty: easy, medium, or hard

Coverage:
- Pages: 3 tables (page 46 operational, page 47 margins, page 77 cash flow)
- Data Types: Costs, percentages, financial metrics, margins
- Difficulty: 7 easy, 2 medium, 1 hard (focus on reliable baseline)
- Table Complexity: Single-column, multi-column, row-based lookups

Last Updated: 2025-10-19
Created By: Senior Developer (AI) - Story 2.1 Review (AI1: Define Ground Truth Queries)
"""

from typing import TypedDict, cast


class TableAccuracyQuery(TypedDict):
    """Type definition for table accuracy validation queries."""

    id: int
    question: str
    expected_answer: str
    expected_keywords: list[str]
    source_document: str
    expected_page_number: int
    expected_section: str
    category: str
    difficulty: str


# 10 Table-Specific Queries for AC3 Validation (Story 2.1)
# Selected from GROUND_TRUTH_QA for high table dependency and varied complexity

TABLE_ACCURACY_QUERIES_LIST = [
    {
        "id": 1,
        "question": "What is the variable cost per ton for Portugal Cement in August 2025 YTD?",
        "expected_answer": "Variable costs for Portugal Cement are 23.2 EUR/ton (Aug-25 YTD), compared to budget of 20.3 EUR/ton and 29.4 EUR/ton in Aug-24",
        "expected_keywords": ["variable costs", "23.2", "EUR/ton", "20.3", "29.4"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 46,
        "expected_section": "Portugal Cement - Operational Performance",
        "category": "cost_analysis",
        "difficulty": "easy",
    },
    {
        "id": 2,
        "question": "What is the thermal energy cost per ton for Portugal Cement?",
        "expected_answer": "Thermal energy costs are 5.8 EUR/ton (Aug-25 YTD), 5.7 EUR/ton (Budget), and 8.3 EUR/ton (Aug-24)",
        "expected_keywords": ["termic energy", "thermal energy", "5.8", "EUR/ton", "8.3"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 46,
        "expected_section": "Portugal Cement - Operational Performance",
        "category": "cost_analysis",
        "difficulty": "easy",
    },
    {
        "id": 3,
        "question": "What is the electricity cost per ton for Portugal Cement operations?",
        "expected_answer": "Electricity costs are 7.8 EUR/ton (Aug-25 YTD), 4.4 EUR/ton (Budget), and 9.6 EUR/ton (Aug-24)",
        "expected_keywords": ["electricity", "7.8", "EUR/ton", "4.4", "9.6"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 46,
        "expected_section": "Portugal Cement - Operational Performance",
        "category": "cost_analysis",
        "difficulty": "easy",
    },
    {
        "id": 6,
        "question": "What is the alternative fuel rate percentage for Portugal Cement?",
        "expected_answer": "Alternative fuel rate is 50% (Aug-25 YTD), 60% (Budget), and 42% (Aug-24)",
        "expected_keywords": ["alternative fuel", "50%", "60%", "42%"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 46,
        "expected_section": "Portugal Cement - Operational Performance",
        "category": "cost_analysis",
        "difficulty": "easy",
    },
    {
        "id": 13,
        "question": "What is the EBITDA IFRS margin percentage for Portugal Cement?",
        "expected_answer": "EBITDA IFRS margin for Portugal Cement is 50.6% (Aug-25 YTD), 53.2% (Budget), and 40.6% (Aug-24)",
        "expected_keywords": ["EBITDA IFRS margin", "50.6%", "53.2%", "40.6%"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 46,
        "expected_section": "Portugal Cement - Operational Performance",
        "category": "margins",
        "difficulty": "easy",
    },
    {
        "id": 14,
        "question": "What is the EBITDA per ton for Portugal Cement?",
        "expected_answer": "EBITDA is 64.4 EUR/ton (Aug-25 YTD), 67.4 EUR/ton (Budget), and 49.5 EUR/ton (Aug-24)",
        "expected_keywords": ["EBITDA", "64.4", "EUR/ton", "67.4", "49.5"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 46,
        "expected_section": "Portugal Cement - Operational Performance",
        "category": "margins",
        "difficulty": "easy",
    },
    {
        "id": 16,
        "question": "What are the fixed costs per ton for Outão plant?",
        "expected_answer": "Outão plant fixed costs are 23.7 EUR/ton (Aug-25), 21.6 EUR/ton (Budget), and 26.5 EUR/ton (Aug-24)",
        "expected_keywords": ["outão", "fixed costs", "23.7", "EUR/ton", "21.6", "26.5"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 47,
        "expected_section": "Portugal Cement - Margin by Plant",
        "category": "margins",
        "difficulty": "medium",
    },
    {
        "id": 17,
        "question": "What are the fixed costs per ton for Maceira plant?",
        "expected_answer": "Maceira plant fixed costs are 26.8 EUR/ton (Aug-25), 22.1 EUR/ton (Budget), and 20.5 EUR/ton (Aug-24)",
        "expected_keywords": ["maceira", "fixed costs", "26.8", "EUR/ton", "22.1", "20.5"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 47,
        "expected_section": "Portugal Cement - Margin by Plant",
        "category": "margins",
        "difficulty": "medium",
    },
    {
        "id": 21,
        "question": "What is the EBITDA for Portugal operations in Aug-25 YTD?",
        "expected_answer": "EBITDA for Portugal is 104,647 thousand EUR (Aug-25 YTD), compared to budget of 108,942 thousand EUR and 94,845 thousand EUR (Aug-24)",
        "expected_keywords": ["EBITDA portugal", "104,647", "108,942", "94,845", "thousand EUR"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 77,
        "expected_section": "Portugal - Cash Flow",
        "category": "financial_performance",
        "difficulty": "easy",
    },
    {
        "id": 22,
        "question": "What is the cash flow from operating activities?",
        "expected_answer": "Cash flow from operating activities is 7,208 thousand EUR (Aug-25 YTD), compared to budget of 35,616 thousand EUR and 7,136 thousand EUR (Aug-24)",
        "expected_keywords": [
            "CF from operating activities",
            "7,208",
            "35,616",
            "7,136",
            "thousand EUR",
        ],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 77,
        "expected_section": "Portugal - Cash Flow",
        "category": "financial_performance",
        "difficulty": "easy",
    },
]

# Export as typed list
TABLE_ACCURACY_QUERIES: list[TableAccuracyQuery] = cast(
    list[TableAccuracyQuery], TABLE_ACCURACY_QUERIES_LIST
)

# Validation: Ensure 10 queries selected
assert len(TABLE_ACCURACY_QUERIES) == 10, "AC3 requires exactly 10 table accuracy queries"

# Coverage Statistics
COVERAGE_STATS = {
    "total_queries": 10,
    "pages_covered": [46, 47, 77],  # 3 distinct tables
    "difficulty_distribution": {"easy": 7, "medium": 2, "hard": 0},
    "category_distribution": {"cost_analysis": 4, "margins": 4, "financial_performance": 2},
    "table_types": ["operational_performance", "margin_by_plant", "cash_flow"],
}
