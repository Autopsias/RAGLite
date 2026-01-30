"""Quality pipeline phase implementations.

This module contains the individual phase implementations for the quality remediation pipeline.
Each phase is responsible for a specific type of data quality fix.

Phases:
- StructuralCleanupPhase: Empty metrics, entity contamination cleanup
- RatioDecompositionPhase: Ratio metric decomposition
- CurrencyCleanupPhase: Currency standardization
- EBITDAScalePhase: EBITDA scale normalization
- UnitInferencePhase: Context-based unit inference
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from raglite.ingestion.quality_pipeline import PhaseResult, PipelinePhase
from raglite.shared.logging import get_logger

if TYPE_CHECKING:
    from psycopg2.extensions import connection as PgConnection
    from psycopg2.extensions import cursor as PgCursor

logger = get_logger(__name__)


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
