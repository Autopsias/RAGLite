"""Metadata handling for external data storage.

Story 8.2: External Data Client Refactoring - Metadata Operations Module
"""

from __future__ import annotations

from datetime import UTC, timedelta
from typing import TYPE_CHECKING

from raglite.external_data.storage.constants import FRESHNESS_THRESHOLDS
from raglite.external_data.storage.core import get_source, list_sources
from raglite.shared.database import utc_now

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def is_source_fresh(
    session: Session,
    source_name: str,
    custom_threshold: timedelta | None = None,
) -> bool:
    """Check if a data source is fresh (recently updated).

    Args:
        session: SQLAlchemy session for database operations
        source_name: Source identifier to check
        custom_threshold: Optional custom staleness threshold (overrides frequency-based)

    Returns:
        True if data is fresh, False if stale or never refreshed

    Raises:
        ValueError: If source_name does not exist
    """
    source = get_source(session, source_name)
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


def get_source_freshness(session: Session, source_name: str) -> dict:
    """Get detailed freshness information for a source.

    Args:
        session: SQLAlchemy session for database operations
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
    source = get_source(session, source_name)
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
    session: Session,
    include_deleted: bool = False,
) -> dict:
    """Generate a freshness report for all data sources.

    Args:
        session: SQLAlchemy session for database operations
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
    sources = list_sources(session, include_deleted=include_deleted)
    now = utc_now()

    fresh_count = 0
    stale_count = 0
    never_refreshed = 0
    source_details = []

    for source in sources:
        try:
            details = get_source_freshness(session, source.source_name)
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


def get_stale_sources(session: Session) -> list[dict]:
    """Get list of stale data sources requiring refresh.

    Args:
        session: SQLAlchemy session for database operations

    Returns:
        List of freshness details for stale sources only,
        sorted by staleness (most stale first)
    """
    report = get_freshness_report(session)
    stale = [s for s in report["sources"] if not s["is_fresh"]]

    # Sort by age (most stale first), handling None age
    stale.sort(
        key=lambda x: x["age_seconds"] if x["age_seconds"] is not None else float("inf"),
        reverse=True,
    )

    return stale
