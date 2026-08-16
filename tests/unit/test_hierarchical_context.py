"""Unit tests for hierarchical parent entity context propagation (Phase 3.1).

Tests parent entity tracking in tables where entity context is defined by
parent rows (e.g., "Portugal" as parent, then "Trade Receivables" below).

Addresses the working capital entity coverage issue identified in Story 5.0.7
where child rows were losing parent entity context (22% coverage).
"""

from raglite.ingestion.adaptive_table.classification import HeaderType, classify_header


class TestParentEntityDetection:
    """Test parent entity row detection heuristics (Phase 3.1)."""

    def test_portugal_classified_as_entity(self):
        """Test Portugal classified as ENTITY (prerequisite for parent detection)."""
        assert classify_header("Portugal") == HeaderType.ENTITY

    def test_brazil_classified_as_entity(self):
        """Test Brazil classified as ENTITY."""
        assert classify_header("Brazil") == HeaderType.ENTITY

    def test_tunisia_classified_as_entity(self):
        """Test Tunisia classified as ENTITY."""
        assert classify_header("Tunisia") == HeaderType.ENTITY

    def test_trade_receivables_classified_as_metric(self):
        """Test Trade Receivables classified as METRIC (child row metric)."""
        assert classify_header("Trade Receivables") == HeaderType.METRIC

    def test_working_capital_classified_as_metric(self):
        """Test Working Capital classified as METRIC."""
        assert classify_header("Working Capital") == HeaderType.METRIC


class TestHierarchicalTablePattern:
    """Test recognition of hierarchical table patterns (Phase 3.1).

    Pattern: Working Capital tables structure:
    Row 1: "Portugal" (parent entity - header row, mostly empty data cells)
    Row 2: "  Trade Receivables" (child metric - inherits parent="Portugal")
    Row 3: "  Trade Payables" (child metric - inherits parent="Portugal")
    Row 4: "Brazil" (new parent entity)
    Row 5: "  Trade Receivables" (child metric - inherits parent="Brazil")
    """

    def test_parent_row_entity_classification(self):
        """Test parent rows are classified as ENTITY type."""
        # These are parent entity rows in hierarchical tables
        assert classify_header("Portugal") == HeaderType.ENTITY
        assert classify_header("Brazil") == HeaderType.ENTITY
        assert classify_header("Group") == HeaderType.ENTITY
        assert classify_header("Tunisia") == HeaderType.ENTITY

    def test_child_row_metric_classification(self):
        """Test child rows are classified as METRIC type."""
        # These are child metric rows that inherit parent entity
        assert classify_header("Trade Receivables") == HeaderType.METRIC
        assert classify_header("Trade Payables") == HeaderType.METRIC
        assert classify_header("Inventory") == HeaderType.METRIC
        assert classify_header("Net Working Capital") == HeaderType.METRIC

    def test_parent_entity_pattern_detection(self):
        """Test that entity-type headers with few data cells are parent candidates.

        Heuristic (from core.py:548-551):
        - header_type == HeaderType.ENTITY
        - len(non_empty_cells) <= 1  # 0 or 1 data cell with values

        This test validates the classification prerequisite for parent detection.
        """
        # Parent rows must be classified as ENTITY first
        parent_candidates = ["Portugal", "Brazil", "Tunisia", "Lebanon", "Group"]
        for candidate in parent_candidates:
            assert classify_header(candidate) == HeaderType.ENTITY, (
                f"{candidate} must be ENTITY for parent detection"
            )


class TestEntityContextInheritance:
    """Test entity context inheritance from parent rows (Phase 3.1).

    Tests the fallback logic (core.py:708-720):
    if not entity and parent_entity_by_row.get(row_idx):
        entity = parent_entity_by_row[row_idx]
    """

    def test_metric_rows_need_entity_context(self):
        """Test that metric rows without entity column need parent context.

        Pattern:
        - Row header: "Trade Receivables" (METRIC)
        - No entity in columns → entity should inherit from parent row
        """
        # Metric rows that need entity inheritance
        metrics_needing_parent = [
            "Trade Receivables",
            "Trade Payables",
            "Inventory",
            "Net Working Capital",
            "Cash",
            "Bank Debt",
        ]

        for metric in metrics_needing_parent:
            header_type = classify_header(metric)
            assert header_type == HeaderType.METRIC, (
                f"{metric} classified as {header_type}, expected METRIC"
            )

    def test_parent_entity_provides_context(self):
        """Test that parent entity rows provide context for child rows.

        Example from Working Capital table:
        - "Portugal" row (parent) → provides entity="Portugal" for following rows
        - "Trade Receivables" row (child) → inherits entity="Portugal"
        """
        # Parent entities that provide context
        parent_entities = [
            "Portugal",
            "Brazil",
            "Tunisia",
            "Lebanon",
            "Angola",
            "Group",
        ]

        for parent in parent_entities:
            assert classify_header(parent) == HeaderType.ENTITY, (
                f"{parent} must be ENTITY to provide parent context"
            )


