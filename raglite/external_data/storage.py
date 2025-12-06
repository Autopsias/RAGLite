"""External data storage utilities.

Story 6.2: PostgreSQL External Data Schema & Storage (AC4)

Provides ExternalDataStorage class for CRUD operations on external data.
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import update
from sqlalchemy.exc import IntegrityError

from raglite.external_data.orm_models import ExternalDataPointORM, ExternalDataSourceORM
from raglite.shared.database import utc_now

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class ExternalDataStorage:
    """Utility for storing and querying external data in PostgreSQL.

    Provides methods for:
    - Creating and managing external data sources
    - Bulk inserting data points
    - Querying data by source, date range, and metric
    - Soft delete operations

    Example:
        >>> from raglite.shared.database import get_session
        >>> from raglite.external_data.storage import ExternalDataStorage
        >>>
        >>> session = get_session()
        >>> storage = ExternalDataStorage(session)
        >>>
        >>> # Create a data source
        >>> source = storage.create_source(
        ...     source_name="INE_BuildingPermits",
        ...     api_endpoint="https://ine.pt/api",
        ...     data_type="time_series",
        ...     refresh_frequency="monthly"
        ... )
        >>>
        >>> # Insert data points
        >>> data = [
        ...     {"date": date(2024, 1, 1), "metric_name": "permits", "value": 1234, "unit": "count"},
        ...     {"date": date(2024, 2, 1), "metric_name": "permits", "value": 1456, "unit": "count"},
        ... ]
        >>> count = storage.insert_data_points("INE_BuildingPermits", data)
    """

    def __init__(self, session: Session) -> None:
        """Initialize storage with database session.

        Args:
            session: SQLAlchemy session for database operations
        """
        self.session = session

    def create_source(
        self,
        source_name: str,
        api_endpoint: str | None = None,
        data_type: str | None = None,
        refresh_frequency: str | None = None,
        metadata: dict | None = None,
    ) -> ExternalDataSourceORM:
        """Create a new external data source.

        Args:
            source_name: Unique identifier for the source (e.g., "INE_BuildingPermits")
            api_endpoint: API endpoint URL (optional)
            data_type: Type of data (e.g., "time_series", "index")
            refresh_frequency: How often data is updated (e.g., "daily", "monthly")
            metadata: Additional source-specific metadata (optional)

        Returns:
            Created ExternalDataSourceORM instance

        Raises:
            IntegrityError: If source_name already exists
        """
        source = ExternalDataSourceORM(
            source_name=source_name,
            api_endpoint=api_endpoint,
            data_type=data_type,
            refresh_frequency=refresh_frequency,
            metadata_=metadata or {},
        )
        self.session.add(source)
        self.session.commit()
        self.session.refresh(source)
        return source

    def get_source(self, source_name: str) -> ExternalDataSourceORM | None:
        """Get an external data source by name.

        Args:
            source_name: Source identifier to look up

        Returns:
            ExternalDataSourceORM if found and not deleted, None otherwise
        """
        result: ExternalDataSourceORM | None = (
            self.session.query(ExternalDataSourceORM)
            .filter(
                ExternalDataSourceORM.source_name == source_name,
                ExternalDataSourceORM.deleted_at.is_(None),
            )
            .first()
        )
        return result

    def get_or_create_source(
        self,
        source_name: str,
        api_endpoint: str | None = None,
        data_type: str | None = None,
        refresh_frequency: str | None = None,
        metadata: dict | None = None,
    ) -> tuple[ExternalDataSourceORM, bool]:
        """Get existing source or create new one.

        Args:
            source_name: Unique identifier for the source
            api_endpoint: API endpoint URL (used only if creating)
            data_type: Type of data (used only if creating)
            refresh_frequency: Update frequency (used only if creating)
            metadata: Additional metadata (used only if creating)

        Returns:
            Tuple of (source, created) where created is True if new source was created
        """
        source = self.get_source(source_name)
        if source:
            return source, False

        try:
            source = self.create_source(
                source_name=source_name,
                api_endpoint=api_endpoint,
                data_type=data_type,
                refresh_frequency=refresh_frequency,
                metadata=metadata,
            )
            return source, True
        except IntegrityError:
            # Race condition - source was created by another process
            self.session.rollback()
            source = self.get_source(source_name)
            if source:
                return source, False
            raise

    def insert_data_points(
        self,
        source_name: str,
        data_points: list[dict],
        upsert: bool = False,
    ) -> int:
        """Bulk insert data points for a source.

        Args:
            source_name: Source identifier to insert data for
            data_points: List of dicts with keys: date, metric_name, value, unit (optional), metadata (optional)
            upsert: If True, update existing records on conflict (default: False)

        Returns:
            Number of data points inserted/updated

        Raises:
            ValueError: If source_name does not exist
            IntegrityError: If duplicate (source_id, date, metric_name) and upsert=False

        Example:
            >>> data = [
            ...     {"date": date(2024, 1, 1), "metric_name": "permits", "value": 1234},
            ...     {"date": date(2024, 2, 1), "metric_name": "permits", "value": 1456},
            ... ]
            >>> storage.insert_data_points("INE_BuildingPermits", data)
            2
        """
        source = self.get_source(source_name)
        if not source:
            raise ValueError(f"Source '{source_name}' not found")

        if not data_points:
            return 0

        count = 0
        for dp in data_points:
            point = ExternalDataPointORM(
                source_id=source.id,
                date=dp["date"],
                metric_name=dp["metric_name"],
                value=dp["value"],
                unit=dp.get("unit"),
                metadata_=dp.get("metadata", {}),
            )

            if upsert:
                # Check if exists and update
                existing = (
                    self.session.query(ExternalDataPointORM)
                    .filter(
                        ExternalDataPointORM.source_id == source.id,
                        ExternalDataPointORM.date == dp["date"],
                        ExternalDataPointORM.metric_name == dp["metric_name"],
                    )
                    .first()
                )
                if existing:
                    existing.value = dp["value"]
                    existing.unit = dp.get("unit")
                    existing.metadata_ = dp.get("metadata", {})
                    existing.deleted_at = None  # Restore if soft deleted
                    count += 1
                    continue

            self.session.add(point)
            count += 1

        self.session.commit()

        # Update last_refresh timestamp
        self.session.execute(
            update(ExternalDataSourceORM)
            .where(ExternalDataSourceORM.id == source.id)
            .values(last_refresh_at=utc_now())
        )
        self.session.commit()

        return count

    def query_data_range(
        self,
        source_name: str,
        start_date: date,
        end_date: date,
        metric_name: str | None = None,
    ) -> list[ExternalDataPointORM]:
        """Query data points for a date range.

        Args:
            source_name: Source identifier to query
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)
            metric_name: Optional filter by specific metric

        Returns:
            List of ExternalDataPointORM matching the criteria, ordered by date

        Raises:
            ValueError: If source_name does not exist
        """
        source = self.get_source(source_name)
        if not source:
            raise ValueError(f"Source '{source_name}' not found")

        query = self.session.query(ExternalDataPointORM).filter(
            ExternalDataPointORM.source_id == source.id,
            ExternalDataPointORM.date >= start_date,
            ExternalDataPointORM.date <= end_date,
            ExternalDataPointORM.deleted_at.is_(None),
        )

        if metric_name:
            query = query.filter(ExternalDataPointORM.metric_name == metric_name)

        results: list[ExternalDataPointORM] = query.order_by(ExternalDataPointORM.date).all()
        return results

    def query_latest(
        self,
        source_name: str,
        metric_name: str | None = None,
        limit: int = 1,
    ) -> list[ExternalDataPointORM]:
        """Query the most recent data points.

        Args:
            source_name: Source identifier to query
            metric_name: Optional filter by specific metric
            limit: Maximum number of results (default: 1)

        Returns:
            List of most recent ExternalDataPointORM, ordered by date descending
        """
        source = self.get_source(source_name)
        if not source:
            raise ValueError(f"Source '{source_name}' not found")

        query = self.session.query(ExternalDataPointORM).filter(
            ExternalDataPointORM.source_id == source.id,
            ExternalDataPointORM.deleted_at.is_(None),
        )

        if metric_name:
            query = query.filter(ExternalDataPointORM.metric_name == metric_name)

        results: list[ExternalDataPointORM] = (
            query.order_by(ExternalDataPointORM.date.desc()).limit(limit).all()
        )
        return results

    def soft_delete_source(self, source_name: str) -> bool:
        """Soft delete a data source and all its data points.

        Args:
            source_name: Source identifier to delete

        Returns:
            True if source was deleted, False if not found
        """
        source = self.get_source(source_name)
        if not source:
            return False

        now = utc_now()

        # Soft delete all data points
        self.session.execute(
            update(ExternalDataPointORM)
            .where(
                ExternalDataPointORM.source_id == source.id,
                ExternalDataPointORM.deleted_at.is_(None),
            )
            .values(deleted_at=now)
        )

        # Soft delete the source
        source.deleted_at = now
        self.session.commit()

        return True

    def list_sources(self, include_deleted: bool = False) -> list[ExternalDataSourceORM]:
        """List all data sources.

        Args:
            include_deleted: If True, include soft-deleted sources

        Returns:
            List of ExternalDataSourceORM
        """
        query = self.session.query(ExternalDataSourceORM)

        if not include_deleted:
            query = query.filter(ExternalDataSourceORM.deleted_at.is_(None))

        results: list[ExternalDataSourceORM] = query.order_by(
            ExternalDataSourceORM.source_name
        ).all()
        return results

    def get_metrics_for_source(self, source_name: str) -> list[str]:
        """Get all unique metric names for a source.

        Args:
            source_name: Source identifier

        Returns:
            List of unique metric names

        Raises:
            ValueError: If source_name does not exist
        """
        source = self.get_source(source_name)
        if not source:
            raise ValueError(f"Source '{source_name}' not found")

        results = (
            self.session.query(ExternalDataPointORM.metric_name)
            .filter(
                ExternalDataPointORM.source_id == source.id,
                ExternalDataPointORM.deleted_at.is_(None),
            )
            .distinct()
            .all()
        )

        return [r[0] for r in results]
