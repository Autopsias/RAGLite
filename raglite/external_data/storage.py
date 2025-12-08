"""External data storage utilities.

Story 6.2: PostgreSQL External Data Schema & Storage (AC4)
Story 6.9: External Data Source Client Fixes - Freshness Tracking

Provides ExternalDataStorage class for CRUD operations on external data.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import update
from sqlalchemy.exc import IntegrityError

from raglite.external_data.orm_models import ExternalDataPointORM, ExternalDataSourceORM
from raglite.shared.database import utc_now
from raglite.shared.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = get_logger(__name__)

# Freshness thresholds by refresh frequency
FRESHNESS_THRESHOLDS: dict[str, timedelta] = {
    "hourly": timedelta(hours=2),
    "daily": timedelta(days=2),
    "weekly": timedelta(days=10),
    "monthly": timedelta(days=45),
    "quarterly": timedelta(days=120),
    "annual": timedelta(days=400),
}


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
                    unit_value = dp.get("unit")
                    existing.unit = unit_value if unit_value is not None else existing.unit
                    existing.metadata_ = dp.get("metadata", {})
                    existing.deleted_at = None  # type: ignore[assignment]
                    count += 1
                    continue

            self.session.add(point)
            count += 1

        self.session.commit()

        # Update last_refresh timestamp
        stmt = (
            update(ExternalDataSourceORM)
            .where(ExternalDataSourceORM.id == source.id)
            .values(last_refresh_at=utc_now())
        )
        self.session.execute(stmt)
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
        stmt = (
            update(ExternalDataPointORM)
            .where(
                ExternalDataPointORM.source_id == source.id,
                ExternalDataPointORM.deleted_at.is_(None),
            )
            .values(deleted_at=now)
        )
        self.session.execute(stmt)

        # Soft delete the source
        source.deleted_at = now  # type: ignore[assignment]
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

    # =========================================================================
    # Data Freshness Tracking (Story 6.9)
    # =========================================================================

    def is_source_fresh(
        self,
        source_name: str,
        custom_threshold: timedelta | None = None,
    ) -> bool:
        """Check if a data source is fresh (recently updated).

        Args:
            source_name: Source identifier to check
            custom_threshold: Optional custom staleness threshold (overrides frequency-based)

        Returns:
            True if data is fresh, False if stale or never refreshed

        Raises:
            ValueError: If source_name does not exist
        """
        source = self.get_source(source_name)
        if not source:
            raise ValueError(f"Source '{source_name}' not found")

        if source.last_refresh_at is None:
            return False  # Never refreshed

        now = utc_now()
        last_refresh = source.last_refresh_at

        # Make last_refresh timezone-aware if needed
        if last_refresh.tzinfo is None:
            last_refresh = last_refresh.replace(tzinfo=UTC)

        # Determine threshold
        if custom_threshold:
            threshold = custom_threshold
        else:
            freq = source.refresh_frequency or "daily"
            threshold = FRESHNESS_THRESHOLDS.get(freq, timedelta(days=2))

        age = now - last_refresh
        return age <= threshold

    def get_source_freshness(self, source_name: str) -> dict:
        """Get detailed freshness information for a source.

        Args:
            source_name: Source identifier

        Returns:
            Dict with freshness details:
            - source_name: Source identifier
            - is_fresh: Boolean indicating freshness
            - last_refresh_at: Last refresh timestamp (ISO format or None)
            - age_seconds: Seconds since last refresh (or None)
            - age_human: Human-readable age string
            - refresh_frequency: Expected refresh frequency
            - threshold_seconds: Staleness threshold in seconds
            - next_refresh_due: When next refresh is expected (ISO format)

        Raises:
            ValueError: If source_name does not exist
        """
        source = self.get_source(source_name)
        if not source:
            raise ValueError(f"Source '{source_name}' not found")

        freq = source.refresh_frequency or "daily"
        threshold = FRESHNESS_THRESHOLDS.get(freq, timedelta(days=2))
        now = utc_now()

        if source.last_refresh_at is None:
            return {
                "source_name": source_name,
                "is_fresh": False,
                "last_refresh_at": None,
                "age_seconds": None,
                "age_human": "never refreshed",
                "refresh_frequency": freq,
                "threshold_seconds": int(threshold.total_seconds()),
                "next_refresh_due": "immediately",
            }

        last_refresh = source.last_refresh_at
        if last_refresh.tzinfo is None:
            last_refresh = last_refresh.replace(tzinfo=UTC)

        age = now - last_refresh
        is_fresh = age <= threshold

        # Human-readable age
        age_seconds = int(age.total_seconds())
        if age_seconds < 60:
            age_human = f"{age_seconds} seconds ago"
        elif age_seconds < 3600:
            age_human = f"{age_seconds // 60} minutes ago"
        elif age_seconds < 86400:
            age_human = f"{age_seconds // 3600} hours ago"
        else:
            age_human = f"{age_seconds // 86400} days ago"

        # Next refresh due
        next_due = last_refresh + threshold
        next_due_str = next_due.isoformat() if next_due > now else "overdue"

        return {
            "source_name": source_name,
            "is_fresh": is_fresh,
            "last_refresh_at": last_refresh.isoformat(),
            "age_seconds": age_seconds,
            "age_human": age_human,
            "refresh_frequency": freq,
            "threshold_seconds": int(threshold.total_seconds()),
            "next_refresh_due": next_due_str,
        }

    def get_freshness_report(
        self,
        include_deleted: bool = False,
    ) -> dict:
        """Generate a freshness report for all data sources.

        Args:
            include_deleted: If True, include soft-deleted sources

        Returns:
            Dict with:
            - generated_at: Report generation timestamp
            - total_sources: Total number of sources
            - fresh_count: Number of fresh sources
            - stale_count: Number of stale sources
            - never_refreshed_count: Sources never refreshed
            - sources: List of per-source freshness details
        """
        sources = self.list_sources(include_deleted=include_deleted)
        now = utc_now()

        fresh_count = 0
        stale_count = 0
        never_refreshed = 0
        source_details = []

        for source in sources:
            try:
                details = self.get_source_freshness(source.source_name)
                source_details.append(details)

                if details["last_refresh_at"] is None:
                    never_refreshed += 1
                elif details["is_fresh"]:
                    fresh_count += 1
                else:
                    stale_count += 1

            except ValueError:
                continue

        return {
            "generated_at": now.isoformat(),
            "total_sources": len(sources),
            "fresh_count": fresh_count,
            "stale_count": stale_count,
            "never_refreshed_count": never_refreshed,
            "sources": source_details,
        }

    def get_stale_sources(self) -> list[dict]:
        """Get list of stale data sources requiring refresh.

        Returns:
            List of freshness details for stale sources only,
            sorted by staleness (most stale first)
        """
        report = self.get_freshness_report()
        stale = [s for s in report["sources"] if not s["is_fresh"]]

        # Sort by age (most stale first), handling None age
        stale.sort(
            key=lambda x: x["age_seconds"] if x["age_seconds"] is not None else float("inf"),
            reverse=True,
        )

        return stale

    def update_last_refresh(
        self,
        source_name: str,
        refresh_time: datetime | None = None,
    ) -> bool:
        """Update the last_refresh_at timestamp for a source.

        Args:
            source_name: Source identifier
            refresh_time: Timestamp to set (default: now)

        Returns:
            True if updated, False if source not found
        """
        source = self.get_source(source_name)
        if not source:
            return False

        refresh_time = refresh_time or utc_now()

        stmt = (
            update(ExternalDataSourceORM)
            .where(ExternalDataSourceORM.id == source.id)
            .values(last_refresh_at=refresh_time)
        )
        self.session.execute(stmt)
        self.session.commit()

        logger.info(
            "Updated last_refresh_at for source",
            extra={"source_name": source_name, "refresh_time": refresh_time.isoformat()},
        )
        return True
