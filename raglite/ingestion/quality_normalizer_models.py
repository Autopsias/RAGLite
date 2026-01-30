"""Data models and constants for quality normalization.

This module contains the data structures and constant mappings used by
quality_normalizer for automatic quality normalization of ingested documents.
"""

from dataclasses import dataclass, field
from datetime import datetime

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
