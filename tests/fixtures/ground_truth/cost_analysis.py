"""
Ground Truth Questions - Cost Analysis (12 questions)

Difficulty Distribution:
- Easy: 6
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


# Category: cost_analysis (12 questions - 6 easy, 3 medium, 3 hard)

COST_ANALYSIS_QUESTIONS = [
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
        "id": 4,
        "question": "What are the raw materials costs per ton?",
        "expected_answer": "Raw materials costs are 3.5 EUR/ton (Aug-25 YTD), 4.2 EUR/ton (Budget), and 6.2 EUR/ton (Aug-24)",
        "expected_keywords": ["raw materials", "3.5", "EUR/ton", "4.2", "6.2"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 46,
        "expected_section": "Portugal Cement - Operational Performance",
        "category": "cost_analysis",
        "difficulty": "easy",
    },
    {
        "id": 5,
        "question": "What are the packaging costs per ton for cement?",
        "expected_answer": "Packaging costs are 3.7 EUR/ton (Aug-25 YTD), 3.3 EUR/ton (Budget), and 3.3 EUR/ton (Aug-24)",
        "expected_keywords": ["packaging", "3.7", "EUR/ton", "3.3"],
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
        "id": 7,
        "question": "What are the maintenance costs per ton?",
        "expected_answer": "Maintenance costs are 11.1 EUR/ton (Aug-25 YTD), 9.5 EUR/ton (Budget), and 12.2 EUR/ton (Aug-24)",
        "expected_keywords": ["maintenance costs", "11.1", "EUR/ton", "9.5", "12.2"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 46,
        "expected_section": "Portugal Cement - Operational Performance",
        "category": "cost_analysis",
        "difficulty": "medium",
    },
    {
        "id": 8,
        "question": "What is the electricity specific consumption for clinker grey production?",
        "expected_answer": "Electricity specific consumption for clinker grey is 77 Kwh/ton (Aug-25 YTD), 58 Kwh/ton (Budget), and 78 Kwh/ton (Aug-24)",
        "expected_keywords": ["electricity spec", "clinker grey", "77", "Kwh/ton", "78"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 46,
        "expected_section": "Portugal Cement - Operational Performance",
        "category": "cost_analysis",
        "difficulty": "hard",
    },
    {
        "id": 9,
        "question": "What is the thermal energy specific consumption in Kcal/kg clinker?",
        "expected_answer": "Thermal energy specific consumption is 835 Kcal/kg clk (Aug-25 YTD), 847 Kcal/kg clk (Budget), and 881 Kcal/kg clk (Aug-24)",
        "expected_keywords": ["termic energy spec", "835", "Kcal/kg", "clk", "847"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 46,
        "expected_section": "Portugal Cement - Operational Performance",
        "category": "cost_analysis",
        "difficulty": "medium",
    },
    {
        "id": 10,
        "question": "What is the external electricity price per MWh?",
        "expected_answer": "External electricity price is 61.4 EUR/MWh (Aug-25 YTD), 41.8 EUR/MWh (Budget), and 77.5 EUR/MWh (Aug-24)",
        "expected_keywords": ["external electricity", "61.4", "EUR/MWh", "41.8", "77.5"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 46,
        "expected_section": "Portugal Cement - Operational Performance",
        "category": "cost_analysis",
        "difficulty": "medium",
    },
    {
        "id": 11,
        "question": "How do total variable costs per ton compare across the three periods and what is the trend?",
        "expected_answer": "Variable costs decreased from 29.4 EUR/ton (Aug-24) to 23.2 EUR/ton (Aug-25 YTD), showing 21% reduction year-over-year, driven by lower thermal energy and electricity costs",
        "expected_keywords": ["variable costs", "29.4", "23.2", "EUR/ton", "21%", "reduction"],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 46,
        "expected_section": "Portugal Cement - Operational Performance",
        "category": "cost_analysis",
        "difficulty": "hard",
    },
    {
        "id": 12,
        "question": "What is the relationship between alternative fuel rate percentage and thermal energy costs per ton?",
        "expected_answer": "Higher alternative fuel rate (50% in Aug-25 vs 42% in Aug-24) correlates with lower thermal energy costs (5.8 EUR/ton vs 8.3 EUR/ton), demonstrating 30% cost reduction through alternative fuel usage",
        "expected_keywords": [
            "alternative fuel",
            "50%",
            "42%",
            "termic energy",
            "5.8",
            "8.3",
            "reduction",
        ],
        "source_document": "2025-08 Performance Review CONSO_v2.pdf",
        "expected_page_number": 46,
        "expected_section": "Portugal Cement - Operational Performance",
        "category": "cost_analysis",
        "difficulty": "hard",
    },
]
