"""
Ground Truth Questions - Operating Expenses (8 questions)

Difficulty Distribution:
- Easy: 3
- Medium: 4
- Hard: 1

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


# Category: operating_expenses (8 questions - 3 easy, 4 medium, 1 hard)

OPERATING_EXPENSES_QUESTIONS = [
    {
        "id": 43,
        "question": "What are the other costs per ton for Portugal Cement operations?",
        "expected_answer": "Other costs are 9.8 EUR/ton (Aug-25 YTD), compared to budget of 9.2 EUR/ton and 10.1 EUR/ton (Aug-24)",
        "expected_keywords": ["other costs", "9.8", "EUR/ton", "9.2", "10.1"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 46,
        "expected_section": "Portugal Cement - Operational Performance",
        "category": "operating_expenses",
        "difficulty": "easy",
    },
    {
        "id": 44,
        "question": "What are the distribution costs per ton?",
        "expected_answer": "Distribution costs are 1.7 EUR/ton (Aug-25 YTD), compared to budget of 1.5 EUR/ton and 1.5 EUR/ton (Aug-24)",
        "expected_keywords": ["distribution costs", "1.7", "EUR/ton", "1.5"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 46,
        "expected_section": "Portugal Cement - Operational Performance",
        "category": "operating_expenses",
        "difficulty": "easy",
    },
    {
        "id": 45,
        "question": "What are the sales costs per ton?",
        "expected_answer": "Sales costs are 1.2 EUR/ton (Aug-25 YTD), compared to budget of 1.1 EUR/ton and 1.2 EUR/ton (Aug-24)",
        "expected_keywords": ["sales costs", "1.2", "EUR/ton", "1.1"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 46,
        "expected_section": "Portugal Cement - Operational Performance",
        "category": "operating_expenses",
        "difficulty": "easy",
    },
    {
        "id": 46,
        "question": "What are the insurance costs?",
        "expected_answer": "Insurance costs are (1,072) thousand EUR (Aug-25 YTD), compared to budget of (1,413) thousand EUR and (1,255) thousand EUR (Aug-24)",
        "expected_keywords": ["insurance", "1,072", "1,413", "1,255", "thousand EUR"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 46,
        "expected_section": "Portugal Cement - Operational Performance",
        "category": "operating_expenses",
        "difficulty": "medium",
    },
    {
        "id": 47,
        "question": "What are the rents and rentals costs?",
        "expected_answer": "Rents and rentals are (1,262) thousand EUR (Aug-25 YTD), compared to budget of (807) thousand EUR and (1,273) thousand EUR (Aug-24)",
        "expected_keywords": ["rents", "rentals", "1,262", "807", "1,273"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 46,
        "expected_section": "Portugal Cement - Operational Performance",
        "category": "operating_expenses",
        "difficulty": "medium",
    },
    {
        "id": 48,
        "question": "What are the production services costs?",
        "expected_answer": "Production services are (5,713) thousand EUR (Aug-25 YTD), compared to budget of (5,863) thousand EUR and (5,723) thousand EUR (Aug-24)",
        "expected_keywords": ["production services", "5,713", "5,863", "5,723"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 46,
        "expected_section": "Portugal Cement - Operational Performance",
        "category": "operating_expenses",
        "difficulty": "medium",
    },
    {
        "id": 49,
        "question": "What are the specialized labour costs?",
        "expected_answer": "Specialized labour costs are (1,778) thousand EUR (Aug-25 YTD), compared to budget of (2,490) thousand EUR and (1,732) thousand EUR (Aug-24)",
        "expected_keywords": ["specialized labour", "1,778", "2,490", "1,732"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 46,
        "expected_section": "Portugal Cement - Operational Performance",
        "category": "operating_expenses",
        "difficulty": "medium",
    },
    {
        "id": 50,
        "question": "How do fixed costs break down into employee costs, maintenance, and other costs, and what is the efficiency trend?",
        "expected_answer": "Fixed costs of 27.4 EUR/ton consist of employee costs (6.6), maintenance (11.1), and other costs (9.8). The stable fixed costs vs prior year (27.9) despite 19% reduction in FTEs (from 287 budget to 232 actual) indicates improved labor productivity",
        "expected_keywords": [
            "fixed costs",
            "27.4",
            "employee costs",
            "6.6",
            "maintenance",
            "11.1",
            "other costs",
            "9.8",
            "FTEs",
            "productivity",
        ],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 59,
        "expected_section": "Portugal Cement - Operational Performance",
        "category": "operating_expenses",
        "difficulty": "hard",
    },
]
