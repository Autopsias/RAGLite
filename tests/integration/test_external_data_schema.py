"""Integration tests for external data PostgreSQL schema.

Story 6.2: PostgreSQL External Data Schema & Storage (AC8)

REQUIRES: PostgreSQL running on test port (5433)
"""

from __future__ import annotations

import os
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

# Set test environment before importing
os.environ["APP_ENV"] = "test"

# Skip all tests in this module if not running integration tests
pytestmark = [pytest.mark.integration, pytest.mark.preserve_collection]


@pytest.fixture(scope="module")
def db_session():
    """PostgreSQL session for integration tests.

    Creates tables in test database and yields session.
    Rolls back after tests complete.
    """
    from raglite.shared.safety import SafetyGuard

    guard = SafetyGuard()
    guard.validate_test_environment("external_data_integration")

    # IMPORTANT: Import ORM models BEFORE create_all() so they register with Base
    from raglite.external_data.orm_models import (  # noqa: F401
        ExternalDataPointORM,
        ExternalDataSourceORM,
    )
    from raglite.shared.database import Base, get_engine, get_session, reset_engine

    # Reset engine to pick up test environment settings
    reset_engine()

    # Create tables in test database
    engine = get_engine()
    Base.metadata.create_all(engine)

    session = get_session()
    yield session

    session.rollback()
    session.close()


@pytest.fixture
def clean_session(db_session):
    """Clean session that rolls back after each test."""
    yield db_session
    db_session.rollback()


class TestSchemaCreation:
    """Tests for PostgreSQL schema creation (AC1)."""

    def test_external_data_sources_table_exists(self, clean_session) -> None:
        """Test external_data_sources table was created."""
        from raglite.external_data.orm_models import ExternalDataSourceORM

        # Simple query to verify table exists
        count = clean_session.query(ExternalDataSourceORM).count()
        assert count >= 0  # Table exists if query succeeds

    def test_external_data_points_table_exists(self, clean_session) -> None:
        """Test external_data_points table was created."""
        from raglite.external_data.orm_models import ExternalDataPointORM

        # Simple query to verify table exists
        count = clean_session.query(ExternalDataPointORM).count()
        assert count >= 0  # Table exists if query succeeds


class TestCRUDOperations:
    """Tests for CRUD operations on external data tables."""

    def test_create_external_data_source(self, clean_session) -> None:
        """Test creating a new external data source."""
        from raglite.external_data.orm_models import ExternalDataSourceORM

        source = ExternalDataSourceORM(
            source_name="INE_Test_Integration",
            api_endpoint="https://ine.pt/api/test",
            data_type="time_series",
            refresh_frequency="monthly",
        )
        clean_session.add(source)
        clean_session.flush()

        assert source.id is not None
        assert source.created_at is not None

    def test_create_external_data_point(self, clean_session) -> None:
        """Test creating a new external data point."""
        from raglite.external_data.orm_models import ExternalDataPointORM, ExternalDataSourceORM

        # Create source first
        source = ExternalDataSourceORM(
            source_name="INE_Test_Point",
            data_type="time_series",
        )
        clean_session.add(source)
        clean_session.flush()

        # Create data point
        point = ExternalDataPointORM(
            source_id=source.id,
            date=date(2024, 6, 15),
            metric_name="building_permits",
            value=Decimal("1234.56"),
            unit="count",
        )
        clean_session.add(point)
        clean_session.flush()

        assert point.id is not None
        assert point.created_at is not None

    def test_query_data_points_by_date_range(self, clean_session) -> None:
        """Test querying data points within a date range."""
        from raglite.external_data.orm_models import ExternalDataPointORM, ExternalDataSourceORM

        # Create source
        source = ExternalDataSourceORM(
            source_name="INE_Test_DateRange",
            data_type="time_series",
        )
        clean_session.add(source)
        clean_session.flush()

        # Create multiple data points
        for i in range(3):
            point = ExternalDataPointORM(
                source_id=source.id,
                date=date(2024, 1 + i, 15),
                metric_name="test_metric",
                value=Decimal(str(100 + i * 10)),
                unit="count",
            )
            clean_session.add(point)
        clean_session.flush()

        # Query by date range
        points = (
            clean_session.query(ExternalDataPointORM)
            .filter(
                ExternalDataPointORM.source_id == source.id,
                ExternalDataPointORM.date >= date(2024, 1, 1),
                ExternalDataPointORM.date <= date(2024, 2, 28),
            )
            .all()
        )

        assert len(points) == 2

    def test_soft_delete_data_point(self, clean_session) -> None:
        """Test soft deleting a data point."""
        from raglite.external_data.orm_models import ExternalDataPointORM, ExternalDataSourceORM

        # Create source and point
        source = ExternalDataSourceORM(
            source_name="INE_Test_SoftDelete",
            data_type="time_series",
        )
        clean_session.add(source)
        clean_session.flush()

        point = ExternalDataPointORM(
            source_id=source.id,
            date=date(2024, 1, 15),
            metric_name="test_metric",
            value=Decimal("100"),
        )
        clean_session.add(point)
        clean_session.flush()

        # Soft delete
        point.deleted_at = datetime.now(UTC)
        clean_session.flush()

        # Verify soft deleted
        deleted_point = (
            clean_session.query(ExternalDataPointORM)
            .filter(ExternalDataPointORM.id == point.id)
            .first()
        )
        assert deleted_point.deleted_at is not None


