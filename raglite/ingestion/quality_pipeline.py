"""Unified quality remediation pipeline.

Phase 5D: Consolidates all fix scripts into an automated pipeline that can run:
- Incrementally: After each document ingestion
- Batch: For full database cleanup

Pipeline Phases:
1. Structural: Empty metrics, entity contamination cleanup
2. Ratio: Ratio metric decomposition (reclassify per-unit metrics)
3. Currency: Currency standardization (kEUR, M EUR)
4. EBITDA Scale: Entity-specific scale normalization
5. Unit Inference: Context-based unit inference for NULL units

Usage:
    # Run full batch pipeline
    from raglite.ingestion.quality_pipeline import QualityRemediationPipeline
    pipeline = QualityRemediationPipeline()
    report = pipeline.run_batch()

    # Run for single document
    report = pipeline.run_incremental(document_id="uuid-here")

    # Run specific phases only
    report = pipeline.run_phases(["structural", "currency"])
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from raglite.shared.logging import get_logger

if TYPE_CHECKING:
    from psycopg2.extensions import connection as PgConnection
    from psycopg2.extensions import cursor as PgCursor

logger = get_logger(__name__)


@dataclass
class PhaseResult:
    """Result from a single pipeline phase."""

    phase_name: str
    rows_affected: int = 0
    success: bool = True
    error: str | None = None
    details: dict = field(default_factory=dict)


@dataclass
class PipelineReport:
    """Report from complete pipeline run."""

    mode: str  # "batch" or "incremental"
    document_id: str | None = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    phases: list[PhaseResult] = field(default_factory=list)
    total_rows_affected: int = 0
    success: bool = True
    errors: list[str] = field(default_factory=list)

    def add_phase(self, result: PhaseResult) -> None:
        """Add phase result to report."""
        self.phases.append(result)
        self.total_rows_affected += result.rows_affected
        if not result.success:
            self.success = False
            if result.error:
                self.errors.append(f"{result.phase_name}: {result.error}")

    @property
    def summary(self) -> str:
        """Get summary string."""
        phase_count = len(self.phases)
        passed = sum(1 for p in self.phases if p.success)
        return (
            f"{self.mode.capitalize()} pipeline: {passed}/{phase_count} phases passed, "
            f"{self.total_rows_affected:,} rows affected"
        )


class PipelinePhase(ABC):
    """Base class for pipeline phases."""

    name: str = "base"

    @abstractmethod
    def run(
        self,
        cursor: PgCursor,
        conn: PgConnection,
        document_id: str | None = None,
        dry_run: bool = False,
    ) -> PhaseResult:
        """Run this phase.

        Args:
            cursor: Database cursor
            conn: Database connection
            document_id: Optional document to filter (incremental mode)
            dry_run: If True, count only

        Returns:
            PhaseResult with phase statistics
        """
        pass


class StructuralCleanupPhase(PipelinePhase):
    """Phase 1: Structural cleanup - empty metrics, entity contamination."""

    name = "structural"

    def run(
        self,
        cursor: PgCursor,
        conn: PgConnection,
        document_id: str | None = None,
        dry_run: bool = False,
    ) -> PhaseResult:
        """Clean structural issues."""
        result = PhaseResult(phase_name=self.name)
        doc_filter = "AND document_id = %s" if document_id else ""

        try:
            # 1. Remove empty metric rows (headers/dividers)
            if dry_run:
                cursor.execute(
                    f"""
                    SELECT COUNT(*) FROM financial_tables
                    WHERE (metric IS NULL OR metric = '') {doc_filter}
                """,
                    (document_id,) if document_id else (),
                )
                empty_count = cursor.fetchone()[0]
            else:
                cursor.execute(
                    f"""
                    DELETE FROM financial_tables
                    WHERE (metric IS NULL OR metric = '') {doc_filter}
                """,
                    (document_id,) if document_id else (),
                )
                empty_count = cursor.rowcount
                conn.commit()

            result.details["empty_metrics_removed"] = empty_count
            result.rows_affected += empty_count

            # 2. Fix entity contamination (metric names in entity field)
            contamination_patterns = [
                "CF from Operations",
                "De(in)crease Trade Working Capital",
                "CF from Operating Activities",
                "Net interest expenses",
            ]
            pattern_list = ", ".join(["%s"] * len(contamination_patterns))

            if dry_run:
                cursor.execute(
                    f"""
                    SELECT COUNT(*) FROM financial_tables
                    WHERE entity_normalized IN ({pattern_list}) {doc_filter}
                """,
                    (*contamination_patterns, document_id)
                    if document_id
                    else contamination_patterns,
                )
                contaminated_count = cursor.fetchone()[0]
            else:
                cursor.execute(
                    f"""
                    UPDATE financial_tables
                    SET entity_normalized = 'Unknown'
                    WHERE entity_normalized IN ({pattern_list}) {doc_filter}
                """,
                    (*contamination_patterns, document_id)
                    if document_id
                    else contamination_patterns,
                )
                contaminated_count = cursor.rowcount
                conn.commit()

            result.details["entity_contamination_fixed"] = contaminated_count
            result.rows_affected += contaminated_count

        except Exception as e:
            result.success = False
            result.error = str(e)
            logger.error(f"Structural cleanup failed: {e}", extra={"document_id": document_id})

        return result


class RatioDecompositionPhase(PipelinePhase):
    """Phase 2: Ratio metric decomposition."""

    name = "ratio"

    def run(
        self,
        cursor: PgCursor,
        conn: PgConnection,
        document_id: str | None = None,
        dry_run: bool = False,
    ) -> PhaseResult:
        """Decompose Ratio metric into actual metric names based on unit context."""
        result = PhaseResult(phase_name=self.name)
        doc_filter = "AND document_id = %s" if document_id else ""

        try:
            # Reclassify 'Ratio' metrics based on unit
            reclassifications = [
                ("EUR/ton", "Price per Ton"),
                ("EUR/m³", "Price per Cubic Meter"),
                ("EUR/MWh", "Energy Cost"),
                ("%", "Percentage Rate"),
            ]

            total = 0
            for unit, new_metric in reclassifications:
                if dry_run:
                    cursor.execute(
                        f"""
                        SELECT COUNT(*) FROM financial_tables
                        WHERE metric = 'Ratio' AND unit = %s {doc_filter}
                    """,
                        (unit, document_id) if document_id else (unit,),
                    )
                    count = cursor.fetchone()[0]
                else:
                    cursor.execute(
                        f"""
                        UPDATE financial_tables
                        SET metric = %s
                        WHERE metric = 'Ratio' AND unit = %s {doc_filter}
                    """,
                        (new_metric, unit, document_id) if document_id else (new_metric, unit),
                    )
                    count = cursor.rowcount
                    if count > 0:
                        conn.commit()

                result.details[f"ratio_to_{unit}"] = count
                total += count

            result.rows_affected = total

        except Exception as e:
            result.success = False
            result.error = str(e)
            logger.error(f"Ratio decomposition failed: {e}")

        return result


class CurrencyCleanupPhase(PipelinePhase):
    """Phase 3: Currency standardization."""

    name = "currency"

    def run(
        self,
        cursor: PgCursor,
        conn: PgConnection,
        document_id: str | None = None,
        dry_run: bool = False,
    ) -> PhaseResult:
        """Standardize currency units."""
        result = PhaseResult(phase_name=self.name)
        doc_filter = "AND document_id = %s" if document_id else ""

        try:
            # Standardize EUR variants
            eur_variants = ["€", "euro", "euros", "Euros"]
            placeholders = ", ".join(["%s"] * len(eur_variants))

            if dry_run:
                cursor.execute(
                    f"""
                    SELECT COUNT(*) FROM financial_tables
                    WHERE unit IN ({placeholders}) {doc_filter}
                """,
                    (*eur_variants, document_id) if document_id else eur_variants,
                )
                count = cursor.fetchone()[0]
            else:
                cursor.execute(
                    f"""
                    UPDATE financial_tables
                    SET unit = 'EUR',
                        unit_original = COALESCE(unit_original, unit)
                    WHERE unit IN ({placeholders}) {doc_filter}
                """,
                    (*eur_variants, document_id) if document_id else eur_variants,
                )
                count = cursor.rowcount
                conn.commit()

            result.details["eur_standardized"] = count
            result.rows_affected += count

            # Standardize kEUR variants
            keur_variants = ["K EUR", "1000 EUR", "1,000 EUR", "thousand EUR", "'000 EUR"]
            placeholders = ", ".join(["%s"] * len(keur_variants))

            if dry_run:
                cursor.execute(
                    f"""
                    SELECT COUNT(*) FROM financial_tables
                    WHERE unit IN ({placeholders}) {doc_filter}
                """,
                    (*keur_variants, document_id) if document_id else keur_variants,
                )
                count = cursor.fetchone()[0]
            else:
                cursor.execute(
                    f"""
                    UPDATE financial_tables
                    SET unit = 'kEUR',
                        unit_original = COALESCE(unit_original, unit)
                    WHERE unit IN ({placeholders}) {doc_filter}
                """,
                    (*keur_variants, document_id) if document_id else keur_variants,
                )
                count = cursor.rowcount
                conn.commit()

            result.details["keur_standardized"] = count
            result.rows_affected += count

            # Standardize M EUR variants
            meur_variants = ["MEUR", "M€", "EUR M", "EUR millions", "million EUR"]
            placeholders = ", ".join(["%s"] * len(meur_variants))

            if dry_run:
                cursor.execute(
                    f"""
                    SELECT COUNT(*) FROM financial_tables
                    WHERE unit IN ({placeholders}) {doc_filter}
                """,
                    (*meur_variants, document_id) if document_id else meur_variants,
                )
                count = cursor.fetchone()[0]
            else:
                cursor.execute(
                    f"""
                    UPDATE financial_tables
                    SET unit = 'M EUR',
                        unit_original = COALESCE(unit_original, unit)
                    WHERE unit IN ({placeholders}) {doc_filter}
                """,
                    (*meur_variants, document_id) if document_id else meur_variants,
                )
                count = cursor.rowcount
                conn.commit()

            result.details["meur_standardized"] = count
            result.rows_affected += count

        except Exception as e:
            result.success = False
            result.error = str(e)
            logger.error(f"Currency cleanup failed: {e}")

        return result


class EBITDAScalePhase(PipelinePhase):
    """Phase 4: EBITDA scale reconciliation."""

    name = "ebitda_scale"

    def run(
        self,
        cursor: PgCursor,
        conn: PgConnection,
        document_id: str | None = None,
        dry_run: bool = False,
    ) -> PhaseResult:
        """Fix EBITDA scale issues (kEUR vs M EUR)."""
        result = PhaseResult(phase_name=self.name)
        doc_filter = "AND document_id = %s" if document_id else ""

        try:
            # Small kEUR values (< 1000) are likely mislabeled M EUR
            if dry_run:
                cursor.execute(
                    f"""
                    SELECT COUNT(*) FROM financial_tables
                    WHERE LOWER(metric) LIKE '%ebitda%'
                      AND unit = 'kEUR'
                      AND ABS(value) < 1000
                      {doc_filter}
                """,
                    (document_id,) if document_id else (),
                )
                count = cursor.fetchone()[0]
            else:
                cursor.execute(
                    f"""
                    UPDATE financial_tables
                    SET unit = 'M EUR',
                        unit_inferred = TRUE,
                        unit_inference_method = 'ebitda_scale_correction'
                    WHERE LOWER(metric) LIKE '%ebitda%'
                      AND unit = 'kEUR'
                      AND ABS(value) < 1000
                      {doc_filter}
                """,
                    (document_id,) if document_id else (),
                )
                count = cursor.rowcount
                conn.commit()

            result.details["small_keur_to_meur"] = count
            result.rows_affected += count

            # NULL units on EBITDA -> assume M EUR
            if dry_run:
                cursor.execute(
                    f"""
                    SELECT COUNT(*) FROM financial_tables
                    WHERE LOWER(metric) LIKE '%ebitda%'
                      AND metric NOT LIKE '%Margin%'
                      AND unit IS NULL
                      {doc_filter}
                """,
                    (document_id,) if document_id else (),
                )
                count = cursor.fetchone()[0]
            else:
                cursor.execute(
                    f"""
                    UPDATE financial_tables
                    SET unit = 'M EUR',
                        unit_inferred = TRUE,
                        unit_inference_method = 'ebitda_default_meur'
                    WHERE LOWER(metric) LIKE '%ebitda%'
                      AND metric NOT LIKE '%Margin%'
                      AND unit IS NULL
                      {doc_filter}
                """,
                    (document_id,) if document_id else (),
                )
                count = cursor.rowcount
                conn.commit()

            result.details["null_to_meur"] = count
            result.rows_affected += count

        except Exception as e:
            result.success = False
            result.error = str(e)
            logger.error(f"EBITDA scale fix failed: {e}")

        return result


class UnitInferencePhase(PipelinePhase):
    """Phase 5: Context-based unit inference."""

    name = "unit_inference"

    def run(
        self,
        cursor: PgCursor,
        conn: PgConnection,
        document_id: str | None = None,
        dry_run: bool = False,
    ) -> PhaseResult:
        """Infer units from context for NULL unit rows."""
        result = PhaseResult(phase_name=self.name)
        doc_filter = "AND document_id = %s" if document_id else ""

        try:
            # Metric-based inference rules
            inferences = [
                # Financial metrics -> M EUR
                ("%revenue%", "M EUR"),
                ("%turnover%", "M EUR"),
                ("%cash%flow%", "M EUR"),
                ("%capex%", "M EUR"),
                ("%profit%", "M EUR"),
                # Volume metrics -> kton
                ("%volume%", "kton"),
                ("%sales%kton%", "kton"),
                # Percentage metrics -> %
                ("%margin%", "%"),
                ("%ratio%", "%"),
                ("%utilization%", "%"),
            ]

            total = 0
            for pattern, unit in inferences:
                if dry_run:
                    cursor.execute(
                        f"""
                        SELECT COUNT(*) FROM financial_tables
                        WHERE LOWER(metric) LIKE %s
                          AND unit IS NULL
                          {doc_filter}
                    """,
                        (pattern, document_id) if document_id else (pattern,),
                    )
                    count = cursor.fetchone()[0]
                else:
                    cursor.execute(
                        f"""
                        UPDATE financial_tables
                        SET unit = %s,
                            unit_inferred = TRUE,
                            unit_inference_method = 'metric_pattern_inference'
                        WHERE LOWER(metric) LIKE %s
                          AND unit IS NULL
                          {doc_filter}
                    """,
                        (unit, pattern, document_id) if document_id else (unit, pattern),
                    )
                    count = cursor.rowcount
                    if count > 0:
                        conn.commit()

                result.details[f"inferred_{pattern}"] = count
                total += count

            result.rows_affected = total

        except Exception as e:
            result.success = False
            result.error = str(e)
            logger.error(f"Unit inference failed: {e}")

        return result


class QualityRemediationPipeline:
    """Unified quality remediation pipeline."""

    # Available phases in execution order
    PHASES: list[tuple[str, type[PipelinePhase]]] = [
        ("structural", StructuralCleanupPhase),
        ("ratio", RatioDecompositionPhase),
        ("currency", CurrencyCleanupPhase),
        ("ebitda_scale", EBITDAScalePhase),
        ("unit_inference", UnitInferencePhase),
    ]

    def __init__(self, conn: PgConnection | None = None):
        """Initialize pipeline.

        Args:
            conn: PostgreSQL connection. If None, will create one when needed.
        """
        self._conn = conn

    def _get_connection(self) -> PgConnection:
        """Get or create PostgreSQL connection."""
        if self._conn is None:
            from raglite.shared.clients import get_postgresql_connection

            self._conn = get_postgresql_connection()
        return self._conn

    def run_incremental(self, document_id: str, dry_run: bool = False) -> PipelineReport:
        """Run pipeline for a single document.

        Args:
            document_id: UUID of the document to process
            dry_run: If True, count only without applying changes

        Returns:
            PipelineReport with results from all phases
        """
        report = PipelineReport(mode="incremental", document_id=document_id)
        conn = self._get_connection()
        cursor = conn.cursor()

        logger.info(
            "Starting incremental pipeline",
            extra={"document_id": document_id, "dry_run": dry_run},
        )

        for phase_name, phase_class in self.PHASES:
            phase = phase_class()
            result = phase.run(cursor, conn, document_id=document_id, dry_run=dry_run)
            report.add_phase(result)
            logger.info(
                f"Phase {phase_name} complete",
                extra={
                    "document_id": document_id,
                    "rows_affected": result.rows_affected,
                    "success": result.success,
                },
            )

        cursor.close()

        logger.info(
            "Incremental pipeline complete",
            extra={
                "document_id": document_id,
                "total_rows_affected": report.total_rows_affected,
                "success": report.success,
            },
        )

        return report

    def run_batch(self, dry_run: bool = False) -> PipelineReport:
        """Run pipeline for entire database.

        Args:
            dry_run: If True, count only without applying changes

        Returns:
            PipelineReport with results from all phases
        """
        report = PipelineReport(mode="batch")
        conn = self._get_connection()
        cursor = conn.cursor()

        logger.info("Starting batch pipeline", extra={"dry_run": dry_run})

        for phase_name, phase_class in self.PHASES:
            phase = phase_class()
            result = phase.run(cursor, conn, document_id=None, dry_run=dry_run)
            report.add_phase(result)
            logger.info(
                f"Phase {phase_name} complete",
                extra={
                    "rows_affected": result.rows_affected,
                    "success": result.success,
                },
            )

        cursor.close()

        logger.info(
            "Batch pipeline complete",
            extra={
                "total_rows_affected": report.total_rows_affected,
                "success": report.success,
            },
        )

        return report

    def run_phases(
        self,
        phases: list[str],
        document_id: str | None = None,
        dry_run: bool = False,
    ) -> PipelineReport:
        """Run specific phases only.

        Args:
            phases: List of phase names to run
            document_id: Optional document to filter (incremental mode)
            dry_run: If True, count only without applying changes

        Returns:
            PipelineReport with results from specified phases
        """
        mode = "incremental" if document_id else "batch"
        report = PipelineReport(mode=mode, document_id=document_id)
        conn = self._get_connection()
        cursor = conn.cursor()

        # Map phase names to classes
        phase_map = {name: cls for name, cls in self.PHASES}

        logger.info(
            f"Starting selective pipeline with phases: {phases}",
            extra={"document_id": document_id, "dry_run": dry_run},
        )

        for phase_name in phases:
            if phase_name not in phase_map:
                logger.warning(f"Unknown phase: {phase_name}")
                continue

            phase = phase_map[phase_name]()
            result = phase.run(cursor, conn, document_id=document_id, dry_run=dry_run)
            report.add_phase(result)

        cursor.close()

        return report
