"""Unit tests for ExternalDataStorage class.

Story 6.2: PostgreSQL External Data Schema & Storage (AC6)

Uses mocking for fast unit testing without database.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from raglite.external_data.orm_models import ExternalDataPointORM, ExternalDataSourceORM
from raglite.external_data.storage import ExternalDataStorage


@pytest.fixture
def mock_session() -> MagicMock:
    """Create mock SQLAlchemy session."""
    session = MagicMock()
    session.query.return_value = session
    session.filter.return_value = session
    session.first.return_value = None
    session.all.return_value = []
    session.scalar.return_value = None
    return session


@pytest.fixture
def storage(mock_session: MagicMock) -> ExternalDataStorage:
    """Create ExternalDataStorage with mock session."""
    return ExternalDataStorage(mock_session)


class TestExternalDataStorageInit:
    """Tests for ExternalDataStorage initialization."""

    def test_init_stores_session(self, mock_session: MagicMock) -> None:
        """Test that init stores the session."""
        storage = ExternalDataStorage(mock_session)
        assert storage.session is mock_session


class TestExternalDataStorageCreateSource:
    """Tests for create_source() method."""

    def test_create_source_adds_to_session(
        self, storage: ExternalDataStorage, mock_session: MagicMock
    ) -> None:
        """Test that create_source adds source to session."""
        storage.create_source(
            source_name="TestSource",
            api_endpoint="https://example.com",
            data_type="time_series",
            refresh_frequency="monthly",
        )

        mock_session.add.assert_called_once()
        mock_session.commit.assert_called()

    def test_create_source_with_metadata(
        self, storage: ExternalDataStorage, mock_session: MagicMock
    ) -> None:
        """Test creating source with metadata."""
        metadata = {"version": "1.0", "region": "Portugal"}
        storage.create_source(
            source_name="TestSource",
            metadata=metadata,
        )

        call_args = mock_session.add.call_args[0][0]
        assert call_args.metadata_ == metadata

    def test_create_source_returns_orm_object(
        self, storage: ExternalDataStorage, mock_session: MagicMock
    ) -> None:
        """Test that create_source returns the ORM object."""
        result = storage.create_source(source_name="TestSource")

        assert isinstance(result, ExternalDataSourceORM)
        assert result.source_name == "TestSource"


class TestExternalDataStorageGetSource:
    """Tests for get_source() method."""

    def test_get_source_queries_by_name(
        self, storage: ExternalDataStorage, mock_session: MagicMock
    ) -> None:
        """Test that get_source queries by source_name."""
        storage.get_source("TestSource")

        mock_session.query.assert_called_with(ExternalDataSourceORM)

    def test_get_source_filters_deleted(
        self, storage: ExternalDataStorage, mock_session: MagicMock
    ) -> None:
        """Test that get_source filters out deleted sources."""
        storage.get_source("TestSource")

        # Verify filter was called (checks for deleted_at is None)
        assert mock_session.filter.called

    def test_get_source_returns_none_when_not_found(
        self, storage: ExternalDataStorage, mock_session: MagicMock
    ) -> None:
        """Test that get_source returns None when source not found."""
        mock_session.first.return_value = None

        result = storage.get_source("NonExistent")

        assert result is None

    def test_get_source_returns_source_when_found(
        self, storage: ExternalDataStorage, mock_session: MagicMock
    ) -> None:
        """Test that get_source returns source when found."""
        mock_source = ExternalDataSourceORM(id=1, source_name="TestSource")
        mock_session.first.return_value = mock_source

        result = storage.get_source("TestSource")

        assert result is mock_source


class TestExternalDataStorageGetOrCreateSource:
    """Tests for get_or_create_source() method."""

    def test_get_or_create_returns_existing(
        self, storage: ExternalDataStorage, mock_session: MagicMock
    ) -> None:
        """Test that get_or_create returns existing source."""
        mock_source = ExternalDataSourceORM(id=1, source_name="ExistingSource")
        mock_session.first.return_value = mock_source

        source, created = storage.get_or_create_source("ExistingSource")

        assert source is mock_source
        assert created is False
        mock_session.add.assert_not_called()

    def test_get_or_create_creates_new(
        self, storage: ExternalDataStorage, mock_session: MagicMock
    ) -> None:
        """Test that get_or_create creates new source when not found."""
        mock_session.first.return_value = None

        source, created = storage.get_or_create_source(
            source_name="NewSource",
            data_type="time_series",
        )

        assert created is True
        assert source.source_name == "NewSource"
        mock_session.add.assert_called_once()


class TestExternalDataStorageInsertDataPoints:
    """Tests for insert_data_points() method."""

    def test_insert_data_points_source_not_found_raises(
        self, storage: ExternalDataStorage, mock_session: MagicMock
    ) -> None:
        """Test that insert raises ValueError when source not found."""
        mock_session.first.return_value = None

        with pytest.raises(ValueError, match="not found"):
            storage.insert_data_points("NonExistent", [])

    def test_insert_data_points_empty_list_returns_zero(
        self, storage: ExternalDataStorage, mock_session: MagicMock
    ) -> None:
        """Test that empty list returns 0."""
        mock_source = ExternalDataSourceORM(id=1, source_name="TestSource")
        mock_session.first.return_value = mock_source

        count = storage.insert_data_points("TestSource", [])

        assert count == 0

    def test_insert_data_points_adds_to_session(
        self, storage: ExternalDataStorage, mock_session: MagicMock
    ) -> None:
        """Test that data points are added to session."""
        mock_source = ExternalDataSourceORM(id=1, source_name="TestSource")
        mock_session.first.return_value = mock_source

        data_points = [
            {"date": date(2024, 1, 1), "metric_name": "permits", "value": 100},
            {"date": date(2024, 2, 1), "metric_name": "permits", "value": 200},
        ]

        count = storage.insert_data_points("TestSource", data_points)

        assert count == 2
        assert mock_session.add.call_count == 2
        mock_session.commit.assert_called()

    def test_insert_data_points_creates_correct_orm_objects(
        self, storage: ExternalDataStorage, mock_session: MagicMock
    ) -> None:
        """Test that correct ORM objects are created."""
        mock_source = ExternalDataSourceORM(id=42, source_name="TestSource")
        mock_session.first.return_value = mock_source

        data_points = [
            {
                "date": date(2024, 1, 15),
                "metric_name": "temperature",
                "value": 22.5,
                "unit": "celsius",
                "metadata": {"station": "Lisboa"},
            }
        ]

        storage.insert_data_points("TestSource", data_points)

        call_args = mock_session.add.call_args[0][0]
        assert isinstance(call_args, ExternalDataPointORM)
        assert call_args.source_id == 42
        assert call_args.date == date(2024, 1, 15)
        assert call_args.metric_name == "temperature"
        assert call_args.value == 22.5
        assert call_args.unit == "celsius"
        assert call_args.metadata_ == {"station": "Lisboa"}


class TestExternalDataStorageQueryDataRange:
    """Tests for query_data_range() method."""

    def test_query_data_range_source_not_found_raises(
        self, storage: ExternalDataStorage, mock_session: MagicMock
    ) -> None:
        """Test that query raises ValueError when source not found."""
        mock_session.first.return_value = None

        with pytest.raises(ValueError, match="not found"):
            storage.query_data_range("NonExistent", date(2024, 1, 1), date(2024, 12, 31))

    def test_query_data_range_returns_results(
        self, storage: ExternalDataStorage, mock_session: MagicMock
    ) -> None:
        """Test that query returns results from session."""
        mock_source = ExternalDataSourceORM(id=1, source_name="TestSource")
        mock_points = [
            ExternalDataPointORM(
                id=1,
                source_id=1,
                date=date(2024, 1, 1),
                metric_name="permits",
                value=Decimal("100"),
            ),
            ExternalDataPointORM(
                id=2,
                source_id=1,
                date=date(2024, 2, 1),
                metric_name="permits",
                value=Decimal("200"),
            ),
        ]

        # Setup mock chain
        mock_session.first.return_value = mock_source
        mock_session.all.return_value = mock_points
        mock_session.order_by.return_value = mock_session

        results = storage.query_data_range("TestSource", date(2024, 1, 1), date(2024, 12, 31))

        assert results == mock_points


class TestExternalDataStorageQueryLatest:
    """Tests for query_latest() method."""

    def test_query_latest_source_not_found_raises(
        self, storage: ExternalDataStorage, mock_session: MagicMock
    ) -> None:
        """Test that query raises ValueError when source not found."""
        mock_session.first.return_value = None

        with pytest.raises(ValueError, match="not found"):
            storage.query_latest("NonExistent")

    def test_query_latest_returns_limited_results(
        self, storage: ExternalDataStorage, mock_session: MagicMock
    ) -> None:
        """Test that query_latest returns limited results."""
        mock_source = ExternalDataSourceORM(id=1, source_name="TestSource")
        mock_points = [
            ExternalDataPointORM(
                id=1,
                source_id=1,
                date=date(2024, 3, 1),
                metric_name="permits",
                value=Decimal("300"),
            ),
        ]

        mock_session.first.return_value = mock_source
        mock_session.order_by.return_value = mock_session
        mock_session.limit.return_value = mock_session
        mock_session.all.return_value = mock_points

        results = storage.query_latest("TestSource", limit=1)

        assert results == mock_points
        mock_session.limit.assert_called_with(1)


class TestExternalDataStorageSoftDelete:
    """Tests for soft_delete_source() method."""

    def test_soft_delete_source_not_found_returns_false(
        self, storage: ExternalDataStorage, mock_session: MagicMock
    ) -> None:
        """Test that soft delete returns False when source not found."""
        mock_session.first.return_value = None

        result = storage.soft_delete_source("NonExistent")

        assert result is False

    def test_soft_delete_source_updates_deleted_at(
        self, storage: ExternalDataStorage, mock_session: MagicMock
    ) -> None:
        """Test that soft delete sets deleted_at timestamp."""
        mock_source = ExternalDataSourceORM(id=1, source_name="TestSource")
        mock_session.first.return_value = mock_source

        result = storage.soft_delete_source("TestSource")

        assert result is True
        assert mock_source.deleted_at is not None
        mock_session.execute.assert_called()  # For updating data points
        mock_session.commit.assert_called()


class TestExternalDataStorageListSources:
    """Tests for list_sources() method."""

    def test_list_sources_returns_all(
        self, storage: ExternalDataStorage, mock_session: MagicMock
    ) -> None:
        """Test that list_sources returns all sources."""
        mock_sources = [
            ExternalDataSourceORM(id=1, source_name="Source_A"),
            ExternalDataSourceORM(id=2, source_name="Source_B"),
        ]
        mock_session.order_by.return_value = mock_session
        mock_session.all.return_value = mock_sources

        results = storage.list_sources()

        assert results == mock_sources

    def test_list_sources_filters_deleted_by_default(
        self, storage: ExternalDataStorage, mock_session: MagicMock
    ) -> None:
        """Test that deleted sources are filtered by default."""
        mock_session.order_by.return_value = mock_session
        mock_session.all.return_value = []

        storage.list_sources()

        # Verify filter was called
        assert mock_session.filter.called


class TestExternalDataStorageGetMetrics:
    """Tests for get_metrics_for_source() method."""

    def test_get_metrics_source_not_found_raises(
        self, storage: ExternalDataStorage, mock_session: MagicMock
    ) -> None:
        """Test that get_metrics raises ValueError when source not found."""
        mock_session.first.return_value = None

        with pytest.raises(ValueError, match="not found"):
            storage.get_metrics_for_source("NonExistent")

    def test_get_metrics_returns_unique_names(
        self, storage: ExternalDataStorage, mock_session: MagicMock
    ) -> None:
        """Test that get_metrics returns unique metric names."""
        mock_source = ExternalDataSourceORM(id=1, source_name="TestSource")
        mock_session.first.return_value = mock_source
        mock_session.distinct.return_value = mock_session
        mock_session.all.return_value = [("permits",), ("output",), ("cost_index",)]

        results = storage.get_metrics_for_source("TestSource")

        assert set(results) == {"permits", "output", "cost_index"}
