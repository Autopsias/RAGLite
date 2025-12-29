"""Rule-based unit pattern detection.

This module provides pattern-based unit inference to avoid 80% of API calls
by handling common financial metric patterns without LLM inference (Story 5.0.6: AC2).
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# Rule-based unit patterns (Story 5.0.6: AC2 - 80% API reduction)
# Maps metric name patterns to their typical units in financial documents
#
# IMPORTANT: Pattern order matters - first match wins!
# Margin/Ratio patterns MUST come before Revenue/EBITDA to correctly handle
# cases like "EBITDA Margin" (should be %, not Meur)
#
# Phase 4.1-4.2: Added cement industry specific patterns (Story 5.0.7)
UNIT_RULES = [
    # ===== PHASE 4: CEMENT INDUSTRY SPECIFIC (HIGHEST PRIORITY) =====
    # TPD (tons per day) → tons/day (BEFORE production pattern)
    (r"(?i)\btpd\b", "tons/day"),
    # MTPA (million tons per annum) → Mton/year (BEFORE capacity pattern)
    (r"(?i)\bmtpa\b", "Mton/year"),
    # kcal/kg (fuel consumption) → kcal/kg (BEFORE other patterns)
    (r"(?i)kcal/kg", "kcal/kg"),
    # kWh/ton (power consumption) → kWh/ton (BEFORE /ton pattern)
    (r"(?i)kwh/ton", "kWh/ton"),
    # GJ/ton (energy intensity) → GJ/ton (BEFORE /ton pattern)
    (r"(?i)gj/ton", "GJ/ton"),
    # Factor (e.g., Clinker Factor) → % (clinker factor is a percentage ratio)
    (r"(?i)\bfactor\b", "%"),
    # ===== STANDARD FINANCIAL PATTERNS =====
    # Margin, Ratio, Rate → % (matches "EBITDA Margin" → % not Meur)
    (r"(?i)(margin|ratio|rate|percentage|%)", "%"),
    # Per ton metrics → EUR/ton (matches "Cost/ton" → EUR/ton not Meur)
    (r"(?i)(/ton|per ton|€/ton)", "EUR/ton"),
    # Revenue, Income, Profit metrics → Meur (AFTER margin/per-ton to avoid conflicts)
    (r"(?i)(revenue|ebitda|profit|income|cost|capex|sales|turnover)", "Meur"),
    # Volume, Production → kton
    (r"(?i)(volume|production|capacity|output)", "kton"),
    # Days, Period → days
    (r"(?i)(days|period)", "days"),
    # Headcount, Employees → FTE
    (r"(?i)(headcount|employees|fte|staff|workforce)", "FTE"),
]


def infer_unit_from_rules(metric: str) -> str | None:
    """Infer unit from metric name using pattern-based rules.

    This implements AC2 (Rule-Based Unit Pre-Filter) to avoid 80% of API calls
    by handling common financial metric patterns without LLM inference.

    Args:
        metric: Metric name to analyze (e.g., "EBITDA IFRS", "Gross Margin")

    Returns:
        Inferred unit string (e.g., "Meur", "%", "EUR/ton") or None if no match

    Example:
        >>> infer_unit_from_rules("Total Revenue")
        'Meur'
        >>> infer_unit_from_rules("EBITDA Margin")
        '%'
        >>> infer_unit_from_rules("Production Volume")
        'kton'
        >>> infer_unit_from_rules("Unknown Metric XYZ")
        None
    """
    if not metric:
        return None

    # Try each pattern in order (first match wins)
    for pattern, unit in UNIT_RULES:
        if re.search(pattern, metric):
            logger.debug(
                "Unit inferred from rules",
                extra={
                    "metric": metric,
                    "pattern": pattern,
                    "unit": unit,
                    "source": "rule",
                },
            )
            return unit

    return None
