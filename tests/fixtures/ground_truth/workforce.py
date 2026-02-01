"""
Ground Truth Questions - Workforce (6 questions)

Difficulty Distribution:
- Easy: 2
- Medium: 3
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


# Category: workforce (6 questions - 2 easy, 3 medium, 1 hard)

WORKFORCE_QUESTIONS = [
    {
        "id": 37,
        "question": "What are the employee costs per ton for Portugal Cement?",
        "expected_answer": "Employee costs are 6.6 EUR/ton (Aug-25 YTD), compared to budget of 6.0 EUR/ton and 5.6 EUR/ton (Aug-24)",
        "expected_keywords": ["employees", "6.6", "EUR/ton", "6.0", "5.6"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 46,
        "expected_section": "Portugal Cement - Operational Performance",
        "category": "workforce",
        "difficulty": "easy",
    },
    {
        "id": 38,
        "question": "How many FTEs work in distribution for Portugal Cement?",
        "expected_answer": "Distribution has 18 FTEs (Aug-25), compared to budget of 19 FTEs and 19 FTEs (Aug-24)",
        "expected_keywords": ["distribution", "FTEs", "18", "19"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 46,
        "expected_section": "Portugal Cement - Operational Performance",
        "category": "workforce",
        "difficulty": "easy",
    },
    {
        "id": 39,
        "question": "What is the total headcount for Tunisia operations in August 2025?",
        "expected_answer": "Tunisia operations have 536 employees in August 2025, compared to budget of 317 and 0 in prior months, with Tunisia Cement having 350 employees",
        "expected_keywords": ["tunisia", "headcount", "536", "350", "employees"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 108,
        "expected_section": "Tunisia - Headcount Evolution",
        "category": "workforce",
        "difficulty": "medium",
    },
    {
        "id": 40,
        "question": "How many FTEs are in sales for Portugal Cement?",
        "expected_answer": "Sales has 16 FTEs (Aug-25), compared to budget of 15 FTEs and 15 FTEs (Aug-24), showing 7% increase",
        "expected_keywords": ["sales", "FTEs", "16", "15", "7%"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 46,
        "expected_section": "Portugal Cement - Operational Performance",
        "category": "workforce",
        "difficulty": "medium",
    },
    {
        "id": 41,
        "question": "What is the breakdown of Tunisia Cement employees by function?",
        "expected_answer": "Tunisia Cement (350 employees in Aug-25) consists of Plants (238), Distribution (84), and Sales (28) employees",
        "expected_keywords": [
            "tunisia cement",
            "350",
            "plants",
            "238",
            "distribution",
            "84",
            "sales",
            "28",
        ],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 46,
        "expected_section": "Tunisia - Headcount Evolution",
        "category": "workforce",
        "difficulty": "medium",
    },
    {
        "id": 42,
        "question": "How does employee cost per ton efficiency compare across periods and what factors drive the changes?",
        "expected_answer": "Employee costs increased from 5.6 EUR/ton (Aug-24) to 6.6 EUR/ton (Aug-25 YTD), showing 18% increase, while FTEs increased from 222 to 232, suggesting higher per-employee costs despite scale economies",
        "expected_keywords": [
            "employee costs",
            "6.6",
            "5.6",
            "EUR/ton",
            "FTEs",
            "232",
            "222",
            "increase",
        ],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 46,
        "expected_section": "Portugal Cement - Operational Performance",
        "category": "workforce",
        "difficulty": "hard",
    },
]
