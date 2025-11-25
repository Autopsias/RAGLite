"""Unit tests for time-series data extraction (Story 4.1).

Tests cover:
- AC1: Time-series extraction identifies temporal financial metrics
- AC2: Data points extracted with timestamps and metric labels
- AC3: Data normalized to consistent time intervals
- AC4: Handles various date formats and fiscal period labels
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from raglite.forecasting.timeseries_extract import (
    ExtractionError,
    extract_timeseries,
    normalize_to_interval,
    parse_fiscal_date,
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
            patch("raglite.shared.clients.get_claude_client") as mock_client,
        ):
            mock_response = MagicMock()
            mock_response.content = [MagicMock(text=mock_llm_response)]
            mock_client.return_value.messages.create.return_value = mock_response

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
            patch("raglite.shared.clients.get_claude_client") as mock_client,
        ):
            mock_response = MagicMock()
            mock_response.content = [MagicMock(text=mock_llm_response)]
            mock_client.return_value.messages.create.return_value = mock_response

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
            patch("raglite.shared.clients.get_claude_client") as mock_client,
        ):
            mock_response = MagicMock()
            mock_response.content = [MagicMock(text="[]")]
            mock_client.return_value.messages.create.return_value = mock_response

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
            patch("raglite.shared.clients.get_claude_client") as mock_client,
        ):
            mock_response = MagicMock()
            mock_response.content = [MagicMock(text="not valid json")]
            mock_client.return_value.messages.create.return_value = mock_response

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
            patch("raglite.shared.clients.get_claude_client") as mock_client,
        ):
            mock_response = MagicMock()
            mock_response.content = [MagicMock(text=mock_llm_response)]
            mock_client.return_value.messages.create.return_value = mock_response

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
            patch("raglite.shared.clients.get_claude_client") as mock_client,
        ):
            mock_response = MagicMock()
            mock_response.content = [MagicMock(text=mock_llm_response)]
            mock_client.return_value.messages.create.return_value = mock_response

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
