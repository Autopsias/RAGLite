"""Type definitions for ground truth questions."""

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
