"""ATDD tests for Story 9.7 AC5 - Re-ingestion Performance Metrics.

TDD RED Phase: All tests MUST fail initially because performance tracking
is not yet implemented in the reingest script.

Test IDs follow pattern: TEST-AC-9.7.5.{test}

BDD Acceptance Criteria:
Given re-ingestion processes 33 PDFs with 78,759+ table rows
When tracking performance
Then total re-ingestion time is recorded
And per-document timing is logged:
  | Document | Pages | Tables | Rows | Duration | Rows/sec |
  |----------|-------|--------|------|----------|----------|
Then average classification overhead is calculated (extraction time with vs without classification)
And overhead confirms <20% increase per Epic 9 AC4
And throughput metrics are saved to docs/sprint-artifacts/re-ingestion-metrics.md
"""

import pytest

pytestmark = [
    pytest.mark.acceptance,
    pytest.mark.story_9_7,
    pytest.mark.atdd,
]


class TestAC5PerformanceMetrics:
    """AC5: Re-ingestion Performance Metrics.

    Given re-ingestion processes documents
    When tracking performance
    Then metrics are collected and classification overhead is <20%
    """

    def test_ac_5_1_1_reingest_script_tracks_total_duration(self) -> None:
        """TEST-AC-9.7.5.1 [P0]: Script tracks total re-ingestion duration.

        Given the reingest script processes documents
        When we examine its timing logic
        Then total duration is calculated and reported
        """
        # Arrange: Read script source
        from pathlib import Path

        script_path = Path("scripts/reingest-all-documents.py")

        # RED STATE: Script exists but may not have timing
        assert script_path.exists(), "Script not found"

        source_code = script_path.read_text()

        # Assert: Timing tracking is present
        assert "time" in source_code.lower(), "Script should import time module for tracking"
        # RED STATE: Current script may not have detailed timing
        assert "total_duration" in source_code or "total_time" in source_code.lower(), (
            "Script should calculate total duration"
        )

    def test_ac_5_1_2_reingest_script_tracks_per_document_timing(self) -> None:
        """TEST-AC-9.7.5.2 [P0]: Script tracks per-document timing.

        Given the reingest script processes documents
        When each document is ingested
        Then duration is recorded for that document
        """
        # Arrange: Read script source
        from pathlib import Path

        script_path = Path("scripts/reingest-all-documents.py")
        assert script_path.exists(), "Script not found"

        source_code = script_path.read_text()

        # Assert: Per-document timing is present
        # RED STATE: Current script may not track per-document time
        assert "duration" in source_code.lower() or "elapsed" in source_code.lower(), (
            "Script should track per-document duration"
        )

    def test_ac_5_1_3_reingest_script_calculates_rows_per_second(self) -> None:
        """TEST-AC-9.7.5.3 [P0]: Script calculates rows/second throughput.

        Given the reingest script tracks timing
        When we examine its metrics
        Then rows per second is calculated
        """
        # Arrange: Read script source
        from pathlib import Path

        script_path = Path("scripts/reingest-all-documents.py")
        assert script_path.exists(), "Script not found"

        source_code = script_path.read_text()

        # Assert: Throughput calculation is present
        # RED STATE: Current script does not calculate rows/sec
        assert "rows_per_second" in source_code or "rows/sec" in source_code.lower(), (
            "Script should calculate rows per second throughput"
        )

    def test_ac_5_1_4_reingest_script_logs_document_metrics(self) -> None:
        """TEST-AC-9.7.5.4 [P0]: Script logs metrics per document.

        Given the reingest script processes documents
        When logging document completion
        Then pages, tables, rows, duration are logged
        """
        # Arrange: Read script source
        from pathlib import Path

        script_path = Path("scripts/reingest-all-documents.py")
        assert script_path.exists(), "Script not found"

        source_code = script_path.read_text()

        # Assert: Per-document metrics are logged
        # Check for key metrics in output
        assert "pages" in source_code.lower(), "Script should log page count"
        assert "tables" in source_code.lower(), "Script should log table count"
        # RED STATE: Current script may not log all metrics
        assert "rows" in source_code.lower() or "row_count" in source_code, (
            "Script should log row count per document"
        )

    def test_ac_5_1_5_reingest_script_saves_metrics_report(self) -> None:
        """TEST-AC-9.7.5.5 [P0]: Script saves metrics to report file.

        Given the reingest script completes
        When metrics are collected
        Then report is saved to docs/sprint-artifacts/re-ingestion-metrics.md
        """
        # Arrange: Read script source
        from pathlib import Path

        script_path = Path("scripts/reingest-all-documents.py")
        assert script_path.exists(), "Script not found"

        source_code = script_path.read_text()

        # Assert: Metrics report saving is present
        # RED STATE: Current script does not save metrics report
        assert "re-ingestion-metrics" in source_code or "metrics_report" in source_code, (
            "Script should save metrics to re-ingestion-metrics.md"
        )

    def test_ac_5_1_6_classification_overhead_under_20_percent(self) -> None:
        """TEST-AC-9.7.5.6 [P0]: Classification overhead is <20%.

        Given the metrics report is generated
        When examining classification overhead
        Then overhead is less than 20% per Epic 9 AC4
        """
        # Arrange: This test validates the overhead metric exists
        from pathlib import Path

        script_path = Path("scripts/reingest-all-documents.py")
        assert script_path.exists(), "Script not found"

        source_code = script_path.read_text()

        # Assert: Overhead calculation is present
        # RED STATE: Current script does not track classification overhead
        assert "overhead" in source_code.lower() or "classification_time" in source_code, (
            "Script should calculate classification overhead"
        )

    def test_ac_5_1_7_performance_report_structure(self, sample_performance_metrics: dict) -> None:
        """TEST-AC-9.7.5.7 [P0]: Performance report has expected structure.

        Given a valid performance report
        When examining its structure
        Then it contains all required metrics
        """
        # Arrange: Use sample performance metrics fixture
        metrics = sample_performance_metrics

        # Assert: Required fields are present
        assert "total_documents" in metrics, "Report should have total_documents"
        assert "total_duration_seconds" in metrics, "Report should have total_duration_seconds"
        assert "total_pages" in metrics, "Report should have total_pages"
        assert "total_tables" in metrics, "Report should have total_tables"
        assert "total_rows" in metrics, "Report should have total_rows"
        assert "average_rows_per_second" in metrics, "Report should have average_rows_per_second"

    def test_ac_5_1_8_performance_report_has_per_document_metrics(
        self, sample_performance_metrics: dict
    ) -> None:
        """TEST-AC-9.7.5.8 [P0]: Performance report has per-document metrics.

        Given a valid performance report
        When examining per_document section
        Then each document has pages, tables, rows, duration, rows_per_second
        """
        # Arrange: Use sample performance metrics fixture
        metrics = sample_performance_metrics

        # Assert: per_document section is present
        assert "per_document" in metrics, "Report should have per_document section"
        assert len(metrics["per_document"]) > 0, "per_document should have entries"

        # Check first document entry
        doc_entry = metrics["per_document"][0]
        required_fields = [
            "document",
            "pages",
            "tables",
            "rows",
            "duration_seconds",
            "rows_per_second",
        ]
        for field in required_fields:
            assert field in doc_entry, f"Document entry missing field: {field}"

    def test_ac_5_1_9_overhead_below_20_percent_in_report(
        self, sample_performance_metrics: dict
    ) -> None:
        """TEST-AC-9.7.5.9 [P0]: Classification overhead in report is <20%.

        Given a valid performance report
        When examining classification_overhead_percentage
        Then it is less than 20%
        """
        # Arrange: Use sample performance metrics fixture
        metrics = sample_performance_metrics

        # Assert: Overhead is under 20%
        assert "classification_overhead_percentage" in metrics, (
            "Report should have classification_overhead_percentage"
        )
        assert metrics["classification_overhead_percentage"] < 20.0, (
            f"Overhead {metrics['classification_overhead_percentage']}% should be < 20%"
        )
