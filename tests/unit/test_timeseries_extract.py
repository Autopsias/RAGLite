"""Unit tests for time-series data extraction (Story 4.1).

Tests cover:
- AC1: Time-series extraction identifies temporal financial metrics
- AC2: Data points extracted with timestamps and metric labels
- AC3: Data normalized to consistent time intervals
- AC4: Handles various date formats and fiscal period labels
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from raglite.forecasting.timeseries_extract import (
    ExtractionError,
    MetricValidationError,
    extract_timeseries,
    extract_timeseries_from_sql,
    normalize_to_interval,
    parse_fiscal_date,
    parse_period_to_date,
)
from raglite.shared.models import TimeSeriesData, TimeSeriesPoint


class TestParseFiscalDate:
    """Tests for parse_fiscal_date function (AC4)."""

    def test_fiscal_quarter_fy24_q3(self) -> None:
        """AC4: Parse 'Q3 FY24' -> January 2024 (fiscal Q3 = Jan-Mar)."""
        result = parse_fiscal_date("Q3 FY24")
        assert result == datetime(2024, 1, 1)

    def test_fiscal_quarter_fy24_q1(self) -> None:
        """AC4: Parse 'Q1 FY24' -> July 2023 (fiscal Q1 = Jul-Sep of previous year)."""
        result = parse_fiscal_date("Q1 FY24")
        assert result == datetime(2023, 7, 1)

    def test_fiscal_quarter_fy24_q2(self) -> None:
        """AC4: Parse 'Q2 FY24' -> October 2023 (fiscal Q2 = Oct-Dec of previous year)."""
        result = parse_fiscal_date("Q2 FY24")
        assert result == datetime(2023, 10, 1)

    def test_fiscal_quarter_fy24_q4(self) -> None:
        """AC4: Parse 'Q4 FY24' -> April 2024 (fiscal Q4 = Apr-Jun)."""
        result = parse_fiscal_date("Q4 FY24")
        assert result == datetime(2024, 4, 1)

    def test_fiscal_quarter_fy2024_format(self) -> None:
        """AC4: Parse 'FY2024 Q3' (reversed format)."""
        result = parse_fiscal_date("FY2024 Q3")
        assert result == datetime(2024, 1, 1)

    def test_fiscal_year_only(self) -> None:
        """AC4: Parse 'FY24' -> July 2023 (start of fiscal year)."""
        result = parse_fiscal_date("FY24")
        assert result == datetime(2023, 7, 1)

    def test_calendar_quarter_q3_2024(self) -> None:
        """AC4: Parse 'Q3 2024' (calendar quarter) -> July 2024."""
        result = parse_fiscal_date("Q3 2024")
        assert result == datetime(2024, 7, 1)

    def test_calendar_quarter_q1_2024(self) -> None:
        """AC4: Parse 'Q1 2024' (calendar quarter) -> January 2024."""
        result = parse_fiscal_date("Q1 2024")
        assert result == datetime(2024, 1, 1)

    def test_month_year_format_jan_2024(self) -> None:
        """AC4: Parse 'Jan 2024' -> January 2024."""
        result = parse_fiscal_date("Jan 2024")
        assert result.year == 2024
        assert result.month == 1

    def test_month_year_format_january_2024(self) -> None:
        """AC4: Parse 'January 2024' -> January 2024."""
        result = parse_fiscal_date("January 2024")
        assert result.year == 2024
        assert result.month == 1

    def test_iso_format_2024_01(self) -> None:
        """AC4: Parse '2024-01' -> January 2024."""
        result = parse_fiscal_date("2024-01")
        assert result.year == 2024
        assert result.month == 1

    def test_slash_format_1_2024(self) -> None:
        """AC4: Parse '1/2024' -> January 2024."""
        result = parse_fiscal_date("1/2024")
        assert result.year == 2024
        assert result.month == 1

    def test_full_iso_date(self) -> None:
        """AC4: Parse '2024-01-15' -> January 15, 2024."""
        result = parse_fiscal_date("2024-01-15")
        assert result == datetime(2024, 1, 15)

    def test_case_insensitive(self) -> None:
        """AC4: Parse handles case-insensitive input."""
        result = parse_fiscal_date("q3 fy24")
        assert result == datetime(2024, 1, 1)

    def test_whitespace_handling(self) -> None:
        """AC4: Parse handles leading/trailing whitespace."""
        result = parse_fiscal_date("  Q3 FY24  ")
        assert result == datetime(2024, 1, 1)

    def test_invalid_date_raises_error(self) -> None:
        """AC4: Invalid date string raises ValueError."""
        with pytest.raises(ValueError, match="Cannot parse date"):
            parse_fiscal_date("not a date")


class TestNormalizeToInterval:
    """Tests for normalize_to_interval function (AC3)."""

    def test_normalize_to_monthly(self) -> None:
        """AC3: Normalize daily points to monthly interval."""
        points = [
            TimeSeriesPoint(date=datetime(2024, 1, 1), value=100.0),
            TimeSeriesPoint(date=datetime(2024, 1, 15), value=110.0),
            TimeSeriesPoint(date=datetime(2024, 2, 1), value=120.0),
        ]
        data = TimeSeriesData(
            metric_name="revenue",
            points=points,
            interval="daily",
            source_documents=["test.pdf"],
        )

        result = normalize_to_interval(data, "monthly")

        assert result.interval == "monthly"
        assert len(result.points) == 2
        # January average: (100 + 110) / 2 = 105
        assert result.points[0].value == 105.0
        assert result.points[0].label == "2024-01"
        # February: 120
        assert result.points[1].value == 120.0
        assert result.points[1].label == "2024-02"

    def test_normalize_to_quarterly(self) -> None:
        """AC3: Normalize monthly points to quarterly interval."""
        points = [
            TimeSeriesPoint(date=datetime(2024, 1, 1), value=100.0),
            TimeSeriesPoint(date=datetime(2024, 2, 1), value=110.0),
            TimeSeriesPoint(date=datetime(2024, 3, 1), value=120.0),
            TimeSeriesPoint(date=datetime(2024, 4, 1), value=130.0),
        ]
        data = TimeSeriesData(
            metric_name="revenue",
            points=points,
            interval="monthly",
            source_documents=["test.pdf"],
        )

        result = normalize_to_interval(data, "quarterly")

        assert result.interval == "quarterly"
        assert len(result.points) == 2
        # Q1 average: (100 + 110 + 120) / 3 = 110
        assert result.points[0].value == 110.0
        assert result.points[0].label == "2024-Q1"
        # Q2: 130
        assert result.points[1].value == 130.0
        assert result.points[1].label == "2024-Q2"

    def test_normalize_to_yearly(self) -> None:
        """AC3: Normalize quarterly points to yearly interval."""
        points = [
            TimeSeriesPoint(date=datetime(2023, 1, 1), value=100.0),
            TimeSeriesPoint(date=datetime(2023, 7, 1), value=120.0),
            TimeSeriesPoint(date=datetime(2024, 1, 1), value=140.0),
        ]
        data = TimeSeriesData(
            metric_name="revenue",
            points=points,
            interval="quarterly",
            source_documents=["test.pdf"],
        )

        result = normalize_to_interval(data, "yearly")

        assert result.interval == "yearly"
        assert len(result.points) == 2
        # 2023 average: (100 + 120) / 2 = 110
        assert result.points[0].value == 110.0
        assert result.points[0].label == "2023"
        # 2024: 140
        assert result.points[1].value == 140.0
        assert result.points[1].label == "2024"

    def test_normalize_empty_points(self) -> None:
        """AC3: Handle empty points list gracefully."""
        data = TimeSeriesData(
            metric_name="revenue",
            points=[],
            interval="raw",
            source_documents=[],
        )

        result = normalize_to_interval(data, "monthly")

        assert result.interval == "monthly"
        assert len(result.points) == 0

    def test_normalize_preserves_metadata(self) -> None:
        """AC3: Normalization preserves source documents metadata."""
        points = [TimeSeriesPoint(date=datetime(2024, 1, 1), value=100.0)]
        data = TimeSeriesData(
            metric_name="revenue",
            points=points,
            interval="raw",
            source_documents=["doc1.pdf", "doc2.pdf"],
        )

        result = normalize_to_interval(data, "monthly")

        assert result.metric_name == "revenue"
        assert result.source_documents == ["doc1.pdf", "doc2.pdf"]

    def test_invalid_interval_raises_error(self) -> None:
        """AC3: Invalid interval string raises ValueError."""
        data = TimeSeriesData(
            metric_name="revenue",
            points=[],
            interval="raw",
            source_documents=[],
        )

        with pytest.raises(ValueError, match="Unsupported interval"):
            normalize_to_interval(data, "weekly")


class TestExtractTimeseries:
    """Tests for extract_timeseries function (AC1, AC2)."""

    @pytest.mark.asyncio
    async def test_extract_timeseries_with_mock_llm(self) -> None:
        """AC1, AC2: Extract time-series data with mocked LLM response."""
        mock_search_results = [
            MagicMock(
                source_document="Q3_2024_Report.pdf",
                page_number=5,
                text="Revenue for Q1 2024 was $1.2M, Q2 2024 was $1.5M, Q3 2024 was $1.8M",
            )
        ]

        mock_llm_response = """[
            {"date": "Q1 2024", "value": 1200000, "label": "Q1 2024 Revenue"},
            {"date": "Q2 2024", "value": 1500000, "label": "Q2 2024 Revenue"},
            {"date": "Q3 2024", "value": 1800000, "label": "Q3 2024 Revenue"}
        ]"""

        with (
            patch(
                "raglite.retrieval.search.hybrid_search",
                new_callable=AsyncMock,
                return_value=mock_search_results,
            ),
            patch("raglite.shared.clients.get_mistral_client") as mock_client,
        ):
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = mock_llm_response
            mock_client.return_value.chat.complete.return_value = mock_response

            result = await extract_timeseries(["Q3_2024_Report.pdf"], metric="revenue")

            assert result.metric_name == "revenue"
            assert len(result.points) == 3
            assert result.points[0].value == 1200000
            assert result.points[1].value == 1500000
            assert result.points[2].value == 1800000
            assert "Q3_2024_Report.pdf" in result.source_documents

    @pytest.mark.asyncio
    async def test_extract_timeseries_handles_json_code_block(self) -> None:
        """AC2: Handle LLM response with markdown code blocks."""
        mock_search_results = [
            MagicMock(
                source_document="report.pdf",
                page_number=1,
                text="Revenue data",
            )
        ]

        mock_llm_response = """```json
        [{"date": "Jan 2024", "value": 100.0}]
        ```"""

        with (
            patch(
                "raglite.retrieval.search.hybrid_search",
                new_callable=AsyncMock,
                return_value=mock_search_results,
            ),
            patch("raglite.shared.clients.get_mistral_client") as mock_client,
        ):
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = mock_llm_response
            mock_client.return_value.chat.complete.return_value = mock_response

            result = await extract_timeseries(["report.pdf"], metric="revenue")

            assert len(result.points) == 1
            assert result.points[0].value == 100.0

    @pytest.mark.asyncio
    async def test_extract_timeseries_no_results_raises_error(self) -> None:
        """AC1: Raise ExtractionError when no documents found."""
        with patch(
            "raglite.retrieval.search.hybrid_search",
            new_callable=AsyncMock,
            return_value=[],
        ):
            with pytest.raises(ExtractionError, match="No documents found"):
                await extract_timeseries(["nonexistent.pdf"], metric="revenue")

    @pytest.mark.asyncio
    async def test_extract_timeseries_empty_llm_response_raises_error(self) -> None:
        """AC1: Raise ExtractionError when LLM returns empty array."""
        mock_search_results = [
            MagicMock(
                source_document="report.pdf",
                page_number=1,
                text="No revenue data",
            )
        ]

        with (
            patch(
                "raglite.retrieval.search.hybrid_search",
                new_callable=AsyncMock,
                return_value=mock_search_results,
            ),
            patch("raglite.shared.clients.get_mistral_client") as mock_client,
        ):
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "[]"
            mock_client.return_value.chat.complete.return_value = mock_response

            with pytest.raises(ExtractionError, match="No revenue data found"):
                await extract_timeseries(["report.pdf"], metric="revenue")

    @pytest.mark.asyncio
    async def test_extract_timeseries_invalid_json_raises_error(self) -> None:
        """AC2: Raise ExtractionError for invalid JSON response."""
        mock_search_results = [
            MagicMock(
                source_document="report.pdf",
                page_number=1,
                text="Revenue data",
            )
        ]

        with (
            patch(
                "raglite.retrieval.search.hybrid_search",
                new_callable=AsyncMock,
                return_value=mock_search_results,
            ),
            patch("raglite.shared.clients.get_mistral_client") as mock_client,
        ):
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "not valid json"
            mock_client.return_value.chat.complete.return_value = mock_response

            with pytest.raises(ExtractionError, match="Invalid LLM response"):
                await extract_timeseries(["report.pdf"], metric="revenue")

    @pytest.mark.asyncio
    async def test_extract_timeseries_sorts_by_date(self) -> None:
        """AC2: Results are sorted by date."""
        mock_search_results = [
            MagicMock(
                source_document="report.pdf",
                page_number=1,
                text="Revenue data",
            )
        ]

        # Return data out of order
        mock_llm_response = """[
            {"date": "Mar 2024", "value": 300},
            {"date": "Jan 2024", "value": 100},
            {"date": "Feb 2024", "value": 200}
        ]"""

        with (
            patch(
                "raglite.retrieval.search.hybrid_search",
                new_callable=AsyncMock,
                return_value=mock_search_results,
            ),
            patch("raglite.shared.clients.get_mistral_client") as mock_client,
        ):
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = mock_llm_response
            mock_client.return_value.chat.complete.return_value = mock_response

            result = await extract_timeseries(["report.pdf"], metric="revenue")

            # Should be sorted: Jan < Feb < Mar
            assert result.points[0].value == 100  # Jan
            assert result.points[1].value == 200  # Feb
            assert result.points[2].value == 300  # Mar

    @pytest.mark.asyncio
    async def test_extract_timeseries_filters_by_document(self) -> None:
        """AC1: Filter results by specified document names."""
        mock_search_results = [
            MagicMock(
                source_document="Q3_2024_Report.pdf",
                page_number=5,
                text="Q3 data",
            ),
            MagicMock(
                source_document="other_doc.pdf",
                page_number=1,
                text="Other data",
            ),
        ]

        mock_llm_response = '[{"date": "Q3 2024", "value": 100}]'

        with (
            patch(
                "raglite.retrieval.search.hybrid_search",
                new_callable=AsyncMock,
                return_value=mock_search_results,
            ),
            patch("raglite.shared.clients.get_mistral_client") as mock_client,
        ):
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = mock_llm_response
            mock_client.return_value.chat.complete.return_value = mock_response

            # Only request Q3_2024_Report.pdf
            result = await extract_timeseries(["Q3_2024_Report.pdf"], metric="revenue")

            assert len(result.points) == 1


class TestTimeSeriesModels:
    """Tests for Pydantic models (AC2)."""

    def test_timeseries_point_creation(self) -> None:
        """AC2: TimeSeriesPoint contains date, value, and label."""
        point = TimeSeriesPoint(
            date=datetime(2024, 1, 1),
            value=1000.0,
            label="Q1 2024",
        )

        assert point.date == datetime(2024, 1, 1)
        assert point.value == 1000.0
        assert point.label == "Q1 2024"

    def test_timeseries_point_optional_label(self) -> None:
        """AC2: TimeSeriesPoint label is optional."""
        point = TimeSeriesPoint(
            date=datetime(2024, 1, 1),
            value=1000.0,
        )

        assert point.label is None

    def test_timeseries_data_creation(self) -> None:
        """AC2: TimeSeriesData contains metric_name, points, interval, source_documents."""
        points = [
            TimeSeriesPoint(date=datetime(2024, 1, 1), value=100.0),
            TimeSeriesPoint(date=datetime(2024, 2, 1), value=200.0),
        ]
        data = TimeSeriesData(
            metric_name="revenue",
            points=points,
            interval="monthly",
            source_documents=["report.pdf"],
        )

        assert data.metric_name == "revenue"
        assert len(data.points) == 2
        assert data.interval == "monthly"
        assert data.source_documents == ["report.pdf"]

    def test_timeseries_data_defaults(self) -> None:
        """AC2: TimeSeriesData has sensible defaults."""
        data = TimeSeriesData(metric_name="revenue")

        assert data.points == []
        assert data.interval == "raw"
        assert data.source_documents == []


# =============================================================================
# Story 5.0.1: SQL-based time-series extraction tests
# =============================================================================


class TestParsePeriodToDate:
    """Test period string parsing to datetime (Mon-YY format) - Story 5.0.1 AC5."""

    @pytest.mark.parametrize(
        "period,fiscal_year,expected_month",
        [
            # All months in 2025
            ("Jan-25", 2025, 1),
            ("Feb-25", 2025, 2),
            ("Mar-25", 2025, 3),
            ("Apr-25", 2025, 4),
            ("May-25", 2025, 5),
            ("Jun-25", 2025, 6),
            ("Jul-25", 2025, 7),
            ("Aug-25", 2025, 8),
            ("Sep-25", 2025, 9),
            ("Oct-25", 2025, 10),
            ("Nov-25", 2025, 11),
            ("Dec-25", 2025, 12),
            # All months in 2024
            ("Jan-24", 2024, 1),
            ("Feb-24", 2024, 2),
            ("Mar-24", 2024, 3),
            ("Apr-24", 2024, 4),
            ("May-24", 2024, 5),
            ("Jun-24", 2024, 6),
            ("Jul-24", 2024, 7),
            ("Aug-24", 2024, 8),
            ("Sep-24", 2024, 9),
            ("Oct-24", 2024, 10),
            ("Nov-24", 2024, 11),
            ("Dec-24", 2024, 12),
        ],
    )
    def test_valid_period_formats_all_months(
        self, period: str, fiscal_year: int, expected_month: int
    ) -> None:
        """Test extraction from all valid Mon-YY month patterns."""
        result = parse_period_to_date(period, fiscal_year)

        assert result.year == fiscal_year
        assert result.month == expected_month
        assert result.day == 1  # Always first day of month
        assert result.hour == 0
        assert result.minute == 0
        assert result.second == 0

    def test_case_insensitivity(self) -> None:
        """Test that month abbreviations are case-insensitive."""
        test_cases = [
            ("jan-25", 2025, 1),
            ("JAN-25", 2025, 1),
            ("Jan-25", 2025, 1),
            ("jAn-25", 2025, 1),
        ]

        for period, fiscal_year, expected_month in test_cases:
            result = parse_period_to_date(period, fiscal_year)
            assert result.month == expected_month

    def test_whitespace_handling(self) -> None:
        """Test that leading/trailing whitespace is stripped."""
        result = parse_period_to_date("  Jan-25  ", 2025)
        assert result.month == 1
        assert result.year == 2025

    @pytest.mark.parametrize(
        "invalid_period",
        [
            "Var.",  # Non-date value
            "YTD",  # Non-date value
            "2024",  # Year only
            "Jan",  # Missing year
            "25",  # Year only
            "Jan 25",  # Space instead of hyphen
            "Jan_25",  # Underscore instead of hyphen
            "Jan-2025",  # 4-digit year
            "",  # Empty string
        ],
    )
    def test_invalid_period_formats(self, invalid_period: str) -> None:
        """Test that invalid period formats raise ValueError."""
        with pytest.raises(ValueError, match="Invalid period format"):
            parse_period_to_date(invalid_period, 2025)

    def test_invalid_month_abbreviation(self) -> None:
        """Test that unrecognized month abbreviations raise ValueError."""
        with pytest.raises(ValueError, match="Invalid month abbreviation"):
            parse_period_to_date("Xyz-25", 2025)


@pytest.mark.asyncio
class TestExtractTimeseriesFromSQL:
    """Test SQL-based time-series extraction - Story 5.0.1 AC2."""

    async def test_successful_extraction_sufficient_data(self) -> None:
        """Test successful extraction with ≥8 data points."""
        # Mock SQL connection and cursor
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("Jan-24", 2024, 100.5, 1, "2024-01 Performance Review", False),
            ("Feb-24", 2024, 105.2, 1, "2024-02 Performance Review", False),
            ("Mar-24", 2024, 110.8, 1, "2024-03 Performance Review", False),
            ("Apr-24", 2024, 115.3, 1, "2024-04 Performance Review", False),
            ("May-24", 2024, 120.0, 1, "2024-05 Performance Review", False),
            ("Jun-24", 2024, 125.5, 1, "2024-06 Performance Review", False),
            ("Jul-24", 2024, 130.2, 1, "2024-07 Performance Review", False),
            ("Aug-24", 2024, 135.8, 1, "2024-08 Performance Review", False),
            ("Sep-24", 2024, 140.3, 1, "2024-09 Performance Review", False),
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("raglite.shared.clients.get_postgresql_connection") as mock_pg:
            mock_pg.return_value = mock_conn

            result = await extract_timeseries_from_sql(metric="revenue", min_points=8)

            # Verify result
            assert isinstance(result, TimeSeriesData)
            assert result.metric_name == "revenue"
            assert len(result.points) == 9  # All 9 data points returned
            assert result.interval == "monthly"

            # Verify points are sorted chronologically
            assert result.points[0].date.month == 1  # Jan
            assert result.points[-1].date.month == 9  # Sep

            # Verify SQL query was executed with synonym-mapped metric
            mock_cursor.execute.assert_called_once()
            # "revenue" gets mapped to "turnover" via synonym mapping
            assert "turnover" in mock_cursor.execute.call_args[0][1]

    async def test_insufficient_data_raises_error(self) -> None:
        """Test that <min_points data raises ExtractionError (fallback when metrics can't be fetched)."""
        # Mock SQL connection with only 5 data points
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("Jan-24", 2024, 100.5, 1, "2024-01 Performance Review", False),
            ("Feb-24", 2024, 105.2, 1, "2024-02 Performance Review", False),
            ("Mar-24", 2024, 110.8, 1, "2024-03 Performance Review", False),
            ("Apr-24", 2024, 115.3, 1, "2024-04 Performance Review", False),
            ("May-24", 2024, 120.0, 1, "2024-05 Performance Review", False),
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("raglite.shared.clients.get_postgresql_connection") as mock_pg:
            mock_pg.return_value = mock_conn

            # Mock list_available_metrics to fail, ensuring fallback to ExtractionError
            with patch("raglite.forecasting.metrics.list_available_metrics") as mock_list:
                mock_list.side_effect = Exception("Metrics fetch failed")

                # When list_available_metrics fails, falls back to ExtractionError
                with pytest.raises(ExtractionError, match="Insufficient data.*found 5.*need 6"):
                    await extract_timeseries_from_sql(metric="revenue", min_points=6)

    async def test_no_data_found_raises_error(self) -> None:
        """Test that no SQL data raises ExtractionError."""
        # Mock SQL connection with no results
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("raglite.shared.clients.get_postgresql_connection") as mock_pg:
            mock_pg.return_value = mock_conn

            with pytest.raises(ExtractionError, match="No data found in financial_tables"):
                await extract_timeseries_from_sql(metric="revenue", min_points=8)

    async def test_invalid_data_points_skipped(self) -> None:
        """Test that invalid data points are skipped with warnings."""
        # Mock SQL connection with mix of valid and invalid data
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("Jan-24", 2024, 100.5, 1, "2024-01 Performance Review", False),
            (
                "InvalidFormat",
                2024,
                105.2,
                1,
                "2024-02 Performance Review",
                False,
            ),  # Invalid period format
            (
                "Mar-24",
                2024,
                "not_a_number",
                1,
                "2024-03 Performance Review",
                False,
            ),  # Invalid value
            ("Apr-24", 2024, 115.3, 1, "2024-04 Performance Review", False),
            ("May-24", 2024, 120.0, 1, "2024-05 Performance Review", False),
            ("Jun-24", 2024, 125.5, 1, "2024-06 Performance Review", False),
            ("Jul-24", 2024, 130.2, 1, "2024-07 Performance Review", False),
            ("Aug-24", 2024, 135.8, 1, "2024-08 Performance Review", False),
            ("Sep-24", 2024, 140.3, 1, "2024-09 Performance Review", False),
            ("Oct-24", 2024, 145.0, 1, "2024-10 Performance Review", False),
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("raglite.shared.clients.get_postgresql_connection") as mock_pg:
            mock_pg.return_value = mock_conn

            result = await extract_timeseries_from_sql(metric="revenue", min_points=8)

            # Should have 8 valid points (2 invalid skipped)
            assert len(result.points) == 8

    async def test_sql_query_error_handling(self) -> None:
        """Test that SQL query errors are caught and re-raised as ExtractionError."""
        # Mock SQL connection that raises an error
        mock_conn = MagicMock()
        mock_conn.cursor.side_effect = Exception("Database connection error")

        with patch("raglite.shared.clients.get_postgresql_connection") as mock_pg:
            mock_pg.return_value = mock_conn

            with pytest.raises(ExtractionError, match="SQL query failed"):
                await extract_timeseries_from_sql(metric="revenue", min_points=8)

    async def test_metric_pattern_matching(self) -> None:
        """Test that metric uses LIKE pattern for flexible matching."""
        # Mock SQL connection
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("Jan-24", 2024, 100.5, 1, "2024-01 Performance Review", False),
            ("Feb-24", 2024, 105.2, 1, "2024-02 Performance Review", False),
            ("Mar-24", 2024, 110.8, 1, "2024-03 Performance Review", False),
            ("Apr-24", 2024, 115.3, 1, "2024-04 Performance Review", False),
            ("May-24", 2024, 120.0, 1, "2024-05 Performance Review", False),
            ("Jun-24", 2024, 125.5, 1, "2024-06 Performance Review", False),
            ("Jul-24", 2024, 130.2, 1, "2024-07 Performance Review", False),
            ("Aug-24", 2024, 135.8, 1, "2024-08 Performance Review", False),
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("raglite.shared.clients.get_postgresql_connection") as mock_pg:
            mock_pg.return_value = mock_conn

            result = await extract_timeseries_from_sql(metric="revenue", min_points=8)

            # Should match via synonym mapping (revenue → turnover)
            assert len(result.points) == 8

            # Verify synonym mapping was applied (revenue → turnover)
            assert "turnover" in mock_cursor.execute.call_args[0][1]

    async def test_chronological_sorting(self) -> None:
        """Test that results are sorted chronologically by fiscal_year and period."""
        # Mock SQL connection with unsorted data
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("Jun-24", 2024, 125.5, 1, "2024-06 Performance Review", False),
            ("Jan-24", 2024, 100.5, 1, "2024-01 Performance Review", False),
            ("Dec-24", 2024, 150.0, 1, "2024-12 Performance Review", False),
            ("Mar-24", 2024, 110.8, 1, "2024-03 Performance Review", False),
            ("Sep-24", 2024, 140.3, 1, "2024-09 Performance Review", False),
            ("Apr-24", 2024, 115.3, 1, "2024-04 Performance Review", False),
            ("Feb-24", 2024, 105.2, 1, "2024-02 Performance Review", False),
            ("Aug-24", 2024, 135.8, 1, "2024-08 Performance Review", False),
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("raglite.shared.clients.get_postgresql_connection") as mock_pg:
            mock_pg.return_value = mock_conn

            result = await extract_timeseries_from_sql(metric="revenue", min_points=8)

            # Verify points are sorted chronologically
            dates = [p.date for p in result.points]
            assert dates == sorted(dates)

            # Verify first and last months
            assert result.points[0].date.month == 1  # Jan
            assert result.points[-1].date.month == 12  # Dec

    # Story 5.0.4 AC2: Tests for dynamic metric support
    async def test_arbitrary_metric_names_accepted(self) -> None:
        """Test that arbitrary metric names like 'capex', 'margins' are accepted (AC2)."""
        # Mock SQL connection for a custom metric "capex"
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("Jan-24", 2024, 50.0, 1, "2024-01 Performance Review", False),
            ("Feb-24", 2024, 52.0, 1, "2024-02 Performance Review", False),
            ("Mar-24", 2024, 48.5, 1, "2024-03 Performance Review", False),
            ("Apr-24", 2024, 51.2, 1, "2024-04 Performance Review", False),
            ("May-24", 2024, 53.0, 1, "2024-05 Performance Review", False),
            ("Jun-24", 2024, 49.8, 1, "2024-06 Performance Review", False),
            ("Jul-24", 2024, 54.5, 1, "2024-07 Performance Review", False),
            ("Aug-24", 2024, 52.3, 1, "2024-08 Performance Review", False),
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("raglite.shared.clients.get_postgresql_connection") as mock_pg:
            mock_pg.return_value = mock_conn

            # Should accept any metric name
            result = await extract_timeseries_from_sql(metric="capex", min_points=8)

            # Verify result
            assert result.metric_name == "capex"
            assert len(result.points) == 8
            # Verify metric name was used in query
            call_args = mock_cursor.execute.call_args[0]
            assert "capex" in call_args[1]

    async def test_metric_name_case_insensitivity(self) -> None:
        """Test that metric names are case insensitive: 'REVENUE' and 'revenue' return same data (AC2)."""
        # Test uppercase
        mock_cursor_upper = MagicMock()
        mock_cursor_upper.fetchall.return_value = [
            ("Jan-24", 2024, 100.0, 1, "2024-01 Performance Review", False),
            ("Feb-24", 2024, 105.0, 1, "2024-02 Performance Review", False),
            ("Mar-24", 2024, 110.0, 1, "2024-03 Performance Review", False),
            ("Apr-24", 2024, 115.0, 1, "2024-04 Performance Review", False),
            ("May-24", 2024, 120.0, 1, "2024-05 Performance Review", False),
            ("Jun-24", 2024, 125.0, 1, "2024-06 Performance Review", False),
            ("Jul-24", 2024, 130.0, 1, "2024-07 Performance Review", False),
            ("Aug-24", 2024, 135.0, 1, "2024-08 Performance Review", False),
        ]

        mock_conn_upper = MagicMock()
        mock_conn_upper.cursor.return_value = mock_cursor_upper

        with patch("raglite.shared.clients.get_postgresql_connection") as mock_pg:
            mock_pg.return_value = mock_conn_upper

            result_upper = await extract_timeseries_from_sql(metric="REVENUE", min_points=8)
            assert result_upper.metric_name == "REVENUE"
            assert len(result_upper.points) == 8

            # Verify synonym mapping was used (REVENUE → revenue → turnover)
            call_args = mock_cursor_upper.execute.call_args[0]
            assert "turnover" in call_args[1]

        # Test lowercase (separate mock to avoid state issues)
        mock_cursor_lower = MagicMock()
        mock_cursor_lower.fetchall.return_value = [
            ("Jan-24", 2024, 100.0, 1, "2024-01 Performance Review", False),
            ("Feb-24", 2024, 105.0, 1, "2024-02 Performance Review", False),
            ("Mar-24", 2024, 110.0, 1, "2024-03 Performance Review", False),
            ("Apr-24", 2024, 115.0, 1, "2024-04 Performance Review", False),
            ("May-24", 2024, 120.0, 1, "2024-05 Performance Review", False),
            ("Jun-24", 2024, 125.0, 1, "2024-06 Performance Review", False),
            ("Jul-24", 2024, 130.0, 1, "2024-07 Performance Review", False),
            ("Aug-24", 2024, 135.0, 1, "2024-08 Performance Review", False),
        ]

        mock_conn_lower = MagicMock()
        mock_conn_lower.cursor.return_value = mock_cursor_lower

        with patch("raglite.shared.clients.get_postgresql_connection") as mock_pg:
            mock_pg.return_value = mock_conn_lower

            result_lower = await extract_timeseries_from_sql(metric="revenue", min_points=8)
            assert result_lower.metric_name == "revenue"
            assert len(result_lower.points) == 8

            # Verify synonym mapping was used (revenue → turnover)
            call_args = mock_cursor_lower.execute.call_args[0]
            assert "turnover" in call_args[1]

    async def test_metric_synonym_resolution(self) -> None:
        """Test that metric synonyms are resolved correctly (AC2)."""
        # Mock SQL connection
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("Jan-24", 2024, 100.0, 1, "2024-01 Performance Review", False),
            ("Feb-24", 2024, 105.0, 1, "2024-02 Performance Review", False),
            ("Mar-24", 2024, 110.0, 1, "2024-03 Performance Review", False),
            ("Apr-24", 2024, 115.0, 1, "2024-04 Performance Review", False),
            ("May-24", 2024, 120.0, 1, "2024-05 Performance Review", False),
            ("Jun-24", 2024, 125.0, 1, "2024-06 Performance Review", False),
            ("Jul-24", 2024, 130.0, 1, "2024-07 Performance Review", False),
            ("Aug-24", 2024, 135.0, 1, "2024-08 Performance Review", False),
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("raglite.shared.clients.get_postgresql_connection") as mock_pg:
            mock_pg.return_value = mock_conn

            # Test "revenue" → "turnover" synonym
            _result = await extract_timeseries_from_sql(metric="revenue", min_points=8)

            # Verify SQL query uses "turnover" (synonym)
            call_args = mock_cursor.execute.call_args[0]
            assert "turnover" in call_args[1]  # Parameter should be "turnover"

            # Test "ebitda" → "EBITDA IFRS" synonym (Story 6.26: Restored)
            mock_cursor.reset_mock()
            _result_ebitda = await extract_timeseries_from_sql(metric="ebitda", min_points=8)

            call_args = mock_cursor.execute.call_args[0]
            # EBITDA synonym mapping - "ebitda" maps to "EBITDA IFRS" for consolidated YTD data
            assert (
                "EBITDA IFRS" in call_args[1]
            )  # Parameter should be "EBITDA IFRS" (synonym mapping applied)

    # Story 5.0.4 AC5: Test EBITDA consolidated GROUP extraction
    async def test_ebitda_uses_consolidated_group_values(self) -> None:
        """Test that EBITDA extraction uses consolidated GROUP values automatically (AC5)."""
        # Mock SQL connection with GROUP entity filtering
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            (
                "Jan-24",
                2024,
                155.5,
                3,
                "2024-01 Performance Review",
                False,
            ),  # Consolidated GROUP sum
            ("Feb-24", 2024, 160.2, 3, "2024-02 Performance Review", False),
            ("Mar-24", 2024, 165.8, 3, "2024-03 Performance Review", False),
            ("Apr-24", 2024, 170.3, 3, "2024-04 Performance Review", False),
            ("May-24", 2024, 175.0, 3, "2024-05 Performance Review", False),
            ("Jun-24", 2024, 180.5, 3, "2024-06 Performance Review", False),
            ("Jul-24", 2024, 185.2, 3, "2024-07 Performance Review", False),
            ("Aug-24", 2024, 190.8, 3, "2024-08 Performance Review", False),
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("raglite.shared.clients.get_postgresql_connection") as mock_pg:
            mock_pg.return_value = mock_conn

            # Extract EBITDA (should use consolidated GROUP filtering)
            result = await extract_timeseries_from_sql(metric="ebitda", min_points=8)

            # Verify result
            assert result.metric_name == "ebitda"
            assert len(result.points) == 8

            # Verify SQL query includes GROUP entity filter
            call_args = mock_cursor.execute.call_args[0]
            query = call_args[0]
            # Query should filter to GROUP entity
            assert "GROUP" in query or "group" in query or "consolidated" in query

    # Story 5.0.4 AC3: Tests for insufficient data validation
    async def test_insufficient_data_raises_metric_validation_error(self) -> None:
        """Test that <min_points data raises MetricValidationError with available metrics (AC3)."""

        # Mock SQL connection with only 3 data points
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("Jan-24", 2024, 100.0, 1, "2024-01 Performance Review", False),
            ("Feb-24", 2024, 105.0, 1, "2024-02 Performance Review", False),
            ("Mar-24", 2024, 110.0, 1, "2024-03 Performance Review", False),
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("raglite.shared.clients.get_postgresql_connection") as mock_pg:
            mock_pg.return_value = mock_conn

            # Mock list_available_metrics to return alternative metrics
            with patch("raglite.forecasting.metrics.list_available_metrics") as mock_list:
                from raglite.forecasting.metrics import MetricInfo

                # Note: period column is VARCHAR, not datetime (Story 5.0.4 fix)
                mock_list.return_value = [
                    MetricInfo(
                        name="revenue",
                        data_point_count=12,
                        min_period="Jan-23",
                        max_period="Dec-24",
                        can_forecast=True,
                    ),
                    MetricInfo(
                        name="ebitda",
                        data_point_count=10,
                        min_period="Jan-23",
                        max_period="Oct-24",
                        can_forecast=True,
                    ),
                ]

                # Should raise MetricValidationError
                with pytest.raises(MetricValidationError) as exc_info:
                    await extract_timeseries_from_sql(metric="margins", min_points=8)

                # Verify error details
                error = exc_info.value
                assert error.metric_name == "margins"
                assert error.data_points_found == 3
                assert error.minimum_required == 8
                assert "revenue" in error.available_metrics
                assert "ebitda" in error.available_metrics
                assert "margins" in str(error)  # Error message mentions the metric

    async def test_unknown_metric_suggests_available_metrics(self) -> None:
        """Test that unknown metric raises ExtractionError with available metrics suggestion (AC3)."""
        # Mock SQL connection with no results
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []  # No data found

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("raglite.shared.clients.get_postgresql_connection") as mock_pg:
            mock_pg.return_value = mock_conn

            # Mock list_available_metrics
            with patch("raglite.forecasting.metrics.list_available_metrics") as mock_list:
                from raglite.forecasting.metrics import MetricInfo

                # Note: period column is VARCHAR, not datetime (Story 5.0.4 fix)
                mock_list.return_value = [
                    MetricInfo(
                        name="revenue",
                        data_point_count=12,
                        min_period="Jan-23",
                        max_period="Dec-24",
                        can_forecast=True,
                    ),
                    MetricInfo(
                        name="ebitda",
                        data_point_count=10,
                        min_period="Jan-23",
                        max_period="Oct-24",
                        can_forecast=True,
                    ),
                ]

                # Should raise ExtractionError with available metrics
                with pytest.raises(ExtractionError) as exc_info:
                    await extract_timeseries_from_sql(metric="unknown_metric", min_points=8)

                # Verify error message contains suggestions
                error_msg = str(exc_info.value)
                assert "unknown_metric" in error_msg
                assert "Available metrics:" in error_msg
                assert "revenue" in error_msg or "ebitda" in error_msg


class TestYearValueFilter:
    """Tests for year-value data corruption filter (Story 6.24.1).

    Tests cover:
    - AC1: Filter values in range 2000-2099 from Capacity Utilization
    - AC2: Filter values in range 2000-2099 from Thermal Energy
    - AC3: Log filtered values for audit trail
    """

    @pytest.mark.asyncio
    async def test_year_value_filtered_in_sql_extraction(self) -> None:
        """AC1/AC2: Year values (2000-2099) are filtered during SQL extraction."""
        # Mock SQL connection with year values in data
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            # Normal values
            ("Jan-23", 2023, 85.5, 1, "2023-01 Performance Review", False),
            ("Feb-23", 2023, 87.2, 1, "2023-02 Performance Review", False),
            # Year values that should be filtered
            ("Mar-23", 2023, 2021.0, 1, "2021-12 Performance Review", False),  # Year!
            ("Apr-23", 2023, 2022.0, 1, "2022-12 Performance Review", False),  # Year!
            ("May-23", 2023, 2023.0, 1, "2023-01 Performance Review", False),  # Year!
            # More normal values
            ("Jun-23", 2023, 88.9, 1, "2023-06 Performance Review", False),
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("raglite.shared.clients.get_postgresql_connection") as mock_pg:
            mock_pg.return_value = mock_conn

            result = await extract_timeseries_from_sql(metric="Frequency Ratio", min_points=3)

            # Should only have 3 valid data points (year values filtered)
            assert len(result.points) == 3
            values = [p.value for p in result.points]
            assert 85.5 in values
            assert 87.2 in values
            assert 88.9 in values
            # Year values should NOT be present
            assert 2021.0 not in values
            assert 2022.0 not in values
            assert 2023.0 not in values

    @pytest.mark.asyncio
    async def test_year_value_filtered_in_percentage_metrics(self) -> None:
        """AC1: Year values filtered in percentage metric validation."""
        # Mock SQL connection with year values
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("Jan-23", 2023, 75.0, 1, "2023-01 Review", False),
            ("Feb-23", 2023, 2024.0, 1, "2024-02 Review", False),  # Year value!
            ("Mar-23", 2023, 80.0, 1, "2023-03 Review", False),
            ("Apr-23", 2023, 2021.0, 1, "2021-12 Review", False),  # Year value!
            ("May-23", 2023, 85.0, 1, "2023-05 Review", False),
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("raglite.shared.clients.get_postgresql_connection") as mock_pg:
            mock_pg.return_value = mock_conn

            result = await extract_timeseries_from_sql(metric="capacity_utilization", min_points=3)

            # Should only have 3 valid data points
            assert len(result.points) == 3
            values = [p.value for p in result.points]
            # Valid percentage values should be present
            assert 75.0 in values
            assert 80.0 in values
            assert 85.0 in values
            # Year values should be filtered
            assert 2024.0 not in values
            assert 2021.0 not in values

    @pytest.mark.asyncio
    async def test_year_boundary_values_filtered(self) -> None:
        """AC1/AC2: Boundary year values (2000, 2099) are filtered."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("Jan-23", 2023, 2000.0, 1, "2000-01 Review", False),  # Boundary year
            ("Feb-23", 2023, 2099.0, 1, "2099-12 Review", False),  # Boundary year
            ("Mar-23", 2023, 1999.0, 1, "2023-03 Review", False),  # NOT filtered (valid data)
            ("Apr-23", 2023, 2100.0, 1, "2023-04 Review", False),  # NOT filtered (valid data)
            ("May-23", 2023, 50.0, 1, "2023-05 Review", False),
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("raglite.shared.clients.get_postgresql_connection") as mock_pg:
            mock_pg.return_value = mock_conn

            result = await extract_timeseries_from_sql(metric="Thermal Energy", min_points=3)

            # Should have 3 valid data points (2000 and 2099 filtered)
            assert len(result.points) == 3
            values = [p.value for p in result.points]
            # Year boundary values should be filtered
            assert 2000.0 not in values
            assert 2099.0 not in values
            # Non-year values should be present
            assert 1999.0 in values  # Just outside year range
            assert 2100.0 in values  # Just outside year range
            assert 50.0 in values

    @pytest.mark.asyncio
    async def test_percentage_metric_year_value_logging(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """AC3: Filtered year values are logged for audit trail."""
        import logging

        caplog.set_level(logging.WARNING)

        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("Jan-23", 2023, 75.0, 1, "2023-01 Review", False),
            ("Feb-23", 2023, 2024.0, 1, "2024-02 Review", False),  # Year value
            ("Mar-23", 2023, 80.0, 1, "2023-03 Review", False),
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("raglite.shared.clients.get_postgresql_connection") as mock_pg:
            mock_pg.return_value = mock_conn

            await extract_timeseries_from_sql(metric="Frequency Ratio", min_points=2)

            # Check that year value filtering was logged
            # The year filter logs warnings during SQL extraction
            warning_records = [r for r in caplog.records if r.levelname == "WARNING"]
            assert len(warning_records) > 0, "Expected year-value filter warning logs"

            # Check for year-related warning messages
            log_messages = [record.message for record in warning_records]
            has_year_warning = any(
                "year" in msg.lower() or "filtered year" in msg.lower() for msg in log_messages
            )
            assert has_year_warning, f"Expected year-value filter warning. Got: {log_messages}"


class TestExtractExternalRegressorTimeseries:
    """Tests for extract_external_regressor_timeseries (Story 6.24.4).

    This function enables validation of external-only metrics by reusing
    regressor fetch logic, bridging the gap between regressor system and
    validation system.

    Testing Strategy:
    - Unit tests with mocked fetch_single_regressor
    - Tests cover AC1-AC5 from Story 6.24.4
    - Edge cases: NaN/Inf values, empty series, insufficient data
    - Boundary: No actual API calls (integration testing separate)
    """

    @pytest.mark.asyncio
    async def test_extract_euribor_3m_success(self, mocker) -> None:
        """Test successful extraction of euribor_3m regressor data."""
        from raglite.forecasting.timeseries_extract import extract_external_regressor_timeseries

        # Mock fetch_single_regressor to return sample data
        mock_series = pd.Series(
            data=[0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
            index=pd.date_range("2024-01-01", periods=6, freq="ME"),
        )
        # Fix Issue #1: Mock at import location, not definition location
        mocker.patch(
            "raglite.forecasting.timeseries_extract.fetch_single_regressor",
            return_value=mock_series,
        )

        result = await extract_external_regressor_timeseries("euribor_3m", min_points=6)

        assert result is not None
        assert result.metric_name == "euribor_3m"
        assert len(result.points) == 6
        assert result.points[0].value == 0.5
        assert result.points[-1].value == 1.0
        assert result.interval == "monthly"

    @pytest.mark.asyncio
    async def test_extract_insufficient_data_returns_none(self, mocker) -> None:
        """Test that insufficient data returns None."""
        from raglite.forecasting.timeseries_extract import extract_external_regressor_timeseries

        # Mock fetch_single_regressor to return insufficient data
        mock_series = pd.Series(
            data=[1.0, 2.0, 3.0],
            index=pd.date_range("2024-01-01", periods=3, freq="ME"),
        )
        mocker.patch(
            "raglite.forecasting.timeseries_extract.fetch_single_regressor",
            return_value=mock_series,
        )

        result = await extract_external_regressor_timeseries("gdp_growth", min_points=6)

        assert result is None

    @pytest.mark.asyncio
    async def test_extract_none_series_returns_none(self, mocker) -> None:
        """Test that None series from fetch returns None."""
        from raglite.forecasting.timeseries_extract import extract_external_regressor_timeseries

        # Mock fetch_single_regressor to return None
        mocker.patch(
            "raglite.forecasting.timeseries_extract.fetch_single_regressor",
            return_value=None,
        )

        result = await extract_external_regressor_timeseries("invalid_metric", min_points=6)

        assert result is None

    @pytest.mark.asyncio
    async def test_extract_empty_series_returns_none(self, mocker) -> None:
        """Test that empty series returns None (Issue #7 fix)."""
        from raglite.forecasting.timeseries_extract import extract_external_regressor_timeseries

        # Mock fetch_single_regressor to return empty series
        mock_series = pd.Series([], dtype=float)
        mocker.patch(
            "raglite.forecasting.timeseries_extract.fetch_single_regressor",
            return_value=mock_series,
        )

        result = await extract_external_regressor_timeseries("empty_metric", min_points=6)

        assert result is None

    @pytest.mark.asyncio
    async def test_extract_diesel_price_conversion(self, mocker) -> None:
        """Test data type conversion for diesel price regressor."""
        from raglite.forecasting.timeseries_extract import extract_external_regressor_timeseries

        # Mock fetch_single_regressor to return diesel price data
        mock_series = pd.Series(
            data=[1.45, 1.50, 1.55, 1.60, 1.65, 1.70, 1.75],
            index=pd.date_range("2024-01-01", periods=7, freq="ME"),
        )
        mocker.patch(
            "raglite.forecasting.timeseries_extract.fetch_single_regressor",
            return_value=mock_series,
        )

        result = await extract_external_regressor_timeseries("diesel", min_points=6)

        assert result is not None
        assert result.metric_name == "diesel"
        assert len(result.points) == 7
        # Verify all values are floats
        assert all(isinstance(p.value, float) for p in result.points)
        # Verify date conversion
        assert all(isinstance(p.date, datetime) for p in result.points)

    @pytest.mark.asyncio
    async def test_extract_filters_nan_values(self, mocker, caplog) -> None:
        """Test that NaN values are filtered out (Issue #4 fix)."""
        from raglite.forecasting.timeseries_extract import extract_external_regressor_timeseries

        # Mock fetch_single_regressor to return data with NaN
        mock_series = pd.Series(
            data=[1.0, float("nan"), 3.0, 4.0, float("nan"), 6.0, 7.0, 8.0],
            index=pd.date_range("2024-01-01", periods=8, freq="ME"),
        )
        mocker.patch(
            "raglite.forecasting.timeseries_extract.fetch_single_regressor",
            return_value=mock_series,
        )

        result = await extract_external_regressor_timeseries("test_metric", min_points=6)

        assert result is not None
        assert len(result.points) == 6  # 8 total - 2 NaN = 6 valid
        # Verify no NaN values in result
        assert all(not (val != val) for val in [p.value for p in result.points])
        # Check warning log
        warning_records = [r for r in caplog.records if r.levelname == "WARNING"]
        assert any("Filtered NaN/Inf values" in r.message for r in warning_records)

    @pytest.mark.asyncio
    async def test_extract_filters_inf_values(self, mocker, caplog) -> None:
        """Test that infinite values are filtered out (Issue #4 fix)."""
        from raglite.forecasting.timeseries_extract import extract_external_regressor_timeseries

        # Mock fetch_single_regressor to return data with Inf
        mock_series = pd.Series(
            data=[1.0, float("inf"), 3.0, 4.0, float("-inf"), 6.0, 7.0, 8.0],
            index=pd.date_range("2024-01-01", periods=8, freq="ME"),
        )
        mocker.patch(
            "raglite.forecasting.timeseries_extract.fetch_single_regressor",
            return_value=mock_series,
        )

        result = await extract_external_regressor_timeseries("test_metric", min_points=6)

        assert result is not None
        assert len(result.points) == 6  # 8 total - 2 Inf = 6 valid
        # Verify no infinite values in result
        import math

        assert all(not math.isinf(p.value) for p in result.points)
        # Check warning log
        warning_records = [r for r in caplog.records if r.levelname == "WARNING"]
        assert any("Filtered NaN/Inf values" in r.message for r in warning_records)

    @pytest.mark.asyncio
    async def test_extract_nan_filtering_insufficient_after_filter(self, mocker, caplog) -> None:
        """Test that insufficient data after NaN filtering returns None."""
        from raglite.forecasting.timeseries_extract import extract_external_regressor_timeseries

        # Mock fetch_single_regressor to return data with too many NaN
        mock_series = pd.Series(
            data=[1.0, float("nan"), float("nan"), 4.0, float("nan"), float("nan")],
            index=pd.date_range("2024-01-01", periods=6, freq="ME"),
        )
        mocker.patch(
            "raglite.forecasting.timeseries_extract.fetch_single_regressor",
            return_value=mock_series,
        )

        result = await extract_external_regressor_timeseries("test_metric", min_points=6)

        assert result is None  # Only 2 valid points after filtering
        # Check warning logs
        warning_records = [r for r in caplog.records if r.levelname == "WARNING"]
        assert any("Insufficient valid data after filtering" in r.message for r in warning_records)

    @pytest.mark.asyncio
    async def test_extract_handles_fetch_exception(self, mocker, caplog) -> None:
        """Test error handling when fetch_single_regressor raises exception."""
        from raglite.forecasting.timeseries_extract import extract_external_regressor_timeseries

        # Mock fetch_single_regressor to raise exception
        mocker.patch(
            "raglite.forecasting.timeseries_extract.fetch_single_regressor",
            side_effect=Exception("API connection failed"),
        )

        result = await extract_external_regressor_timeseries("construction_output", min_points=6)

        assert result is None
        # Check error log
        error_records = [r for r in caplog.records if r.levelname == "ERROR"]
        assert len(error_records) > 0
        assert any("Failed to extract external regressor" in r.message for r in error_records)