class TestConstraints:
    """Tests for database constraints."""

    def test_foreign_key_constraint(self, clean_session) -> None:
        """Test foreign key constraint enforcement."""
        from raglite.external_data.orm_models import ExternalDataPointORM

        # Try to create data point with non-existent source_id
        point = ExternalDataPointORM(
            source_id=99999,  # Non-existent source
            date=date(2024, 1, 1),
            metric_name="test",
            value=Decimal("100"),
        )
        clean_session.add(point)

        with pytest.raises(IntegrityError):
            clean_session.flush()

        clean_session.rollback()

    def test_unique_constraint_on_source_date_metric(self, clean_session) -> None:
        """Test unique constraint on (source_id, date, metric_name)."""
        from raglite.external_data.orm_models import ExternalDataPointORM, ExternalDataSourceORM

        # Create source
        source = ExternalDataSourceORM(
            source_name="INE_Test_Unique",
            data_type="time_series",
        )
        clean_session.add(source)
        clean_session.flush()

        # Create first data point
        point1 = ExternalDataPointORM(
            source_id=source.id,
            date=date(2024, 1, 15),
            metric_name="building_permits",
            value=Decimal("100"),
        )
        clean_session.add(point1)
        clean_session.flush()

        # Try to create duplicate
        point2 = ExternalDataPointORM(
            source_id=source.id,
            date=date(2024, 1, 15),  # Same date
            metric_name="building_permits",  # Same metric
            value=Decimal("200"),
        )
        clean_session.add(point2)

        with pytest.raises(IntegrityError):
            clean_session.flush()

        clean_session.rollback()

    def test_unique_source_name(self, clean_session) -> None:
        """Test unique constraint on source_name."""
        from raglite.external_data.orm_models import ExternalDataSourceORM

        # Create first source
        source1 = ExternalDataSourceORM(
            source_name="INE_Test_UniqueName",
            data_type="time_series",
        )
        clean_session.add(source1)
        clean_session.flush()

        # Try to create duplicate name
        source2 = ExternalDataSourceORM(
            source_name="INE_Test_UniqueName",  # Same name
            data_type="different",
        )
        clean_session.add(source2)

        with pytest.raises(IntegrityError):
            clean_session.flush()

        clean_session.rollback()


class TestRelationships:
    """Tests for ORM relationships."""

    def test_source_to_data_points_relationship(self, clean_session) -> None:
        """Test one-to-many relationship from source to data points."""
        from raglite.external_data.orm_models import ExternalDataPointORM, ExternalDataSourceORM

        # Create source with data points
        source = ExternalDataSourceORM(
            source_name="INE_Test_Relationship",
            data_type="time_series",
        )
        clean_session.add(source)
        clean_session.flush()

        # Add data points
        for i in range(3):
            point = ExternalDataPointORM(
                source_id=source.id,
                date=date(2024, 1 + i, 15),
                metric_name=f"metric_{i}",
                value=Decimal(str(100 + i)),
            )
            clean_session.add(point)
        clean_session.flush()

        # Access through relationship
        assert len(source.data_points) == 3

    def test_data_point_to_source_relationship(self, clean_session) -> None:
        """Test many-to-one relationship from data point to source."""
        from raglite.external_data.orm_models import ExternalDataPointORM, ExternalDataSourceORM

        # Create source
        source = ExternalDataSourceORM(
            source_name="INE_Test_BackRef",
            data_type="time_series",
        )
        clean_session.add(source)
        clean_session.flush()

        # Create data point
        point = ExternalDataPointORM(
            source_id=source.id,
            date=date(2024, 1, 15),
            metric_name="test",
            value=Decimal("100"),
        )
        clean_session.add(point)
        clean_session.flush()

        # Access source through relationship
        assert point.source.source_name == "INE_Test_BackRef"


class TestIndexUsage:
    """Tests for index usage in queries."""

    def test_query_uses_source_date_index(self, clean_session) -> None:
        """Test that date range queries can use the source_date index."""
        from raglite.external_data.orm_models import ExternalDataPointORM, ExternalDataSourceORM

        # Create source with many data points
        source = ExternalDataSourceORM(
            source_name="INE_Test_IndexUsage",
            data_type="time_series",
        )
        clean_session.add(source)
        clean_session.flush()

        for i in range(10):
            point = ExternalDataPointORM(
                source_id=source.id,
                date=date(2024, 1, i + 1),
                metric_name="test",
                value=Decimal(str(100 + i)),
            )
            clean_session.add(point)
        clean_session.flush()

        # Query that should use idx_data_points_source_date
        points = (
            clean_session.query(ExternalDataPointORM)
            .filter(
                ExternalDataPointORM.source_id == source.id,
                ExternalDataPointORM.date >= date(2024, 1, 5),
            )
            .all()
        )

        # Verify query works (index usage is tested at DB level with EXPLAIN)
        assert len(points) == 6
