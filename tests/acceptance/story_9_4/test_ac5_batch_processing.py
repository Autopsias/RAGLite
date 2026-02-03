"""ATDD Tests for Story 9-4 AC5: Batch Processing Performance.

This module validates AC5 from the story:
- AC5.1: Returns list of ClassifiedEntityLevel matching input order
- AC5.2: Returns EntityLevelReport with accurate counts
- AC5.3: LRU cache provides <100ms for 1000 duplicate entities
- AC5.4: Handles None table_titles gracefully

Test IDs follow pattern: TEST-AC-{story}.{ac}.{test}
Example: TEST-AC-9.4.5.1 = Story 9.4, AC5, Test 1

TDD RED PHASE: These tests import from modules that DO NOT EXIST YET.
All tests MUST fail initially.
"""

import time

import pytest

pytestmark = [
    pytest.mark.atdd,
    pytest.mark.slow,
]


class TestAC5BatchProcessingPerformance:
    """AC5: Batch Processing Performance.

    Given a batch of entity strings to classify
    When using classify_entity_levels_batch()
    Then batch processing is efficient with caching
    """

    def test_ac_5_5_1_batch_returns_correct_order(self) -> None:
        """TEST-AC-9.4.5.1 [P0]: Returns list of ClassifiedEntityLevel matching input order.

        Scenario: Batch classification with report
          Given a list of 100 entities ["GROUP", "Portugal", "SECIL", ...]
          When classify_entity_levels_batch() is called
          Then results list has 100 ClassifiedEntityLevel entries
          And report.total_records equals 100
          And report.entity_level_breakdown sums to 100
        """
        from raglite.ingestion.classification import (
            EntityLevel,
            classify_entity_levels_batch,
        )

        entities = [
            "GROUP",
            "Portugal",
            "SECIL SA",
            "Cement Division",
            "N/A",
        ]

        results, report = classify_entity_levels_batch(entities)

        # Verify order is preserved
        assert len(results) == 5
        assert results[0].entity_level == EntityLevel.CONSOLIDATED
        assert results[1].entity_level == EntityLevel.GEOGRAPHIC
        assert results[2].entity_level == EntityLevel.COMPANY_ONLY
        assert results[3].entity_level == EntityLevel.SEGMENT
        assert results[4].entity_level == EntityLevel.UNKNOWN

        # Verify report counts
        assert report.total_records == 5
        breakdown_sum = sum(report.entity_level_breakdown.values())
        assert breakdown_sum == report.total_records

    def test_ac_5_5_2_report_has_accurate_counts(self) -> None:
        """TEST-AC-9.4.5.2 [P0]: Returns EntityLevelReport with accurate counts.

        Given a mixed list of entities
        When classify_entity_levels_batch() is called
        Then report has accurate counts per entity level
        """
        from raglite.ingestion.classification import classify_entity_levels_batch

        entities = [
            # 3 consolidated
            "GROUP",
            "Consolidated",
            "Total Group",
            # 2 company_only
            "SECIL SA",
            "Company Ltd",
            # 2 segment
            "Cement Division",
            "Ready-Mix Segment",
            # 2 geographic
            "Portugal",
            "Tunisia",
            # 1 unknown
            "N/A",
        ]

        results, report = classify_entity_levels_batch(entities)

        assert report.total_records == 10
        assert report.consolidated_count == 3
        assert report.company_only_count == 2
        assert report.segment_count == 2
        assert report.geographic_count == 2
        assert report.unknown_count == 1

        # Verify breakdown sums to total
        breakdown_sum = sum(report.entity_level_breakdown.values())
        assert breakdown_sum == report.total_records

    def test_ac_5_5_3_cache_performance_under_100ms(self) -> None:
        """TEST-AC-9.4.5.3 [P2]: LRU cache provides <100ms for 1000 duplicate entities.

        Scenario: Cached batch performance
          Given a list of 1000 identical entities ["GROUP", "GROUP", ...]
          When classify_entity_levels_batch() is called
          Then classification completes in <100ms
        """
        from raglite.ingestion.classification import classify_entity_levels_batch

        # 1000 identical entities to test cache hit performance
        entities = ["GROUP"] * 1000

        start = time.time()
        results, report = classify_entity_levels_batch(entities)
        elapsed = time.time() - start

        assert len(results) == 1000
        assert elapsed < 0.1, f"Batch took {elapsed * 1000:.1f}ms, expected <100ms"

    def test_ac_5_5_4_handles_none_table_titles(self) -> None:
        """TEST-AC-9.4.5.4 [P1]: Handles None table_titles gracefully.

        Scenario: Batch classification with None table_titles
          Given a list of entities ["GROUP", "Portugal"]
          And table_titles is None
          When classify_entity_levels_batch() is called
          Then classification succeeds without errors
          And results contain valid ClassifiedEntityLevel entries
        """
        from raglite.ingestion.classification import classify_entity_levels_batch

        entities = ["GROUP", "Portugal"]

        # Test with explicit None
        results, report = classify_entity_levels_batch(entities, table_titles=None)

        assert len(results) == 2
        assert report.total_records == 2

        # Verify each result is valid
        for result in results:
            assert hasattr(result, "entity_level")
            assert hasattr(result, "source")
            assert hasattr(result, "original")

    def test_ac_5_5_5_batch_with_table_titles_list(self) -> None:
        """TEST-AC-9.4.5.5 [P1]: Batch supports table_titles list for classification.

        Given entities and matching table_titles lists
        When classify_entity_levels_batch() is called
        Then table_titles influence classification
        """
        from raglite.ingestion.classification import (
            EntityLevel,
            classify_entity_levels_batch,
        )

        entities = ["Revenue", "Revenue", "Revenue"]
        table_titles = [
            "GROUP Financial Statements",
            "Portugal Operations",
            "Cement Division Results",
        ]

        results, report = classify_entity_levels_batch(entities, table_titles=table_titles)

        # Generic "Revenue" should be classified by table_title context
        assert results[0].entity_level == EntityLevel.CONSOLIDATED
        assert results[1].entity_level == EntityLevel.GEOGRAPHIC
        assert results[2].entity_level == EntityLevel.SEGMENT

    def test_ac_5_5_6_batch_validates_list_lengths(self) -> None:
        """TEST-AC-9.4.5.6 [P1]: Batch validates mismatched list lengths.

        Given entities and table_titles lists of different lengths
        When classify_entity_levels_batch() is called
        Then it raises ValueError
        """
        from raglite.ingestion.classification import classify_entity_levels_batch

        entities = ["GROUP", "Portugal", "SECIL"]
        table_titles = ["Title1", "Title2"]  # Mismatched length

        with pytest.raises(ValueError, match="same length"):
            classify_entity_levels_batch(entities, table_titles=table_titles)

    def test_ac_5_5_7_batch_preserves_original_values(self) -> None:
        """TEST-AC-9.4.5.7 [P1]: Batch results preserve original entity values.

        Given a list of entities
        When classify_entity_levels_batch() is called
        Then each result contains the original entity string
        """
        from raglite.ingestion.classification import classify_entity_levels_batch

        entities = ["GROUP", "Portugal", "SECIL SA", "N/A"]

        results, report = classify_entity_levels_batch(entities)

        for i, result in enumerate(results):
            assert result.original == entities[i], (
                f"Original mismatch at index {i}: expected '{entities[i]}', got '{result.original}'"
            )

    def test_ac_5_5_8_large_batch_performance(self) -> None:
        """TEST-AC-9.4.5.8 [P2]: Large batch (1000 varied entities) completes efficiently.

        Given a list of 1000 varied entities
        When classify_entity_levels_batch() is called
        Then classification completes in <500ms
        """
        from raglite.ingestion.classification import classify_entity_levels_batch

        # Generate varied entities
        base_entities = [
            "GROUP",
            "Portugal",
            "SECIL SA",
            "Cement Division",
            "N/A",
            "Tunisia",
            "Company Ltd",
            "Consolidated",
            "Europe",
            "Ready-Mix Segment",
        ]
        entities = base_entities * 100  # 1000 entities

        start = time.time()
        results, report = classify_entity_levels_batch(entities)
        elapsed = time.time() - start

        assert len(results) == 1000
        assert report.total_records == 1000
        assert elapsed < 0.5, f"Large batch took {elapsed * 1000:.1f}ms, expected <500ms"
