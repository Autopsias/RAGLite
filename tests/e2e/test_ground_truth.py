"""Tests for ground truth test set structure and validation.

This module tests the ground truth data structure to ensure it meets
all acceptance criteria for Story 1.12A without requiring PDF access
or running actual queries.

Test Coverage:
    - AC1: 50+ questions present
    - AC2: All 6 categories represented
    - AC3: 40/40/20 difficulty distribution
    - AC4: Data stored in correct format
    - AC5: All required fields present
    - AC7: Module is importable and documented
"""

from tests.fixtures.ground_truth import GROUND_TRUTH_QA, GroundTruthQuestion


class TestGroundTruthStructure:
    """Test ground truth data structure and basic validation."""

    def test_minimum_question_count(self) -> None:
        """Verify GROUND_TRUTH_QA contains at least 50 questions (AC1)."""
        assert len(GROUND_TRUTH_QA) >= 50, f"Expected ≥50 questions, got {len(GROUND_TRUTH_QA)}"

    def test_unique_question_ids(self) -> None:
        """Verify all question IDs are unique (AC1)."""
        ids = [qa["id"] for qa in GROUND_TRUTH_QA]
        assert len(ids) == len(set(ids)), "Question IDs must be unique"

    def test_ids_are_sequential(self) -> None:
        """Verify question IDs are sequential starting from 1."""
        ids: list[int] = sorted([qa["id"] for qa in GROUND_TRUTH_QA])
        expected_ids = list(range(1, len(GROUND_TRUTH_QA) + 1))
        assert ids == expected_ids, "Question IDs should be sequential 1, 2, 3, ..."

    def test_all_required_fields_present(self) -> None:
        """Verify all required fields present in each question (AC5)."""
        required_fields = [
            "id",
            "question",
            "expected_answer",
            "expected_keywords",
            "source_document",
            "expected_page_number",
            "expected_section",
            "category",
            "difficulty",
        ]

        for qa in GROUND_TRUTH_QA:
            missing_fields = [field for field in required_fields if field not in qa]
            assert not missing_fields, f"Question {qa.get('id')} missing fields: {missing_fields}"

    def test_question_text_non_empty(self) -> None:
        """Verify all questions have non-empty text."""
        for qa in GROUND_TRUTH_QA:
            question: str = qa["question"]
            assert question.strip(), f"Question {qa['id']} has empty question text"

    def test_expected_answer_non_empty(self) -> None:
        """Verify all questions have non-empty expected answers (AC5)."""
        for qa in GROUND_TRUTH_QA:
            answer: str = qa["expected_answer"]
            assert answer.strip(), f"Question {qa['id']} has empty expected_answer"

    def test_expected_keywords_non_empty(self) -> None:
        """Verify all questions have non-empty keyword lists (AC5)."""
        for qa in GROUND_TRUTH_QA:
            assert isinstance(qa["expected_keywords"], list), (
                f"Question {qa['id']} expected_keywords must be a list"
            )
            assert len(qa["expected_keywords"]) > 0, (
                f"Question {qa['id']} has empty expected_keywords"
            )
            assert all(kw.strip() for kw in qa["expected_keywords"]), (
                f"Question {qa['id']} has empty keyword strings"
            )

    def test_page_numbers_valid(self) -> None:
        """Verify expected_page_number is valid integer for all questions (AC5)."""
        for qa in GROUND_TRUTH_QA:
            page: int = qa["expected_page_number"]
            assert isinstance(page, int), f"Question {qa['id']} page number must be integer"
            assert page > 0, f"Question {qa['id']} page number must be positive"

    def test_expected_section_non_empty(self) -> None:
        """Verify all questions have non-empty section identifiers (AC5)."""
        for qa in GROUND_TRUTH_QA:
            section: str = qa["expected_section"]
            assert section.strip(), f"Question {qa['id']} has empty expected_section"

    def test_source_document_consistent(self) -> None:
        """Verify all questions reference the same source document (AC5)."""
        expected_doc = "2025-08 Performance Review CONSO_v2.pdf"
        for qa in GROUND_TRUTH_QA:
            assert qa["source_document"] == expected_doc, (
                f"Question {qa['id']} has wrong source_document"
            )


