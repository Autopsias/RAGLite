"""
Ground Truth Test Set - VALIDATED AGAINST ACTUAL PDF CONTENT

This module provides 50 validated question-answer pairs for testing RAG system accuracy.
All questions have been manually validated against the actual PDF content on 2025-10-14.

Usage:
    Import GROUND_TRUTH_QA for accuracy testing and validation:
    >>> from tests.fixtures.ground_truth import GROUND_TRUTH_QA
    >>> questions = GROUND_TRUTH_QA[:15]  # Select subset for testing

Source Document: 2025-08 Performance Review CONSO_v2.pdf (160 pages)
Validation Method: Systematic PDF reading and keyword verification
Categories: 6 (Cost Analysis, Margins, Financial Performance, Safety, Workforce, Operating Expenses)
Difficulty Levels: 3 (easy, medium, hard)

Last Updated: 2025-01-06
Split from: tests/fixtures/ground_truth.py (original 802 LOC file)
"""

from typing import TypedDict, cast

from tests.fixtures.ground_truth.cost_analysis import COST_ANALYSIS_QUESTIONS
from tests.fixtures.ground_truth.financial_performance import FINANCIAL_PERFORMANCE_QUESTIONS
from tests.fixtures.ground_truth.margins import MARGINS_QUESTIONS
from tests.fixtures.ground_truth.operating_expenses import OPERATING_EXPENSES_QUESTIONS
from tests.fixtures.ground_truth.safety_metrics import SAFETY_METRICS_QUESTIONS
from tests.fixtures.ground_truth.workforce import WORKFORCE_QUESTIONS


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


# Combined ground truth QA set (50 questions total)
# Distribution:
# - Cost Analysis: 12 questions (5 easy, 5 medium, 2 hard)
# - Margins: 8 questions (3 easy, 4 medium, 1 hard)
# - Financial Performance: 10 questions (4 easy, 4 medium, 2 hard)
# - Safety Metrics: 6 questions (2 easy, 3 medium, 1 hard)
# - Workforce: 6 questions (2 easy, 3 medium, 1 hard)
# - Operating Expenses: 8 questions (3 easy, 4 medium, 1 hard)

GROUND_TRUTH_QA: list[GroundTruthQuestion] = cast(
    list[GroundTruthQuestion],
    COST_ANALYSIS_QUESTIONS
    + FINANCIAL_PERFORMANCE_QUESTIONS
    + MARGINS_QUESTIONS
    + OPERATING_EXPENSES_QUESTIONS
    + SAFETY_METRICS_QUESTIONS
    + WORKFORCE_QUESTIONS,
)
