"""Ground truth test set for RAGLite Phase 1 accuracy validation.

This module contains 50+ representative financial Q&A pairs from the Secil Group
performance review document (2025-08 Performance Review CONSO_v2.pdf). Used for
daily/weekly accuracy tracking throughout Phase 1 development and final validation.

The test set expands the Week 0 baseline (15 queries) to enable robust accuracy
tracking and regression detection during Phase 1 implementation (Weeks 1-5).

Usage:
    from tests.fixtures.archive.ground_truth_old_backup import GROUND_TRUTH_QA

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

# Import all category question sets
from .cost_analysis import COST_ANALYSIS_QUESTIONS
from .financial_performance import FINANCIAL_PERFORMANCE_QUESTIONS
from .margins import MARGINS_QUESTIONS
from .operating_expenses import OPERATING_EXPENSES_QUESTIONS
from .safety_metrics import SAFETY_METRICS_QUESTIONS
from .workforce import WORKFORCE_QUESTIONS

__all__ = [
    "GROUND_TRUTH_QA",
    "COST_ANALYSIS_QUESTIONS",
    "MARGINS_QUESTIONS",
    "FINANCIAL_PERFORMANCE_QUESTIONS",
    "SAFETY_METRICS_QUESTIONS",
    "WORKFORCE_QUESTIONS",
    "OPERATING_EXPENSES_QUESTIONS",
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

_category_counts: dict[str, int] = {}
_difficulty_counts: dict[str, int] = {}
for qa in GROUND_TRUTH_QA:
    category: str = qa["category"]  # type: ignore[assignment]
    difficulty: str = qa["difficulty"]  # type: ignore[assignment]
    _category_counts[category] = _category_counts.get(category, 0) + 1
    _difficulty_counts[difficulty] = _difficulty_counts.get(difficulty, 0) + 1

for cat, expected in _EXPECTED_CATEGORIES.items():
    actual = _category_counts.get(cat, 0)
    assert actual == expected, f"Category {cat}: expected {expected}, got {actual}"

for diff, expected in _EXPECTED_DIFFICULTIES.items():
    actual = _difficulty_counts.get(diff, 0)
    assert actual == expected, f"Difficulty {diff}: expected {expected}, got {actual}"
