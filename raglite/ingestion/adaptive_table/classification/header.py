"""
Header classification for adaptive table extraction.

This module provides header cell classification (TEMPORAL, ENTITY, METRIC).
"""

from __future__ import annotations

import logging
import re
from enum import Enum

logger = logging.getLogger(__name__)


class HeaderType(Enum):
    """Classification of header content."""

    TEMPORAL = "temporal"  # Dates, periods, quarters, years
    ENTITY = "entity"  # Companies, divisions, countries
    METRIC = "metric"  # Financial metrics, KPIs
    UNKNOWN = "unknown"  # Cannot classify


def _is_unit_descriptor(text_lower: str) -> bool:
    """Check if text is a unit descriptor (should return UNKNOWN).

    Headers like "Currency (1000 EUR)" describe units, NOT actual data categories.
    These should return UNKNOWN early to prevent misclassification as METRIC.

    Args:
        text_lower: Lowercase text content

    Returns:
        True if text matches unit descriptor patterns
    """
    unit_descriptor_patterns = [
        r"currency\s*\([^)]*\)",  # "Currency (1000 EUR)", "Currency (EUR million)"
        r"\b\d+\s*eur\b",  # "1000 EUR" standalone
        r"\b\d+\s*usd\b",  # "1000 USD" standalone
        r"^\s*unit[s]?\s*$",  # "Unit", "Units" as standalone header
        r"^\s*uom\s*$",  # "UOM" (Unit of Measure)
    ]

    return any(re.search(pattern, text_lower) for pattern in unit_descriptor_patterns)


def _get_temporal_patterns() -> list[str]:
    """Get temporal header patterns (dates, periods, quarters, years)."""
    return [
        # Years
        r"\b(20\d{2}|19\d{2})\b",
        # Quarters, halves, periods
        r"\b(Q[1-4]|H[1-2])\b",
        # English months (with optional year suffix)
        r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b",
        r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[-\s]?\d{2,4}\b",
        # Portuguese months (CRITICAL - document is in Portuguese!)
        r"\b(fev|abr|mai|ago|set|out|dez)\b",
        # Full month names
        r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\b",
        # Financial periods (case-insensitive via text_lower)
        r"\bytd\b",  # Year-to-date (CRITICAL!)
        r"\bmtd\b",  # Month-to-date
        r"\bqtd\b",  # Quarter-to-date
        r"\bly\b",  # Last year (CRITICAL!)
        r"\bpy\b",  # Previous year
        # Comparison keywords
        r"\bbudget\b",
        r"\bforecast\b",
        r"\bactual\b",
        r"\breal\b",  # Portuguese for "actual"
        r"\bvar\.?\b",  # Variance
        r"\bvs\.?\b",  # Versus (CRITICAL!)
        # Percentage comparisons (CRITICAL - no space after %!)
        r"%\s*(ly|py|b)\b",  # %LY, %PY, %B
        r"%\s*real\b",  # %Real
        # Generic temporal terms
        r"\bmonth\b",
        r"\byear\b",
        r"\bperiod\b",
        r"\blast\s+\d+\s+(months|years)\b",
    ]


def _get_entity_patterns() -> list[str]:
    """Get entity header patterns (countries, divisions, business units)."""
    return [
        # Common European countries (universal pattern)
        r"\b(portugal|spain|france|italy|germany|uk|belgium|netherlands|poland|greece)\b",
        # Common non-European countries (universal pattern)
        r"\b(usa|canada|brazil|mexico|argentina|chile)\b",
        r"\b(china|japan|india|singapore|australia)\b",
        r"\b(tunisia|morocco|egypt|algeria|lebanon|angola|kenya|nigeria)\b",
        # Industry-specific terms (keep cement/aggregates but add more universal terms)
        r"\b(cement|concrete|clinker|aggregates|ready-mix|ready\s*mix)\b",
        # Generic company/division terms (CRITICAL - universal!)
        r"\b(group|total|consolidated|conso)\b",
        r"\b(division|segment|region|regional)\b",
        r"\b(operations|corporate|holding)\b",
        r"\b(subsidiary|affiliate|joint\s*venture)\b",
        # Generic entity descriptors (universal)
        r"\b(north|south|east|west|central)\b",
        r"\b(domestic|international|overseas)\b",
        r"\b(others|other|misc|miscellaneous)\b",
    ]