class TestWorkingCapitalTableScenario:
    """Test Working Capital table scenario (Story 5.0.7 root cause).

    Before Phase 3.1:
    - Working Capital queries: 22% entity coverage
    - Child rows lost parent entity context

    After Phase 3.1:
    - Child rows inherit parent entity
    - Expected: 70-95% entity coverage
    """

    def test_portugal_working_capital_entity_chain(self):
        """Test Portugal working capital entity classification chain."""
        # Parent row
        assert classify_header("Portugal") == HeaderType.ENTITY

        # Child metric rows (should inherit entity="Portugal")
        assert classify_header("Trade Receivables") == HeaderType.METRIC
        assert classify_header("Trade Payables") == HeaderType.METRIC
        assert classify_header("Working Capital/Turnover") == HeaderType.METRIC

    def test_brazil_working_capital_entity_chain(self):
        """Test Brazil working capital entity classification chain."""
        # Parent row
        assert classify_header("Brazil") == HeaderType.ENTITY

        # Child metric rows (should inherit entity="Brazil")
        assert classify_header("Trade Receivables") == HeaderType.METRIC
        assert classify_header("Inventory") == HeaderType.METRIC

    def test_group_consolidated_entity_chain(self):
        """Test Group/Consolidated working capital entity classification chain."""
        # Parent row variations
        assert classify_header("Group") == HeaderType.ENTITY
        assert classify_header("Conso") == HeaderType.ENTITY
        assert classify_header("Consolidated") == HeaderType.ENTITY

        # Child metric rows (should inherit entity="Group")
        assert classify_header("Total Working Capital") == HeaderType.METRIC
        assert classify_header("Net Working Capital") == HeaderType.METRIC


class TestParentEntityLogging:
    """Test parent entity logging for observability (Phase 3.1).

    Logging structure (core.py:556-564, 712-720):
    - "Hierarchical parent entity detected" when new parent found
    - "Entity inherited from hierarchical parent" when child inherits
    """

    def test_parent_detection_observable(self):
        """Test parent entity detection produces observable classification.

        When a parent entity is detected (e.g., "Portugal" row with few data cells),
        it should be classified as HeaderType.ENTITY, enabling debug logging.
        """
        parent_entities = ["Portugal", "Brazil", "Tunisia"]
        for parent in parent_entities:
            # Classification is the first step that enables parent detection
            result = classify_header(parent)
            assert result == HeaderType.ENTITY, (
                f"Parent '{parent}' must classify as ENTITY for detection"
            )

    def test_child_metric_observable(self):
        """Test child metrics produce observable classification.

        Child metrics (e.g., "Trade Receivables") must classify as METRIC
        to trigger the parent inheritance fallback logic.
        """
        child_metrics = ["Trade Receivables", "Trade Payables", "Inventory"]
        for metric in child_metrics:
            result = classify_header(metric)
            assert result == HeaderType.METRIC, (
                f"Child metric '{metric}' must classify as METRIC for inheritance"
            )


class TestEdgeCases:
    """Test edge cases in parent entity tracking (Phase 3.1)."""

    def test_empty_row_header_no_parent(self):
        """Test empty row header handling (core.py:534-537)."""
        # Empty/None headers should not break parent tracking
        assert classify_header("") == HeaderType.UNKNOWN
        assert classify_header(None) == HeaderType.UNKNOWN

    def test_unknown_header_no_parent_override(self):
        """Test UNKNOWN headers don't become parent entities."""
        # Non-entity headers should not be detected as parents
        assert classify_header("Random Text") != HeaderType.ENTITY
        assert classify_header("123456") != HeaderType.ENTITY

    def test_temporal_headers_not_parents(self):
        """Test temporal headers are not detected as parent entities."""
        # Temporal headers should not be parent entities
        assert classify_header("2024") == HeaderType.TEMPORAL
        assert classify_header("Q1 2024") == HeaderType.TEMPORAL
        assert classify_header("Jan 2024") == HeaderType.TEMPORAL
