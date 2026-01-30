"""Automatic quality normalization after document ingestion.

Phase 5C: Implements post-ingestion quality normalization to reduce manual
intervention for data quality issues like:
- Unit standardization (consolidate 444 variants to ~20 canonical units)
- Scale validation (detect kEUR vs M EUR mixing)
- Pattern cleanup (CR/LF, malformed values)

This module provides:
- AutoQualityNormalizer: Per-document normalizer for post-ingestion hook
- normalize_document(): Convenience function for single document
- normalize_all(): Batch normalization for entire database

Usage:
    # Single document (after ingestion)
    from raglite.ingestion.quality_normalizer import normalize_document
    report = normalize_document(document_id="uuid-here")

    # Batch normalization
    from raglite.ingestion.quality_normalizer import normalize_all
    report = normalize_all()
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from raglite.shared.logging import get_logger

if TYPE_CHECKING:
    from psycopg2.extensions import connection as PgConnection
    from psycopg2.extensions import cursor as PgCursor

logger = get_logger(__name__)


# Canonical unit mappings - consolidate variants to standard forms
UNIT_NORMALIZATION_MAP: dict[str, str] = {
    # EUR variants -> standard EUR units
    "EUR": "EUR",
    "€": "EUR",
    "euro": "EUR",
    "euros": "EUR",
    "Euros": "EUR",
    # kEUR variants
    "kEUR": "kEUR",
    "K EUR": "kEUR",
    "1000 EUR": "kEUR",
    "1,000 EUR": "kEUR",
    "thousand EUR": "kEUR",
    "'000 EUR": "kEUR",
    # M EUR variants
    "M EUR": "M EUR",
    "MEUR": "M EUR",
    "M€": "M EUR",
    "EUR M": "M EUR",
    "EUR millions": "M EUR",
    "million EUR": "M EUR",
    "millions EUR": "M EUR",
    # Percentage variants
    "%": "%",
    "percent": "%",
    "pct": "%",
    "percentage": "%",
    "p.p.": "p.p.",  # Percentage points kept separate
    # Volume units
    "kton": "kton",
    "kt": "kton",
    "kT": "kton",
    "thousand tons": "kton",
    "tons": "ton",
    "ton": "ton",
    "t": "ton",
    "m³": "m³",
    "m3": "m³",
    "cubic meters": "m³",
    # Energy units
    "MWh": "MWh",
    "mwh": "MWh",
    "kWh": "kWh",
    "kwh": "kWh",
    "GJ": "GJ",
    "gj": "GJ",
    # Per-unit rates
    "EUR/ton": "EUR/ton",
    "€/ton": "EUR/ton",
    "EUR/t": "EUR/ton",
    "EUR/m³": "EUR/m³",
    "€/m³": "EUR/m³",
    "EUR/MWh": "EUR/MWh",
    "€/MWh": "EUR/MWh",
}

# Patterns that indicate contaminated units (entity names in unit field)
CONTAMINATED_UNIT_PATTERNS = [
    "GROUP",
    "ANGOLA",
    "TUNISIA",
    "LEBANON",
    "PORTUGAL",
    "BRAZIL",
    "N/A",
    "NULL",
    "-",
    "",
]


@dataclass
class QualityReport:
    """Report from quality normalization run."""

    document_id: str | None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    # Unit normalization
    units_standardized: int = 0
    units_inferred: int = 0
    contaminated_units_cleaned: int = 0

    # Scale validation
    scale_issues_found: int = 0
    scale_issues_fixed: int = 0

    # Pattern cleanup
    patterns_cleaned: int = 0

    # Summary
    total_rows_processed: int = 0
    critical_issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def summary(self) -> str:
        """Get summary string."""
        return (
            f"Processed {self.total_rows_processed} rows: "
            f"{self.units_standardized} units standardized, "
            f"{self.scale_issues_fixed} scale issues fixed, "
            f"{len(self.critical_issues)} critical issues"
        )


class AutoQualityNormalizer:
    """Automatic quality normalization for ingested documents.

    Runs post-ingestion to standardize units, validate scales, and clean patterns.
    Can be used for single documents or batch processing.
    """

    def __init__(self, conn: PgConnection | None = None):
        """Initialize normalizer.

        Args:
            conn: PostgreSQL connection. If None, will create one when needed.
        """
        self._conn = conn
        self._cursor: PgCursor | None = None

    def _get_connection(self) -> PgConnection:
        """Get or create PostgreSQL connection."""
        if self._conn is None:
            from raglite.shared.clients import get_postgresql_connection

            self._conn = get_postgresql_connection()
        return self._conn

    def _get_cursor(self) -> PgCursor:
        """Get cursor for operations."""
        if self._cursor is None:
            self._cursor = self._get_connection().cursor()
        return self._cursor

    def normalize_document(self, document_id: str) -> QualityReport:
        """Normalize quality for a single document.

        Args:
            document_id: UUID of the document to normalize

        Returns:
            QualityReport with normalization statistics
        """
        report = QualityReport(document_id=document_id)
        cursor = self._get_cursor()
        conn = self._get_connection()

        logger.info(
            "Starting quality normalization for document",
            extra={"document_id": document_id},
        )

        # 1. Standardize units
        report.units_standardized = self._standardize_units(cursor, conn, document_id)

        # 2. Clean contaminated units
        report.contaminated_units_cleaned = self._clean_contaminated_units(
            cursor, conn, document_id
        )

        # 3. Validate scales
        scale_result = self._validate_scales(cursor, document_id)
        report.scale_issues_found = scale_result["issues_found"]
        report.warnings.extend(scale_result["warnings"])

        # 4. Cleanup patterns (CR/LF, etc.)
        report.patterns_cleaned = self._cleanup_patterns(cursor, conn, document_id)

        # Get total rows
        cursor.execute(
            "SELECT COUNT(*) FROM financial_tables WHERE document_id = %s",
            (document_id,),
        )
        report.total_rows_processed = cursor.fetchone()[0]

        logger.info(
            "Quality normalization complete",
            extra={
                "document_id": document_id,
                "units_standardized": report.units_standardized,
                "contaminated_cleaned": report.contaminated_units_cleaned,
                "scale_issues": report.scale_issues_found,
                "patterns_cleaned": report.patterns_cleaned,
            },
        )

        return report

    def normalize_all(self, dry_run: bool = False) -> QualityReport:
        """Normalize quality for entire database.

        Args:
            dry_run: If True, count changes but don't apply them

        Returns:
            QualityReport with normalization statistics
        """
        report = QualityReport(document_id=None)
        cursor = self._get_cursor()
        conn = self._get_connection()

        logger.info("Starting batch quality normalization", extra={"dry_run": dry_run})

        # 1. Standardize units (all documents)
        report.units_standardized = self._standardize_units(cursor, conn, dry_run=dry_run)

        # 2. Clean contaminated units
        report.contaminated_units_cleaned = self._clean_contaminated_units(
            cursor, conn, dry_run=dry_run
        )

        # 3. Validate scales
        scale_result = self._validate_scales(cursor)
        report.scale_issues_found = scale_result["issues_found"]
        report.warnings.extend(scale_result["warnings"])

        # 4. Cleanup patterns
        report.patterns_cleaned = self._cleanup_patterns(cursor, conn, dry_run=dry_run)

        # Get total rows
        cursor.execute("SELECT COUNT(*) FROM financial_tables")
        report.total_rows_processed = cursor.fetchone()[0]

        logger.info(
            "Batch quality normalization complete",
            extra={
                "dry_run": dry_run,
                "units_standardized": report.units_standardized,
                "contaminated_cleaned": report.contaminated_units_cleaned,
                "scale_issues": report.scale_issues_found,
                "patterns_cleaned": report.patterns_cleaned,
            },
        )

        return report

    def _standardize_units(
        self,
        cursor: PgCursor,
        conn: PgConnection,
        document_id: str | None = None,
        dry_run: bool = False,
    ) -> int:
        """Standardize unit variants to canonical forms.

        Args:
            cursor: Database cursor
            conn: Database connection
            document_id: Optional document to filter
            dry_run: If True, count only

        Returns:
            Number of rows updated
        """
        total_updated = 0

        # Build document filter
        doc_filter = "AND document_id = %s" if document_id else ""

        for variant, canonical in UNIT_NORMALIZATION_MAP.items():
            if variant == canonical:
                continue  # Already canonical

            if dry_run:
                cursor.execute(
                    f"""
                    SELECT COUNT(*) FROM financial_tables
                    WHERE unit = %s {doc_filter}
                """,
                    (variant, document_id) if document_id else (variant,),
                )
                count = cursor.fetchone()[0]
            else:
                cursor.execute(
                    f"""
                    UPDATE financial_tables
                    SET unit = %s,
                        unit_original = COALESCE(unit_original, unit),
                        unit_inferred = TRUE,
                        unit_inference_method = 'auto_quality_standardization'
                    WHERE unit = %s {doc_filter}
                """,
                    (canonical, variant, document_id) if document_id else (canonical, variant),
                )
                count = cursor.rowcount
                if count > 0:
                    conn.commit()

            total_updated += count

        return total_updated

    def _clean_contaminated_units(
        self,
        cursor: PgCursor,
        conn: PgConnection,
        document_id: str | None = None,
        dry_run: bool = False,
    ) -> int:
        """Clean contaminated units (entity names in unit field).

        Args:
            cursor: Database cursor
            conn: Database connection
            document_id: Optional document to filter
            dry_run: If True, count only

        Returns:
            Number of rows cleaned
        """
        doc_filter = "AND document_id = %s" if document_id else ""
        patterns = CONTAMINATED_UNIT_PATTERNS

        # Build pattern list for IN clause
        placeholders = ", ".join(["%s"] * len(patterns))

        if dry_run:
            cursor.execute(
                f"""
                SELECT COUNT(*) FROM financial_tables
                WHERE unit IN ({placeholders}) {doc_filter}
            """,
                (*patterns, document_id) if document_id else patterns,
            )
            return cursor.fetchone()[0]

        cursor.execute(
            f"""
            UPDATE financial_tables
            SET unit = NULL,
                unit_original = COALESCE(unit_original, unit),
                unit_inferred = FALSE,
                unit_inference_method = 'contamination_cleanup'
            WHERE unit IN ({placeholders}) {doc_filter}
        """,
            (*patterns, document_id) if document_id else patterns,
        )
        count = cursor.rowcount
        if count > 0:
            conn.commit()

        return count

    def _validate_scales(self, cursor: PgCursor, document_id: str | None = None) -> dict:
        """Validate scales to detect unit mixing.

        Args:
            cursor: Database cursor
            document_id: Optional document to filter

        Returns:
            Dict with 'issues_found' count and 'warnings' list
        """
        result = {"issues_found": 0, "warnings": []}
        doc_filter = "AND document_id = %s" if document_id else ""

        # Check for EBITDA scale issues (kEUR vs M EUR mixing)
        if document_id:
            cursor.execute(
                f"""
                SELECT
                    metric,
                    MAX(value) / NULLIF(MIN(NULLIF(value, 0)), 0) as swing,
                    MIN(value) as min_val,
                    MAX(value) as max_val
                FROM financial_tables
                WHERE LOWER(metric) LIKE '%ebitda%'
                  AND metric NOT LIKE '%Margin%'
                  AND value > 0
                  {doc_filter}
                GROUP BY metric
                HAVING MAX(value) / NULLIF(MIN(NULLIF(value, 0)), 0) > 10
            """,
                (document_id,),
            )
        else:
            cursor.execute(
                """
                SELECT
                    metric,
                    MAX(value) / NULLIF(MIN(NULLIF(value, 0)), 0) as swing,
                    MIN(value) as min_val,
                    MAX(value) as max_val
                FROM financial_tables
                WHERE LOWER(metric) LIKE '%ebitda%'
                  AND metric NOT LIKE '%Margin%'
                  AND value > 0
                GROUP BY metric
                HAVING MAX(value) / NULLIF(MIN(NULLIF(value, 0)), 0) > 10
            """
            )

        for metric, swing, min_val, max_val in cursor.fetchall():
            result["issues_found"] += 1
            result["warnings"].append(
                f"High swing detected for {metric}: {swing:.1f}x "
                f"(range: {min_val:,.0f} to {max_val:,.0f}). "
                "Possible kEUR/M EUR mixing."
            )

        return result

    def _cleanup_patterns(
        self,
        cursor: PgCursor,
        conn: PgConnection,
        document_id: str | None = None,
        dry_run: bool = False,
    ) -> int:
        """Cleanup malformed patterns in metric/unit fields.

        Args:
            cursor: Database cursor
            conn: Database connection
            document_id: Optional document to filter
            dry_run: If True, count only

        Returns:
            Number of rows cleaned
        """
        doc_filter = "AND document_id = %s" if document_id else ""
        total_cleaned = 0

        # Helper to execute queries with optional document_id filter
        def exec_with_doc_filter(sql_template: str, params: tuple | None = None) -> None:
            """Execute SQL with optional document_id parameter."""
            if document_id:
                cursor.execute(sql_template.format(doc_filter=doc_filter), (document_id,))
            else:
                cursor.execute(sql_template.format(doc_filter=""))

        # 1. Remove CR/LF from metric names
        if dry_run:
            exec_with_doc_filter(
                """
                SELECT COUNT(*) FROM financial_tables
                WHERE metric ~ E'[\\r\\n]' {doc_filter}
            """
            )
            count = cursor.fetchone()[0]
        else:
            exec_with_doc_filter(
                """
                UPDATE financial_tables
                SET metric = REGEXP_REPLACE(metric, E'[\\r\\n]+', ' ', 'g')
                WHERE metric ~ E'[\\r\\n]' {doc_filter}
            """
            )
            count = cursor.rowcount
            if count > 0:
                conn.commit()
        total_cleaned += count

        # 2. Trim whitespace from metric names
        if dry_run:
            exec_with_doc_filter(
                """
                SELECT COUNT(*) FROM financial_tables
                WHERE metric != TRIM(metric) {doc_filter}
            """
            )
            count = cursor.fetchone()[0]
        else:
            exec_with_doc_filter(
                """
                UPDATE financial_tables
                SET metric = TRIM(metric)
                WHERE metric != TRIM(metric) {doc_filter}
            """
            )
            count = cursor.rowcount
            if count > 0:
                conn.commit()
        total_cleaned += count

        # 3. Trim whitespace from units
        if dry_run:
            exec_with_doc_filter(
                """
                SELECT COUNT(*) FROM financial_tables
                WHERE unit IS NOT NULL AND unit != TRIM(unit) {doc_filter}
            """
            )
            count = cursor.fetchone()[0]
        else:
            exec_with_doc_filter(
                """
                UPDATE financial_tables
                SET unit = TRIM(unit)
                WHERE unit IS NOT NULL AND unit != TRIM(unit) {doc_filter}
            """
            )
            count = cursor.rowcount
            if count > 0:
                conn.commit()
        total_cleaned += count

        return total_cleaned


# Convenience functions for direct use
def normalize_document(document_id: str) -> QualityReport:
    """Normalize quality for a single document.

    Args:
        document_id: UUID of the document to normalize

    Returns:
        QualityReport with normalization statistics
    """
    normalizer = AutoQualityNormalizer()
    return normalizer.normalize_document(document_id)


def normalize_all(dry_run: bool = False) -> QualityReport:
    """Normalize quality for entire database.

    Args:
        dry_run: If True, count changes but don't apply them

    Returns:
        QualityReport with normalization statistics
    """
    normalizer = AutoQualityNormalizer()
    return normalizer.normalize_all(dry_run=dry_run)
