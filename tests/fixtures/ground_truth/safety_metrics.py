"""
Ground Truth Questions - Safety Metrics (6 questions)

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


# Category: safety_metrics (6 questions - 2 easy, 3 medium, 1 hard)

SAFETY_METRICS_QUESTIONS = [
    {
        "id": 31,
        "question": "How many FTE employees work in Portugal Cement operations?",
        "expected_answer": "Portugal Cement has 232 FTEs (Aug-25), compared to budget of 287 FTEs and 222 FTEs (Aug-24)",
        "expected_keywords": ["FTEs", "232", "287", "222", "employees"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 46,
        "expected_section": "Portugal Cement - Operational Performance",
        "category": "safety_metrics",
        "difficulty": "easy",
    },
    {
        "id": 32,
        "question": "What is the daily clinker production capacity?",
        "expected_answer": "Daily clinker production is 1.9 kton (Aug-25 YTD), compared to budget of 1.8 kton and 1.6 kton (Aug-24)",
        "expected_keywords": ["daily clinker production", "1.9", "kton", "1.8", "1.6"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 46,
        "expected_section": "Portugal Cement - Operational Performance",
        "category": "safety_metrics",
        "difficulty": "easy",
    },
    {
        "id": 33,
        "question": "What is the reliability factor percentage for cement production?",
        "expected_answer": "Reliability factor is 57% (Aug-25 YTD), compared to budget of 66% and 61% (Aug-24)",
        "expected_keywords": ["reliability factor", "57%", "66%", "61%"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 46,
        "expected_section": "Portugal Cement - Operational Performance",
        "category": "safety_metrics",
        "difficulty": "medium",
    },
    {
        "id": 34,
        "question": "What is the utilization factor in tons for cement production?",
        "expected_answer": "Utilization factor (tons) is 44% (Aug-25 YTD), compared to budget of 59% and 44% (Aug-24)",
        "expected_keywords": ["utilization factor", "tons", "44%", "59%"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 46,
        "expected_section": "Portugal Cement - Operational Performance",
        "category": "safety_metrics",
        "difficulty": "medium",
    },
    {
        "id": 35,
        "question": "What is the performance factor percentage?",
        "expected_answer": "Performance factor is 19% (Aug-25 YTD), compared to budget of 21% and 16% (Aug-24)",
        "expected_keywords": ["performance factor", "19%", "21%", "16%"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 46,
        "expected_section": "Portugal Cement - Operational Performance",
        "category": "safety_metrics",
        "difficulty": "medium",
    },
    {
        "id": 36,
        "question": "What is the CO2 emissions per ton of clinker and how does it compare across periods?",
        "expected_answer": "CO2 emissions are 763 kg/ton clinker (Aug-25 YTD), compared to 748 kg/ton (Budget) and 768 kg/ton (Aug-24), showing 2% increase vs budget but 1% reduction vs prior year",
        "expected_keywords": ["emissions", "CO2", "763", "kg", "ton clinker", "748", "768"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 46,
        "expected_section": "Portugal Cement - Operational Performance",
        "category": "safety_metrics",
        "difficulty": "hard",
    },
]