class TestCategoryDistribution:
    """Test category representation and distribution (AC2)."""

    EXPECTED_CATEGORIES = {
        "cost_analysis": 12,
        "margins": 8,
        "financial_performance": 10,
        "safety_metrics": 6,
        "workforce": 6,
        "operating_expenses": 8,
    }

    def test_all_categories_present(self) -> None:
        """Verify all 6 categories are represented in data set (AC2)."""
        actual_categories: set[str] = {qa["category"] for qa in GROUND_TRUTH_QA}
        expected_categories: set[str] = set(self.EXPECTED_CATEGORIES.keys())
        assert actual_categories == expected_categories, (
            f"Missing categories: {expected_categories - actual_categories}"
        )

    def test_no_invalid_categories(self) -> None:
        """Verify no invalid category values present."""
        valid_categories: set[str] = set(self.EXPECTED_CATEGORIES.keys())
        for qa in GROUND_TRUTH_QA:
            assert qa["category"] in valid_categories, (
                f"Question {qa['id']} has invalid category: {qa['category']}"
            )

    def test_category_distribution(self) -> None:
        """Verify category distribution matches target percentages (AC2)."""
        category_counts: dict[str, int] = {}
        for qa in GROUND_TRUTH_QA:
            cat: str = qa["category"]
            category_counts[cat] = category_counts.get(cat, 0) + 1

        for cat, expected_count in self.EXPECTED_CATEGORIES.items():
            actual_count = category_counts.get(cat, 0)
            assert actual_count == expected_count, (
                f"Category {cat}: expected {expected_count}, got {actual_count}"
            )

    def test_category_distribution_tolerance(self) -> None:
        """Verify category distribution is within ±1 question tolerance."""
        category_counts: dict[str, int] = {}
        for qa in GROUND_TRUTH_QA:
            cat: str = qa["category"]
            category_counts[cat] = category_counts.get(cat, 0) + 1

        for cat, expected_count in self.EXPECTED_CATEGORIES.items():
            actual_count = category_counts.get(cat, 0)
            tolerance = 1
            assert abs(actual_count - expected_count) <= tolerance, (
                f"Category {cat} outside tolerance: expected {expected_count}±{tolerance}, "
                f"got {actual_count}"
            )


class TestDifficultyDistribution:
    """Test difficulty distribution (AC3)."""

    EXPECTED_DIFFICULTIES = {
        "easy": 20,  # 40%
        "medium": 20,  # 40%
        "hard": 10,  # 20%
    }

    def test_all_difficulties_present(self) -> None:
        """Verify all 3 difficulty levels are present."""
        actual_difficulties: set[str] = {qa["difficulty"] for qa in GROUND_TRUTH_QA}
        expected_difficulties: set[str] = set(self.EXPECTED_DIFFICULTIES.keys())
        assert actual_difficulties == expected_difficulties, (
            f"Missing difficulties: {expected_difficulties - actual_difficulties}"
        )

    def test_no_invalid_difficulties(self) -> None:
        """Verify no invalid difficulty values present."""
        valid_difficulties: set[str] = set(self.EXPECTED_DIFFICULTIES.keys())
        for qa in GROUND_TRUTH_QA:
            assert qa["difficulty"] in valid_difficulties, (
                f"Question {qa['id']} has invalid difficulty: {qa['difficulty']}"
            )

    def test_difficulty_distribution_exact(self) -> None:
        """Verify difficulty distribution is exactly 40/40/20 (AC3)."""
        difficulty_counts: dict[str, int] = {}
        for qa in GROUND_TRUTH_QA:
            diff: str = qa["difficulty"]
            difficulty_counts[diff] = difficulty_counts.get(diff, 0) + 1

        for diff, expected_count in self.EXPECTED_DIFFICULTIES.items():
            actual_count = difficulty_counts.get(diff, 0)
            assert actual_count == expected_count, (
                f"Difficulty {diff}: expected {expected_count}, got {actual_count}"
            )

    def test_difficulty_percentages(self) -> None:
        """Verify difficulty percentages match 40/40/20 target (AC3)."""
        difficulty_counts: dict[str, int] = {}
        for qa in GROUND_TRUTH_QA:
            diff: str = qa["difficulty"]
            difficulty_counts[diff] = difficulty_counts.get(diff, 0) + 1

        total = len(GROUND_TRUTH_QA)
        expected_percentages = {"easy": 40, "medium": 40, "hard": 20}

        for diff, expected_pct in expected_percentages.items():
            actual_count = difficulty_counts.get(diff, 0)
            actual_pct = (actual_count / total) * 100
            # Allow ±5% tolerance
            assert abs(actual_pct - expected_pct) <= 5, (
                f"Difficulty {diff}: expected {expected_pct}%, got {actual_pct:.1f}%"
            )


class TestImportAndAccessibility:
    """Test module import and data accessibility (AC4, AC7)."""

    def test_import_ground_truth_qa(self) -> None:
        """Import test: Verify GROUND_TRUTH_QA can be imported (AC4)."""
        from tests.fixtures.ground_truth import GROUND_TRUTH_QA as imported_qa

        assert imported_qa is not None
        assert isinstance(imported_qa, list)
        assert len(imported_qa) >= 50

    def test_ground_truth_is_list_of_dicts(self) -> None:
        """Verify ground truth is a list of dictionaries (AC4)."""
        assert isinstance(GROUND_TRUTH_QA, list), "GROUND_TRUTH_QA must be a list"
        for qa in GROUND_TRUTH_QA:
            assert isinstance(qa, dict), f"Question {qa.get('id')} must be a dict"

    def test_module_has_docstring(self) -> None:
        """Verify module docstring explains usage and maintenance (AC7)."""
        import tests.fixtures.ground_truth as gt_module

        assert gt_module.__doc__ is not None, "Module must have docstring"
        assert len(gt_module.__doc__) > 100, "Module docstring should be comprehensive"

        # Check for key documentation elements
        doc = gt_module.__doc__.lower()
        assert "usage" in doc, "Docstring should explain usage"
        assert "adding" in doc or "add" in doc, "Docstring should explain how to add questions"
        assert "structure" in doc or "field" in doc, "Docstring should explain structure"


