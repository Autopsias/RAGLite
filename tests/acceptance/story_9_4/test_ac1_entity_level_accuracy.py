"""ATDD Tests for Story 9-4 AC1: Entity Level Classification with 90%+ Accuracy.

This module validates AC1 from the story:
- AC1.1: Returns correct EntityLevel for 90%+ of ground truth samples (50+ samples)
- AC1.2: Classifies consolidated patterns correctly (GROUP, Consolidated, Total)
- AC1.3: Classifies company patterns correctly (SECIL, SA, Ltd, company names)
- AC1.4: Classifies segment patterns correctly (Division, Segment, business unit names)
- AC1.5: Classifies geographic patterns correctly (country names, region names)
- AC1.6: Defaults to UNKNOWN for ambiguous entities (conservative approach)

Test IDs follow pattern: TEST-AC-{story}.{ac}.{test}
Example: TEST-AC-9.4.1.1 = Story 9.4, AC1, Test 1

TDD RED PHASE: These tests import from modules that DO NOT EXIST YET.
All tests MUST fail initially.
"""

import json
from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.atdd,
]


class TestAC1EntityLevelClassificationAccuracy:
    """AC1: Entity Level Classification with 90%+ Accuracy.

    Given a list of entity strings and optional table context from financial tables
    When classifying entity levels using classify_entity_level() or classify_entity_levels_batch()
    Then returns correct EntityLevel for 90%+ of ground truth samples
    """

    GROUND_TRUTH_PATH = Path("tests/fixtures/entity_level_ground_truth.json")
    ACCURACY_THRESHOLD = 0.90

    @pytest.fixture
    def ground_truth_data(self) -> list[dict]:
        """Load ground truth dataset for accuracy validation."""
        assert self.GROUND_TRUTH_PATH.exists(), (
            f"Ground truth file not found: {self.GROUND_TRUTH_PATH}"
        )
        with open(self.GROUND_TRUTH_PATH) as f:
            data = json.load(f)
        assert len(data) >= 50, f"Need 50+ samples, found {len(data)}"
        return data

    def test_ac_1_1_1_achieves_90_percent_accuracy(self, ground_truth_data: list[dict]) -> None:
        """TEST-AC-9.4.1.1 [P0]: 90%+ accuracy on ground truth dataset.

        Scenario: Ground truth validation passes at 90%+
          Given the ground truth dataset with 50+ samples
          When validating classification accuracy
          Then at least 45 samples are correctly classified (90%+)
        """
        # Import from module that doesn't exist yet - will cause ImportError
        from raglite.ingestion.classification import classify_entity_level

        correct = 0
        failures = []

        for sample in ground_truth_data:
            entity = sample["entity"]
            table_title = sample.get("table_title")
            expected_level = sample["expected_entity_level"]

            result = classify_entity_level(entity, table_title=table_title)

            if result.entity_level.value == expected_level:
                correct += 1
            else:
                failures.append(
                    {
                        "entity": entity,
                        "table_title": table_title,
                        "expected": expected_level,
                        "actual": result.entity_level.value,
                        "source": result.source,
                    }
                )

        accuracy = correct / len(ground_truth_data)

        # Log failures for debugging
        if failures:
            for f in failures:
                print(f"FAIL: {f}")

        assert accuracy >= self.ACCURACY_THRESHOLD, (
            f"Accuracy {accuracy:.2%} below threshold {self.ACCURACY_THRESHOLD:.0%}. "
            f"Failures: {len(failures)}/{len(ground_truth_data)}"
        )

    def test_ac_1_1_2_consolidated_group_pattern(self) -> None:
        """TEST-AC-9.4.1.2 [P1]: Classify "GROUP" as CONSOLIDATED.

        Scenario: Classify consolidated entity
          Given the entity string "GROUP"
          When classify_entity_level() is called
          Then entity_level is CONSOLIDATED
          And source is "entity_pattern"
        """
        from raglite.ingestion.classification import EntityLevel, classify_entity_level

        result = classify_entity_level("GROUP")

        assert result.entity_level == EntityLevel.CONSOLIDATED
        assert result.source == "entity_pattern"

    def test_ac_1_1_3_consolidated_total_group_pattern(self) -> None:
        """TEST-AC-9.4.1.3 [P1]: Classify "Total Group" as CONSOLIDATED.

        Scenario: Classify consolidated with "Total" keyword
          Given the entity string "Total Group"
          When classify_entity_level() is called
          Then entity_level is CONSOLIDATED
          And source is "entity_pattern"
        """
        from raglite.ingestion.classification import EntityLevel, classify_entity_level

        result = classify_entity_level("Total Group")

        assert result.entity_level == EntityLevel.CONSOLIDATED
        assert result.source == "entity_pattern"

    def test_ac_1_1_4_consolidated_keyword_variations(self) -> None:
        """TEST-AC-9.4.1.4 [P1]: Classify consolidated keyword variations.

        Given various consolidated patterns
        When classify_entity_level() is called
        Then all are classified as CONSOLIDATED
        """
        from raglite.ingestion.classification import EntityLevel, classify_entity_level

        consolidated_patterns = [
            "GROUP",
            "Consolidated",
            "Total Group",
            "Group Total",
            "CONSOLIDATED",
            "GROUP EBITDA",
        ]

        for entity in consolidated_patterns:
            result = classify_entity_level(entity)
            assert result.entity_level == EntityLevel.CONSOLIDATED, (
                f"'{entity}' expected CONSOLIDATED, got {result.entity_level.value}"
            )

    def test_ac_1_1_5_company_sa_suffix_pattern(self) -> None:
        """TEST-AC-9.4.1.5 [P1]: Classify company entity with SA suffix.

        Scenario: Classify company entity with SA suffix
          Given the entity string "SECIL SA"
          When classify_entity_level() is called
          Then entity_level is COMPANY_ONLY
          And source is "entity_pattern"
        """
        from raglite.ingestion.classification import EntityLevel, classify_entity_level

        result = classify_entity_level("SECIL SA")

        assert result.entity_level == EntityLevel.COMPANY_ONLY
        assert result.source == "entity_pattern"

    def test_ac_1_1_6_company_ltd_suffix_pattern(self) -> None:
        """TEST-AC-9.4.1.6 [P1]: Classify company entity with Ltd suffix.

        Given the entity string "Company Ltd"
        When classify_entity_level() is called
        Then entity_level is COMPANY_ONLY
        """
        from raglite.ingestion.classification import EntityLevel, classify_entity_level

        result = classify_entity_level("Company Ltd")

        assert result.entity_level == EntityLevel.COMPANY_ONLY

    def test_ac_1_1_7_company_patterns_variations(self) -> None:
        """TEST-AC-9.4.1.7 [P1]: Classify various company patterns.

        Given various company patterns (SA, Ltd, Lda, Inc, Corp)
        When classify_entity_level() is called
        Then all are classified as COMPANY_ONLY
        """
        from raglite.ingestion.classification import EntityLevel, classify_entity_level

        company_patterns = [
            "SECIL SA",
            "SECIL Portugal SA",
            "Company Ltd",
            "Empresa Lda",
            "Corporation Inc",
            "MyCompany Corp",
        ]

        for entity in company_patterns:
            result = classify_entity_level(entity)
            assert result.entity_level == EntityLevel.COMPANY_ONLY, (
                f"'{entity}' expected COMPANY_ONLY, got {result.entity_level.value}"
            )

    def test_ac_1_1_8_segment_division_pattern(self) -> None:
        """TEST-AC-9.4.1.8 [P1]: Classify segment entity.

        Scenario: Classify segment entity
          Given the entity string "Cement Division"
          When classify_entity_level() is called
          Then entity_level is SEGMENT
          And source is "entity_pattern"
        """
        from raglite.ingestion.classification import EntityLevel, classify_entity_level

        result = classify_entity_level("Cement Division")

        assert result.entity_level == EntityLevel.SEGMENT
        assert result.source == "entity_pattern"

    def test_ac_1_1_9_segment_patterns_variations(self) -> None:
        """TEST-AC-9.4.1.9 [P1]: Classify various segment patterns.

        Given various segment patterns (Division, Segment, Unit, Cement, Ready-Mix)
        When classify_entity_level() is called
        Then all are classified as SEGMENT
        """
        from raglite.ingestion.classification import EntityLevel, classify_entity_level

        segment_patterns = [
            "Cement Division",
            "Ready-Mix Segment",
            "Concrete Unit",
            "Aggregates Sector",
            "Cement Operations",
        ]

        for entity in segment_patterns:
            result = classify_entity_level(entity)
            assert result.entity_level == EntityLevel.SEGMENT, (
                f"'{entity}' expected SEGMENT, got {result.entity_level.value}"
            )

    def test_ac_1_1_10_geographic_country_pattern(self) -> None:
        """TEST-AC-9.4.1.10 [P1]: Classify geographic entity (country).

        Scenario: Classify geographic entity (country)
          Given the entity string "Portugal"
          When classify_entity_level() is called
          Then entity_level is GEOGRAPHIC
          And source is "entity_pattern"
        """
        from raglite.ingestion.classification import EntityLevel, classify_entity_level

        result = classify_entity_level("Portugal")

        assert result.entity_level == EntityLevel.GEOGRAPHIC
        assert result.source == "entity_pattern"

    def test_ac_1_1_11_case_insensitive_matching(self) -> None:
        """TEST-AC-9.4.1.11 [P1]: Case-insensitive pattern matching.

        Given entity strings in various cases
        When classify_entity_level() is called
        Then classification is case-insensitive
        """
        from raglite.ingestion.classification import EntityLevel, classify_entity_level

        test_cases = [
            ("group", EntityLevel.CONSOLIDATED),
            ("GROUP", EntityLevel.CONSOLIDATED),
            ("Group", EntityLevel.CONSOLIDATED),
            ("portugal", EntityLevel.GEOGRAPHIC),
            ("PORTUGAL", EntityLevel.GEOGRAPHIC),
            ("division", EntityLevel.SEGMENT),
        ]

        for entity, expected in test_cases:
            result = classify_entity_level(entity)
            assert result.entity_level == expected, (
                f"'{entity}' expected {expected.value}, got {result.entity_level.value}"
            )
