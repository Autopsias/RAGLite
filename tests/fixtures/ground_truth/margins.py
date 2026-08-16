"""
Ground Truth Questions - Margins (8 questions)

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


# Category: margins (8 questions - 3 easy, 4 medium, 1 hard)

MARGINS_QUESTIONS = [
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
        "id": 15,
        "question": "What is the unit variable margin per ton?",
        "expected_answer": "Unit variable margin is 90.1 EUR/ton (Aug-25 YTD), 92.0 EUR/ton (Budget), and 78.2 EUR/ton (Aug-24)",
        "expected_keywords": ["unit variable margin", "90.1", "EUR/ton", "92.0", "78.2"],
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
        "id": 18,
        "question": "What is the unit cement EBITDA for Outão plant internal market?",
        "expected_answer": "Outão plant unit cement EBITDA for internal market is 80.5 EUR/ton (Aug-25), 81.9 EUR/ton (Budget), and 65.0 EUR/ton (Aug-24)",
        "expected_keywords": ["outão", "unit cement ebitda", "80.5", "EUR/ton", "81.9", "65.0"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 47,
        "expected_section": "Portugal Cement - Margin by Plant",
        "category": "margins",
        "difficulty": "medium",
    },
    {
        "id": 19,
        "question": "What are the fixed costs per ton for Pataias plant and how do they compare to other plants?",
        "expected_answer": "Pataias plant fixed costs are 59.8 EUR/ton (Aug-25), significantly higher than Outão (23.7) and Maceira (26.8), reflecting its smaller scale of operations",
        "expected_keywords": ["pataias", "fixed costs", "59.8", "EUR/ton", "outão", "maceira"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 47,
        "expected_section": "Portugal Cement - Margin by Plant",
        "category": "margins",
        "difficulty": "medium",
    },
    {
        "id": 20,
        "question": "How does the EBITDA margin improvement from Aug-24 to Aug-25 YTD relate to variable and fixed cost changes?",
        "expected_answer": "EBITDA margin improved from 40.6% to 50.6% (10 pp increase) driven by variable cost reduction of 21% (from 29.4 to 23.2 EUR/ton) while fixed costs remained stable at 27.4 EUR/ton, demonstrating operational efficiency gains",
        "expected_keywords": [
            "EBITDA margin",
            "50.6%",
            "40.6%",
            "10 pp",
            "variable costs",
            "fixed costs",
            "efficiency",
        ],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 46,
        "expected_section": "Portugal Cement - Operational Performance",
        "category": "margins",
        "difficulty": "hard",
    },
]
