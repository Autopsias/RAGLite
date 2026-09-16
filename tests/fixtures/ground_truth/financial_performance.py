"""
Ground Truth Questions - Financial Performance (10 questions)

Difficulty Distribution:
- Easy: 4
- Medium: 3
- Hard: 3

Source: tests/fixtures/ground_truth.py (split for maintainability)
Last Updated: 2025-01-06
"""

from typing import TypedDict


class GroundTruthQuestion(TypedDict):
    """Type definition for ground truth question-answer pairs."""

    id: int
    question: str
    expected_answer: str
    expected_keywords: list[str]
    source_document: str
    expected_page_number: int
    expected_section: str
    category: str
    difficulty: str


# Category: financial_performance (10 questions - 4 easy, 3 medium, 3 hard)

FINANCIAL_PERFORMANCE_QUESTIONS = [
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
    {
        "id": 23,
        "question": "What are the capital expenditures (Capex) for the period?",
        "expected_answer": "Capital expenditures are (33,059) thousand EUR (Aug-25 YTD), compared to budget of (52,506) thousand EUR and (32,456) thousand EUR (Aug-24)",
        "expected_keywords": ["capex", "33,059", "52,506", "32,456", "thousand EUR"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 77,
        "expected_section": "Portugal - Cash Flow",
        "category": "financial_performance",
        "difficulty": "easy",
    },
    {
        "id": 24,
        "question": "What is the financial net debt closing balance?",
        "expected_answer": "Financial net debt closing balance is 244,709 thousand EUR (Aug-25), compared to budget of 258,679 thousand EUR and 233,686 thousand EUR (Aug-24)",
        "expected_keywords": [
            "financial net debt",
            "closing balance",
            "244,709",
            "258,679",
            "233,686",
        ],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 23,
        "expected_section": "Portugal - Cash Flow",
        "category": "financial_performance",
        "difficulty": "easy",
    },
    {
        "id": 25,
        "question": "What is the change in trade working capital?",
        "expected_answer": "Trade working capital decreased by (30,913) thousand EUR (Aug-25 YTD), compared to budget increase of 5,862 thousand EUR and decrease of (7,623) thousand EUR (Aug-24)",
        "expected_keywords": ["trade working capital", "30,913", "5,862", "7,623"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 23,
        "expected_section": "Portugal - Cash Flow",
        "category": "financial_performance",
        "difficulty": "medium",
    },
    {
        "id": 26,
        "question": "What are the income tax payments for the period?",
        "expected_answer": "Income tax is (11,801) thousand EUR (Aug-25 YTD), compared to budget of (16,051) thousand EUR and (7,187) thousand EUR (Aug-24)",
        "expected_keywords": ["income tax", "11,801", "16,051", "7,187"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 23,
        "expected_section": "Portugal - Cash Flow",
        "category": "financial_performance",
        "difficulty": "medium",
    },
    {
        "id": 27,
        "question": "What are the net interest expenses?",
        "expected_answer": "Net interest expenses are (6,853) thousand EUR (Aug-25 YTD), compared to budget of (5,699) thousand EUR and (4,994) thousand EUR (Aug-24)",
        "expected_keywords": ["net interest expenses", "6,853", "5,699", "4,994"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 23,
        "expected_section": "Portugal - Cash Flow",
        "category": "financial_performance",
        "difficulty": "hard",
    },
    {
        "id": 28,
        "question": "What is the cash set free or tied up after investments?",
        "expected_answer": "Cash tied up after investments is (25,851) thousand EUR (Aug-25 YTD), compared to budget of (16,889) thousand EUR and (25,320) thousand EUR (Aug-24)",
        "expected_keywords": ["cash set free", "tied up", "investments", "25,851", "16,889"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 23,
        "expected_section": "Portugal - Cash Flow",
        "category": "financial_performance",
        "difficulty": "medium",
    },
    {
        "id": 29,
        "question": "How does the EBITDA Portugal plus Group Structure compare across periods and what is the growth rate?",
        "expected_answer": "EBITDA Portugal plus Group Structure is 91,438 thousand EUR (Aug-25 YTD) vs 77,992 thousand EUR (Aug-24), showing 17% growth year-over-year despite being 2% below budget",
        "expected_keywords": ["EBITDA", "group structure", "91,438", "77,992", "17%", "growth"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 23,
        "expected_section": "Portugal - Cash Flow",
        "category": "financial_performance",
        "difficulty": "hard",
    },
    {
        "id": 30,
        "question": "What is the relationship between cash flow from operations and working capital changes?",
        "expected_answer": "CF from operations decreased to 25,862 thousand EUR (55% below budget) primarily due to significant trade working capital decrease of (30,913) thousand EUR, demonstrating that strong EBITDA growth was offset by working capital outflows",
        "expected_keywords": [
            "CF from operations",
            "25,862",
            "working capital",
            "30,913",
            "EBITDA",
        ],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 23,
        "expected_section": "Portugal - Cash Flow",
        "category": "financial_performance",
        "difficulty": "hard",
    },
]