def _get_metric_patterns() -> list[str]:
    """Get metric header patterns (financial/operational metrics)."""
    return [
        # Core financial metrics (universal)
        r"\b(ebitda|ebit|revenue|turnover|sales|margin)\b",
        r"\b(cost|expense|opex|capex)\b",
        r"\b(profit|loss|income|earnings)\b",
        # Cash and debt (CRITICAL - universal!)
        r"\b(cash|debt|equity)\b",
        r"\b(receivables|payables|inventory)\b",
        r"\b(assets|liabilities)\b",
        # Financial modifiers (CRITICAL - universal!)
        r"\b(net|gross|total|operating)\b",
        # Capital metrics (CRITICAL - universal!)
        r"\b(capital|invested|working|employed)\b",
        # Performance metrics (CRITICAL - universal!)
        r"\b(profitability|performance|efficiency)\b",
        r"\b(operational|financial|commercial)\b",
        r"\b(results|indicators|metrics)\b",
        # Production and operations (universal)
        r"\b(production|volume|capacity|output)\b",
        r"\b(variable|fixed)\b",
        # Pricing (universal)
        r"\b(price|unit|average)\b",
        # Energy and utilities (may vary by industry, but universal terms)
        r"\b(thermal|electrical|fuel|energy)\b",
        # HR metrics (universal)
        r"\b(employee|headcount|fte|workforce)\b",
        # Safety metrics (universal)
        r"\b(frequency|severity|accident|safety)\b",
        # Accounting (universal)
        r"\b(depreciation|amortization|provision)\b",
        # Ratios and units (universal - add more common units)
        r"\bratio\b",
        r"\beur/ton\b",
        r"\b\$/ton\b",
        r"\bgbp/ton\b",
        r"\bgj/ton\b",
        r"\bmwh\b",
        r"\bkwh\b",
        # Exchange rates (CRITICAL - universal!)
        r"\beur/[a-z]{3}\b",  # EUR/USD, EUR/BRL, EUR/AKZ, etc.
        r"\busd/[a-z]{3}\b",  # USD/EUR, etc.
        r"\bgbp/[a-z]{3}\b",  # GBP/USD, etc.
        r"\bexchange\b",
        r"\bcurrency\b",
        # ====== CEMENT INDUSTRY SPECIFIC METRICS (Phase 1.1) ======
        # Fuels - CRITICAL for petcoke queries
        r"\b(petcoke|pet\s*coke|petroleum\s*coke)\b",
        r"\b(coal|lignite|natural\s*gas|fuel\s*oil)\b",
        r"\b(alternative\s*fuels?|af\s*rate|biomass|waste\s*fuel)\b",
        # Production metrics - clinker, slag, etc.
        r"\b(clinker|slag|fly\s*ash|gypsum|limestone)\b",
        r"\b(clinker\s*factor|clinker\s*ratio|clinker/cement)\b",
        r"\b(kiln|grinding|raw\s*mill|cement\s*mill)\b",
        # Sustainability metrics - CO2, emissions, GHG
        r"\b(co2|emissions?|carbon|scope\s*[123]|ghg)\b",
        r"\b(thermal\s*substitution|tsr)\b",
        r"\b(decarboni[sz]ation|net\s*zero)\b",
        # Capacity and utilization
        r"\b(utilization|uptime|availability)\b",
        r"\b(mtpa|tpd|tons?\s*per)\b",
        r"\b(kcal/kg|gj/ton|kwh/ton)\b",
        # Logistics and distribution
        r"\b(lead\s*distance|freight|logistics)\b",
        r"\b(dispatch|delivery|transport)\b",
    ]


def _classify_from_scores(temporal_score: int, entity_score: int, metric_score: int) -> HeaderType:
    """Classify header based on pattern match scores.

    Temporal has highest priority (strongest layout signal).

    Args:
        temporal_score: Count of temporal pattern matches
        entity_score: Count of entity pattern matches
        metric_score: Count of metric pattern matches

    Returns:
        HeaderType classification based on strongest signal
    """
    if temporal_score > 0:
        return HeaderType.TEMPORAL
    elif metric_score > entity_score:
        return HeaderType.METRIC
    elif entity_score > 0:
        return HeaderType.ENTITY
    else:
        return HeaderType.UNKNOWN


def classify_header(text: str) -> HeaderType:
    """Classify header cell content using pattern matching.

    Uses comprehensive pattern matching for financial document headers.
    Temporal indicators take precedence (strongest signal for layout detection).

    Args:
        text: Cell text content

    Returns:
        HeaderType classification
    """
    if not text or not text.strip():
        return HeaderType.UNKNOWN

    text_lower = text.lower().strip()

    # Check for unit descriptors first (return UNKNOWN early)
    if _is_unit_descriptor(text_lower):
        return HeaderType.UNKNOWN

    # Get pattern lists
    temporal_patterns = _get_temporal_patterns()
    entity_patterns = _get_entity_patterns()
    metric_patterns = _get_metric_patterns()

    # Count pattern matches
    temporal_score = sum(1 for p in temporal_patterns if re.search(p, text_lower))
    entity_score = sum(1 for p in entity_patterns if re.search(p, text_lower))
    metric_score = sum(1 for p in metric_patterns if re.search(p, text_lower))

    # Classify based on strongest signal
    return _classify_from_scores(temporal_score, entity_score, metric_score)