class TestDataQuality:
    """Test data quality and consistency."""

    def test_no_duplicate_questions(self) -> None:
        """Verify no duplicate question text."""
        questions: list[str] = [qa["question"].lower().strip() for qa in GROUND_TRUTH_QA]
        assert len(questions) == len(set(questions)), "Duplicate questions found"

    def test_expected_keywords_are_relevant(self) -> None:
        """Verify expected_keywords appear in question or expected_answer."""
        for qa in GROUND_TRUTH_QA:
            question_text: str = qa["question"].lower()
            answer_text: str = qa["expected_answer"].lower()
            combined_text: str = question_text + " " + answer_text

            # At least some keywords should appear in the question or answer context
            keywords: list[str] = qa["expected_keywords"]
            relevant_count = sum(1 for kw in keywords if kw.lower() in combined_text)

            # Allow flexibility - at least 30% of keywords should be contextually relevant
            threshold = max(1, len(keywords) * 0.3)
            assert relevant_count >= threshold, (
                f"Question {qa['id']}: Expected keywords not sufficiently relevant to question/answer"
            )

    def test_page_numbers_within_reasonable_range(self) -> None:
        """Verify page numbers are within reasonable range for a 160-page document."""
        max_expected_page = 160  # Based on test document specs
        for qa in GROUND_TRUTH_QA:
            page: int = qa["expected_page_number"]
            assert 1 <= page <= max_expected_page, (
                f"Question {qa['id']} has page number {page} outside valid range 1-{max_expected_page}"
            )

    def test_questions_are_actually_questions(self) -> None:
        """Verify most question texts are formatted as questions (end with ?)."""
        question_count = sum(
            1 for qa in GROUND_TRUTH_QA if str(qa["question"]).strip().endswith("?")
        )
        percentage = (question_count / len(GROUND_TRUTH_QA)) * 100

        # Allow some flexibility - at least 80% should be formatted as questions
        assert percentage >= 80, (
            f"Only {percentage:.1f}% of entries are formatted as questions (expected ≥80%)"
        )


class TestSubsetSelection:
    """Test subset selection for daily tracking (AC7)."""

    def test_random_subset_selection(self) -> None:
        """Verify random subset selection works for daily tracking."""
        import random

        subset_size = 15
        subset: list[GroundTruthQuestion] = random.sample(GROUND_TRUTH_QA, subset_size)

        assert len(subset) == subset_size
        assert all(q in GROUND_TRUTH_QA for q in subset)

    def test_category_balanced_subset(self) -> None:
        """Verify subset can be selected with balanced categories."""
        # Select 2-3 questions from each category for balanced daily tracking
        subset: list[GroundTruthQuestion] = []
        categories = [
            "cost_analysis",
            "margins",
            "financial_performance",
            "safety_metrics",
            "workforce",
            "operating_expenses",
        ]

        for cat in categories:
            cat_questions: list[GroundTruthQuestion] = [
                qa for qa in GROUND_TRUTH_QA if qa["category"] == cat
            ]
            subset.extend(cat_questions[:2])  # Take first 2 from each

        assert len(subset) == 12  # 6 categories × 2 questions
        assert len({q["category"] for q in subset}) == 6  # All categories represented

    def test_difficulty_balanced_subset(self) -> None:
        """Verify subset can be selected with balanced difficulty."""
        # Select subset with 40/40/20 difficulty distribution
        easy: list[GroundTruthQuestion] = [
            qa for qa in GROUND_TRUTH_QA if qa["difficulty"] == "easy"
        ][:6]
        medium: list[GroundTruthQuestion] = [
            qa for qa in GROUND_TRUTH_QA if qa["difficulty"] == "medium"
        ][:6]
        hard: list[GroundTruthQuestion] = [
            qa for qa in GROUND_TRUTH_QA if qa["difficulty"] == "hard"
        ][:3]

        subset: list[GroundTruthQuestion] = easy + medium + hard
        assert len(subset) == 15  # 6+6+3

        diff_counts: dict[str, int] = {}
        for qa in subset:
            difficulty: str = qa["difficulty"]
            diff_counts[difficulty] = diff_counts.get(difficulty, 0) + 1

        assert diff_counts["easy"] == 6
        assert diff_counts["medium"] == 6
        assert diff_counts["hard"] == 3
