#!/usr/bin/env python3
"""Cleanup script for old external data (soft delete).

Story 6.2: PostgreSQL External Data Schema & Storage (AC5)

Implements data retention policy:
- 5 years historical data retention
- Soft deletes records older than retention period
- Can be run via cron/scheduler (monthly)

Usage:
    python scripts/cleanup-old-external-data.py [--dry-run] [--retention-years N]

Examples:
    # Preview what would be deleted (dry run)
    python scripts/cleanup-old-external-data.py --dry-run

    # Delete data older than 5 years (default)
    python scripts/cleanup-old-external-data.py

    # Delete data older than 3 years
    python scripts/cleanup-old-external-data.py --retention-years 3
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path for imports (cross-platform)
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import func, update

from raglite.external_data.orm_models import ExternalDataPointORM, ExternalDataSourceORM
from raglite.shared.database import get_session
from raglite.shared.safety import ProductionProtectionError, SafetyGuard

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Cleanup old external data (soft delete)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be deleted without making changes",
    )
    parser.add_argument(
        "--retention-years",
        type=int,
        default=5,
        help="Number of years to retain data (default: 5)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompt on production",
    )
    return parser.parse_args()


def cleanup_old_data(
    retention_years: int = 5,
    dry_run: bool = False,
) -> tuple[int, int]:
    """Soft delete external data older than retention period.

    Args:
        retention_years: Number of years to retain data
        dry_run: If True, only count records without modifying

    Returns:
        Tuple of (data_points_deleted, sources_deleted)
    """
    session = get_session()
    cutoff_date = datetime.utcnow() - timedelta(days=retention_years * 365)

    logger.info(f"Retention policy: {retention_years} years")
    logger.info(f"Cutoff date: {cutoff_date.date()}")

    try:
        # Count data points to be soft deleted
        points_query = session.query(func.count(ExternalDataPointORM.id)).filter(
            ExternalDataPointORM.date < cutoff_date.date(),
            ExternalDataPointORM.deleted_at.is_(None),
        )
        points_count = points_query.scalar() or 0

        # Count sources with all data points deleted (orphaned)
        # A source is orphaned if ALL its data points are deleted
        session.query(func.count(ExternalDataSourceORM.id)).filter(
            ExternalDataSourceORM.deleted_at.is_(None),
            ~ExternalDataSourceORM.data_points.any(ExternalDataPointORM.deleted_at.is_(None)),
        )
        # For now, we only soft delete data points, not sources
        sources_count = 0

        logger.info(f"Data points to soft delete: {points_count}")
        logger.info(f"Sources to soft delete: {sources_count}")

        if dry_run:
            logger.info("DRY RUN - No changes made")
            session.rollback()
            return points_count, sources_count

        # Perform soft delete on data points
        if points_count > 0:
            stmt = (
                update(ExternalDataPointORM)
                .where(
                    ExternalDataPointORM.date < cutoff_date.date(),
                    ExternalDataPointORM.deleted_at.is_(None),
                )
                .values(deleted_at=datetime.utcnow())
            )
            session.execute(stmt)
            session.commit()
            logger.info(f"Soft deleted {points_count} data points")

        return points_count, sources_count

    except Exception as e:
        session.rollback()
        logger.error(f"Error during cleanup: {e}")
        raise
    finally:
        session.close()


def main() -> int:
    """Main entry point for cleanup script."""
    args = parse_args()

    # Safety check for production
    guard = SafetyGuard()

    if guard.is_production and not args.dry_run and not args.force:
        try:
            confirmed = guard.require_confirmation(
                f"This will soft delete external data older than {args.retention_years} years "
                "from PRODUCTION database."
            )
            if not confirmed:
                logger.info("Operation cancelled by user")
                return 1
        except ProductionProtectionError as e:
            logger.error(str(e))
            return 1

    try:
        points_deleted, sources_deleted = cleanup_old_data(
            retention_years=args.retention_years,
            dry_run=args.dry_run,
        )

        if args.dry_run:
            logger.info(f"DRY RUN complete: Would soft delete {points_deleted} data points")
        else:
            logger.info(f"Cleanup complete: Soft deleted {points_deleted} data points")

        return 0

    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
