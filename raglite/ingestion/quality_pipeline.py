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

from raglite.ingestion.quality_pipeline_phases import (
    CurrencyCleanupPhase,
    EBITDAScalePhase,
    RatioDecompositionPhase,
    StructuralCleanupPhase,
    UnitInferencePhase,
)
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
        phase_map = dict(self.PHASES)

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
