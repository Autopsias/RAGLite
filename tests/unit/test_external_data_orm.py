"""Unit tests for external data ORM models.

Story 6.2: PostgreSQL External Data Schema & Storage (AC7)

Uses mocking - NO database connection required.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch


class TestExternalDataSourceORM:
    """Unit tests for ExternalDataSourceORM model."""

    def test_external_data_source_orm_creation(self) -> None:
        """Test ORM model instantiation without database."""
        from raglite.external_data.orm_models import ExternalDataSourceORM

        source = ExternalDataSourceORM(
            source_name="INE_BuildingPermits",
            api_endpoint="https://ine.pt/api",
            data_type="time_series",
            refresh_frequency="monthly",
        )
        assert source.source_name == "INE_BuildingPermits"
        assert source.api_endpoint == "https://ine.pt/api"
        assert source.data_type == "time_series"
        assert source.refresh_frequency == "monthly"
        assert source.deleted_at is None  # Soft delete not set

    def test_external_data_source_orm_soft_delete_column(self) -> None:
        """Test that soft delete column exists and is nullable."""
        from raglite.external_data.orm_models import ExternalDataSourceORM

        source = ExternalDataSourceORM(source_name="Test_Source")
        assert source.deleted_at is None

        # Can set deleted_at for soft delete
        source.deleted_at = datetime.now(UTC)
        assert source.deleted_at is not None

    def test_external_data_source_orm_repr(self) -> None:
        """Test string representation."""
        from raglite.external_data.orm_models import ExternalDataSourceORM

        source = ExternalDataSourceORM(id=1, source_name="Test_Source")
        repr_str = repr(source)
        assert "ExternalDataSourceORM" in repr_str
        assert "id=1" in repr_str
        assert "Test_Source" in repr_str

    def test_external_data_source_orm_metadata_column(self) -> None:
        """Test JSONB metadata column."""
        from raglite.external_data.orm_models import ExternalDataSourceORM

        source = ExternalDataSourceORM(
            source_name="Test_Source",
            metadata_={"key": "value", "nested": {"inner": 123}},
        )
        assert source.metadata_["key"] == "value"
        assert source.metadata_["nested"]["inner"] == 123


class TestExternalDataPointORM:
    """Unit tests for ExternalDataPointORM model."""

    def test_external_data_point_orm_creation(self) -> None:
        """Test ORM model instantiation without database."""
        from raglite.external_data.orm_models import ExternalDataPointORM

        point = ExternalDataPointORM(
            source_id=1,
            date=date(2024, 1, 15),
            metric_name="building_permits",
            value=Decimal("1234.56"),
            unit="count",
        )
        assert point.source_id == 1
        assert point.date == date(2024, 1, 15)
        assert point.metric_name == "building_permits"
        assert point.value == Decimal("1234.56")
        assert point.unit == "count"
        assert point.deleted_at is None  # Soft delete not set

    def test_external_data_point_orm_soft_delete_column(self) -> None:
        """Test that soft delete column exists and is nullable."""
        from raglite.external_data.orm_models import ExternalDataPointORM

        point = ExternalDataPointORM(
            source_id=1,
            date=date(2024, 1, 1),
            metric_name="test",
            value=Decimal("100"),
        )
        assert point.deleted_at is None

        # Can set deleted_at for soft delete
        point.deleted_at = datetime.now(UTC)
        assert point.deleted_at is not None

    def test_external_data_point_orm_repr(self) -> None:
        """Test string representation."""
        from raglite.external_data.orm_models import ExternalDataPointORM

        point = ExternalDataPointORM(
            id=1,
            source_id=2,
            date=date(2024, 1, 15),
            metric_name="test_metric",
            value=Decimal("100"),
        )
        repr_str = repr(point)
        assert "ExternalDataPointORM" in repr_str
        assert "id=1" in repr_str
        assert "source_id=2" in repr_str
        assert "test_metric" in repr_str

    def test_external_data_point_orm_metadata_column(self) -> None:
        """Test JSONB metadata column."""
        from raglite.external_data.orm_models import ExternalDataPointORM

        point = ExternalDataPointORM(
            source_id=1,
            date=date(2024, 1, 1),
            metric_name="test",
            value=Decimal("100"),
            metadata_={"region": "Portugal", "confidence": 0.95},
        )
        assert point.metadata_["region"] == "Portugal"
        assert point.metadata_["confidence"] == 0.95


class TestDatabaseModule:
    """Unit tests for database module (mocked)."""

    def test_get_engine_returns_engine(self) -> None:
        """Test get_engine creates SQLAlchemy engine."""
        with patch("raglite.shared.database.create_engine") as mock_create_engine:
            mock_engine = MagicMock()
            mock_create_engine.return_value = mock_engine

            from raglite.shared.database import reset_engine

            reset_engine()  # Reset singleton

            from raglite.shared.database import get_engine

            engine = get_engine()

            mock_create_engine.assert_called_once()
            assert engine is mock_engine

    def test_get_session_returns_session(self) -> None:
        """Test get_session creates SQLAlchemy session."""
        with patch("raglite.shared.database.create_engine") as mock_create_engine:
            mock_engine = MagicMock()
            mock_create_engine.return_value = mock_engine

            from raglite.shared.database import reset_engine

            reset_engine()  # Reset singleton

            from raglite.shared.database import get_session

            session = get_session()

            assert session is not None

    def test_reset_engine_clears_singleton(self) -> None:
        """Test reset_engine clears the engine singleton."""
        from raglite.shared.database import reset_engine

        with patch("raglite.shared.database.create_engine") as mock_create_engine:
            mock_engine = MagicMock()
            mock_create_engine.return_value = mock_engine

            reset_engine()

            from raglite.shared import database

            assert database._engine is None
            assert database._SessionLocal is None


class TestBaseMetadata:
    """Unit tests for SQLAlchemy Base metadata."""

    def test_base_contains_external_data_tables(self) -> None:
        """Test that Base.metadata contains our ORM tables."""
        # Import models to register them
        from raglite.external_data.orm_models import (  # noqa: F401
            ExternalDataPointORM,
            ExternalDataSourceORM,
        )
        from raglite.shared.database import Base

        table_names = list(Base.metadata.tables.keys())
        assert "external_data_sources" in table_names
        assert "external_data_points" in table_names

    def test_external_data_sources_table_columns(self) -> None:
        """Test external_data_sources table has expected columns."""
        from raglite.external_data.orm_models import (  # noqa: F401
            ExternalDataSourceORM,
        )
        from raglite.shared.database import Base

        table = Base.metadata.tables["external_data_sources"]
        column_names = [c.name for c in table.columns]

        expected_columns = [
            "id",
            "source_name",
            "api_endpoint",
            "data_type",
            "refresh_frequency",
            "last_refresh_at",
            "created_at",
            "deleted_at",
            "metadata",
        ]
        for col in expected_columns:
            assert col in column_names, f"Missing column: {col}"

    def test_external_data_points_table_columns(self) -> None:
        """Test external_data_points table has expected columns."""
        from raglite.external_data.orm_models import (  # noqa: F401
            ExternalDataPointORM,
        )
        from raglite.shared.database import Base

        table = Base.metadata.tables["external_data_points"]
        column_names = [c.name for c in table.columns]

        expected_columns = [
            "id",
            "source_id",
            "date",
            "metric_name",
            "value",
            "unit",
            "metadata",
            "created_at",
            "deleted_at",
        ]
        for col in expected_columns:
            assert col in column_names, f"Missing column: {col}"

    def test_external_data_points_foreign_key(self) -> None:
        """Test foreign key constraint on source_id."""
        from raglite.external_data.orm_models import (  # noqa: F401
            ExternalDataPointORM,
        )
        from raglite.shared.database import Base

        table = Base.metadata.tables["external_data_points"]
        source_id_col = table.c.source_id

        # Check foreign key exists
        fks = list(source_id_col.foreign_keys)
        assert len(fks) == 1
        assert fks[0].column.table.name == "external_data_sources"

    def test_external_data_points_indexes(self) -> None:
        """Test indexes are defined on external_data_points."""
        from raglite.external_data.orm_models import (  # noqa: F401
            ExternalDataPointORM,
        )
        from raglite.shared.database import Base

        table = Base.metadata.tables["external_data_points"]
        index_names = [idx.name for idx in table.indexes]

        assert "idx_data_points_source_date" in index_names
        assert "idx_data_points_metric" in index_names

    def test_external_data_points_unique_constraint(self) -> None:
        """Test unique constraint on (source_id, date, metric_name)."""
        from raglite.external_data.orm_models import (  # noqa: F401
            ExternalDataPointORM,
        )
        from raglite.shared.database import Base

        table = Base.metadata.tables["external_data_points"]
        constraints = list(table.constraints)

        unique_constraints = [
            c for c in constraints if hasattr(c, "name") and c.name == "uq_source_date_metric"
        ]
        assert len(unique_constraints) == 1
