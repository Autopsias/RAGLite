"""Entity level classification for ingestion pipeline.

Classifies financial entities into levels:
- CONSOLIDATED: Group-level aggregated data
- COMPANY_ONLY: Individual company data
- SEGMENT: Business segment data
- GEOGRAPHIC: Geographic region data
- UNKNOWN: Cannot determine level

Currency Detection (Story 9.4 Enhancement):
Non-EUR currencies are strong signals for geographic entities:
- BRL (Brazilian Real) → Brazil
- AOA (Angolan Kwanza) → Angola
- LBP (Lebanese Pound) → Lebanon
- TND (Tunisian Dinar) → Tunisia
"""

import re
from functools import lru_cache

from raglite.ingestion.classification.models import (
    ClassifiedEntityLevel,
    EntityLevel,
    EntityLevelReport,
)
from raglite.shared.logging import get_logger

logger = get_logger(__name__)

# Currency to entity mapping (non-EUR currencies indicate geographic entities)
# When a row has a non-EUR currency, it should be classified as that geographic entity
# regardless of what the entity field says (e.g., "SECIL Group" with BRL → Brazil)
CURRENCY_TO_ENTITY: dict[str, str] = {
    # Brazilian Real
    "BRL": "Brazil",
    "1000 BRL": "Brazil",
    "BRL/ton": "Brazil",
    "BRL/m3": "Brazil",
    # Angolan Kwanza
    "AOA": "Angola",
    "1000 AOA": "Angola",
    "AOA/ton": "Angola",
    # Lebanese Pound
    "LBP": "Lebanon",
    "1000 LBP": "Lebanon",
    "LBP/ton": "Lebanon",
    # Tunisian Dinar
    "TND": "Tunisia",
    "1000 TND": "Tunisia",
    "TND/ton": "Tunisia",
}

# Currency codes that indicate non-EUR data (used for pattern matching)
NON_EUR_CURRENCY_CODES: set[str] = {"BRL", "AOA", "LBP", "TND"}

# Geographic entity dictionary
GEOGRAPHIC_ENTITIES: set[str] = {
    # Countries (common in financial reports)
    "portugal",
    "spain",
    "tunisia",
    "brazil",
    "lebanon",
    "angola",
    "mozambique",
    "cape verde",
    "france",
    "germany",
    "uk",
    "italy",
    # Regions
    "iberia",
    "europe",
    "mena",
    "latam",
    "americas",
    "asia",
    "africa",
    "north",
    "south",
    "east",
    "west",
    # Portuguese geographic keywords
    "pais",
    "regiao",
    "continente",
}

# Consolidated keywords (case-insensitive)
CONSOLIDATED_PATTERNS = [
    r"\bgroup\b",
    r"\bconsolidated\b",
    r"\btotal\s*group\b",
    r"\bgroup\s*total\b",
    r"\bholding\b",
    r"\bcorporate\b",
]

# Company patterns (case-insensitive)
COMPANY_PATTERNS = [
    r"\bsa\b",
    r"\bltd\b",
    r"\blda\b",
    r"\bs\.a\.\b",
    r"\bltda\b",
    r"\binc\b",
    r"\bcorp\b",
    r"\bcompany\b",
    r"\bempresa\b",
    r"\bsecil\b",  # Known company name
]

# Segment patterns (case-insensitive)
SEGMENT_PATTERNS = [
    r"\bdivision\b",
    r"\bsegment\b",
    r"\bunit\b",
    r"\bsector\b",
    r"\boperations\b",
    r"\bbusiness\b",
    r"\bready[- ]?mix\b",
    r"\bcement\b",
    r"\bconcrete\b",
    r"\baggregates\b",
]

# Industry-specific keywords (used for "Geographic + Industry = Company" rule)
# These are more specific than generic operational terms
# "Portugal Cement" = company, but "Portugal Operations" = geographic
INDUSTRY_SPECIFIC_PATTERNS = [
    r"\bcement\b",
    r"\bconcrete\b",
    r"\baggregates\b",
    r"\bready[- ]?mix\b",
    r"\bprecast\b",
    r"\bmortars?\b",
    r"\bquarry\b",
    r"\bquarries\b",
    r"\bmining\b",
    r"\bsteel\b",
]


def _detect_currency_entity(unit: str | None) -> str | None:
    """Detect geographic entity from currency in unit field.

    Non-EUR currencies are strong indicators of geographic entities.
    For example, "1000 BRL" or "BRL/ton" indicates Brazil operations.

    Args:
        unit: Unit string (e.g., "M EUR", "1000 BRL", "BRL/ton")

    Returns:
        Entity name if non-EUR currency detected, None otherwise

    Examples:
        >>> _detect_currency_entity("1000 BRL")
        'Brazil'
        >>> _detect_currency_entity("M EUR")
        None
        >>> _detect_currency_entity("AOA/ton")
        'Angola'
    """
    if not unit:
        return None

    unit_upper = unit.upper().strip()

    # Check exact match first
    if unit_upper in CURRENCY_TO_ENTITY:
        return CURRENCY_TO_ENTITY[unit_upper]

    # Check for currency code anywhere in unit string
    for currency_code in NON_EUR_CURRENCY_CODES:
        if currency_code in unit_upper:
            # Map currency code to entity
            for unit_pattern, entity_name in CURRENCY_TO_ENTITY.items():
                if currency_code in unit_pattern.upper():
                    return entity_name

    return None


def classify_entity_level(
    entity: str,
    table_title: str | None = None,
    unit: str | None = None,
    metric: str | None = None,
) -> ClassifiedEntityLevel:
    """Classify an entity string into its entity level.

    Classification hierarchy (checked first to last):
    0. Empty/whitespace/unknown patterns -> UNKNOWN
    0.5. Currency detection (non-EUR currency = geographic) - HIGHEST priority
    1. Entity pattern (consolidated, company, segment, geographic)
    2. Table title context (secondary signal)
    2.5. Metric name context inference (fallback for UNKNOWN only)
    3. Default: UNKNOWN (conservative approach)

    Args:
        entity: Entity string to classify
        table_title: Optional table title for context
        unit: Optional unit string for currency detection (e.g., "1000 BRL")
        metric: Optional metric name for context inference (e.g., "EBITDA IFRS Group")

    Returns:
        ClassifiedEntityLevel with entity level and source attribution

    Examples:
        >>> classify_entity_level("GROUP")
        ClassifiedEntityLevel(original="GROUP", entity_level=CONSOLIDATED, source="entity_pattern")
        >>> classify_entity_level("SECIL SA")
        ClassifiedEntityLevel(original="SECIL SA", entity_level=COMPANY_ONLY, source="entity_pattern")
        >>> classify_entity_level("Portugal")
        ClassifiedEntityLevel(original="Portugal", entity_level=GEOGRAPHIC, source="entity_pattern")
        >>> classify_entity_level("Cement Division")
        ClassifiedEntityLevel(original="Cement Division", entity_level=SEGMENT, source="entity_pattern")
        >>> classify_entity_level("Revenue", table_title="GROUP Financial Statements")
        ClassifiedEntityLevel(original="Revenue", entity_level=CONSOLIDATED, source="table_title")
        >>> classify_entity_level("SECIL Group", unit="1000 BRL")
        ClassifiedEntityLevel(original="SECIL Group", entity_level=GEOGRAPHIC, source="currency_detection", corrected_entity="Brazil")
    """
    # Step 0: Handle empty/whitespace/unknown patterns
    if not entity or not entity.strip():
        return ClassifiedEntityLevel(
            original=entity,
            entity_level=EntityLevel.UNKNOWN,
            source="empty",
        )

    entity_stripped = entity.strip()
    entity_lower = entity_stripped.lower()

    # Check for common unknown markers
    if entity_lower in ("n/a", "none", "null", "-", "--"):
        return ClassifiedEntityLevel(
            original=entity,
            entity_level=EntityLevel.UNKNOWN,
            source="unknown_marker",
        )

    # Check for ambiguous patterns (numbers only, generic text)
    if re.match(r"^\d+$", entity_stripped):
        return ClassifiedEntityLevel(
            original=entity,
            entity_level=EntityLevel.UNKNOWN,
            source="ambiguous",
        )

    # Step 0.5: Currency detection (HIGHEST priority)
    # Non-EUR currencies override entity classification
    # e.g., "SECIL Group" with unit="1000 BRL" → Brazil (geographic)
    currency_entity = _detect_currency_entity(unit)
    if currency_entity:
        logger.debug(f"Currency detection: '{entity}' with unit='{unit}' → {currency_entity}")
        return ClassifiedEntityLevel(
            original=entity,
            entity_level=EntityLevel.GEOGRAPHIC,
            source="currency_detection",
            corrected_entity=currency_entity,
        )

    # Step 1: Check entity patterns (highest priority)
    # Order matters: check company/segment patterns BEFORE geographic
    # Special case: "Portugal Cement" = company name (geo + industry keyword)

    # Check consolidated patterns
    for pattern in CONSOLIDATED_PATTERNS:
        if re.search(pattern, entity_lower):
            return ClassifiedEntityLevel(
                original=entity,
                entity_level=EntityLevel.CONSOLIDATED,
                source="entity_pattern",
            )

    # Check company patterns (explicit company indicators like SA, Ltd)
    has_company_indicator = any(re.search(pattern, entity_lower) for pattern in COMPANY_PATTERNS)

    if has_company_indicator:
        return ClassifiedEntityLevel(
            original=entity,
            entity_level=EntityLevel.COMPANY_ONLY,
            source="entity_pattern",
        )

    # Check for geographic names first
    has_geographic = any(
        re.search(rf"\b{re.escape(geo)}\b", entity_lower) for geo in GEOGRAPHIC_ENTITIES
    )

    if has_geographic:
        # Geographic + Industry-specific keyword = Company name
        # e.g., "Portugal Cement", "Spain Steel", "Brazil Mining"
        has_industry_keyword = any(
            re.search(pattern, entity_lower) for pattern in INDUSTRY_SPECIFIC_PATTERNS
        )

        if has_industry_keyword:
            return ClassifiedEntityLevel(
                original=entity,
                entity_level=EntityLevel.COMPANY_ONLY,
                source="entity_pattern",
            )

        # Geographic WITHOUT industry-specific keyword = GEOGRAPHIC
        # e.g., "Portugal Operations", "Tunisia Business", "Europe Region"
        # Geographic takes precedence over generic segment keywords
        logger.debug(f"Matched geographic entity in '{entity}'")
        return ClassifiedEntityLevel(
            original=entity,
            entity_level=EntityLevel.GEOGRAPHIC,
            source="entity_pattern",
        )

    # Check segment patterns (e.g., "Cement Division", "Ready Mix Unit")
    # Only applies to non-geographic entities
    for pattern in SEGMENT_PATTERNS:
        if re.search(pattern, entity_lower):
            return ClassifiedEntityLevel(
                original=entity,
                entity_level=EntityLevel.SEGMENT,
                source="entity_pattern",
            )

    # Step 2: Check table title context (secondary signal)
    if table_title and table_title.strip():
        table_title_lower = table_title.lower()

        # Check consolidated in table title
        for pattern in CONSOLIDATED_PATTERNS:
            if re.search(pattern, table_title_lower):
                return ClassifiedEntityLevel(
                    original=entity,
                    entity_level=EntityLevel.CONSOLIDATED,
                    source="table_title",
                )

        # Check geographic in table title
        for geo_entity in GEOGRAPHIC_ENTITIES:
            if geo_entity in table_title_lower:
                return ClassifiedEntityLevel(
                    original=entity,
                    entity_level=EntityLevel.GEOGRAPHIC,
                    source="table_title",
                )

        # Check segment in table title
        for pattern in SEGMENT_PATTERNS:
            if re.search(pattern, table_title_lower):
                return ClassifiedEntityLevel(
                    original=entity,
                    entity_level=EntityLevel.SEGMENT,
                    source="table_title",
                )

    # Step 2.5: Metric name context inference (fallback for otherwise-UNKNOWN entities)
    # Only applies when entity/table_title patterns didn't match, to avoid overriding
    # correct classifications (e.g., "GROUP" with metric "Revenue Cement" stays CONSOLIDATED)
    if metric:
        metric_lower = metric.lower().strip()
        # Metric containing "group" or "consolidated" → CONSOLIDATED
        if any(p in metric_lower for p in ("group", "consolidated", "conso")):
            return ClassifiedEntityLevel(
                original=entity,
                entity_level=EntityLevel.CONSOLIDATED,
                source="metric_context",
            )
        # Metric containing geographic entity name → GEOGRAPHIC
        for geo in GEOGRAPHIC_ENTITIES:
            if geo in metric_lower:
                return ClassifiedEntityLevel(
                    original=entity,
                    entity_level=EntityLevel.GEOGRAPHIC,
                    source="metric_context",
                )
        # Metric containing segment keywords → SEGMENT
        segment_keywords = ("cement", "ready-mix", "concrete", "aggregates", "precast")
        if any(p in metric_lower for p in segment_keywords):
            return ClassifiedEntityLevel(
                original=entity,
                entity_level=EntityLevel.SEGMENT,
                source="metric_context",
            )

    # Step 3: Default to UNKNOWN (conservative approach)
    logger.debug(f"No classification found for '{entity}', defaulting to UNKNOWN")
    return ClassifiedEntityLevel(
        original=entity,
        entity_level=EntityLevel.UNKNOWN,
        source="default",
    )


# Module-level cache (persistent across calls)
@lru_cache(maxsize=1000)
def _classify_cached(
    normalized_entity: str,
    normalized_table_title: str | None,
    normalized_unit: str | None,
    normalized_metric: str | None = None,
) -> ClassifiedEntityLevel:
    """Cache wrapper for classify_entity_level.

    Args:
        normalized_entity: Whitespace-stripped entity string
        normalized_table_title: Whitespace-stripped table title (or None)
        normalized_unit: Whitespace-stripped unit string (or None)
        normalized_metric: Whitespace-stripped metric string (or None)

    Returns:
        ClassifiedEntityLevel result
    """
    return classify_entity_level(
        normalized_entity, normalized_table_title, normalized_unit, normalized_metric
    )


def classify_entity_levels_batch(
    entities: list[str],
    table_titles: list[str | None] | None = None,
    units: list[str | None] | None = None,
    metrics: list[str | None] | None = None,
) -> tuple[list[ClassifiedEntityLevel], EntityLevelReport]:
    """Classify a batch of entity strings.

    Args:
        entities: List of entity strings to classify
        table_titles: Optional list of table titles (same length as entities, or None)
        units: Optional list of unit strings for currency detection (same length as entities, or None)
        metrics: Optional list of metric strings for context inference (same length as entities, or None)

    Returns:
        Tuple of (list of ClassifiedEntityLevel, EntityLevelReport)

    Raises:
        ValueError: If table_titles, units, or metrics length doesn't match entities length

    Examples:
        >>> results, report = classify_entity_levels_batch(["GROUP", "Portugal", "SECIL"])
        >>> len(results)
        3
        >>> report.total_records
        3
        >>> # Currency detection example
        >>> results, _ = classify_entity_levels_batch(["SECIL Group"], units=["1000 BRL"])
        >>> results[0].entity_level.name
        'GEOGRAPHIC'
        >>> results[0].corrected_entity
        'Brazil'
    """
    if table_titles is not None and len(table_titles) != len(entities):
        raise ValueError(
            f"table_titles and entities must have the same length (got {len(table_titles)} and {len(entities)})"
        )
    if units is not None and len(units) != len(entities):
        raise ValueError(
            f"units and entities must have the same length (got {len(units)} and {len(entities)})"
        )
    if metrics is not None and len(metrics) != len(entities):
        raise ValueError(
            f"metrics and entities must have the same length (got {len(metrics)} and {len(entities)})"
        )

    # Initialize counters for single-pass counting
    consolidated_count = 0
    company_only_count = 0
    segment_count = 0
    geographic_count = 0
    unknown_count = 0

    # Classify each entity
    results: list[ClassifiedEntityLevel] = []
    for idx, entity in enumerate(entities):
        table_title = table_titles[idx] if table_titles else None
        unit = units[idx] if units else None
        metric = metrics[idx] if metrics else None

        # Normalize inputs for caching
        normalized_entity = entity.strip() if entity else ""
        normalized_table_title = table_title.strip() if table_title else None
        normalized_unit = unit.strip() if unit else None
        normalized_metric = metric.strip() if metric else None

        # Classify with caching
        result = _classify_cached(
            normalized_entity, normalized_table_title, normalized_unit, normalized_metric
        )
        results.append(result)

        # Update counters in single pass
        if result.entity_level == EntityLevel.CONSOLIDATED:
            consolidated_count += 1
        elif result.entity_level == EntityLevel.COMPANY_ONLY:
            company_only_count += 1
        elif result.entity_level == EntityLevel.SEGMENT:
            segment_count += 1
        elif result.entity_level == EntityLevel.GEOGRAPHIC:
            geographic_count += 1
        else:
            unknown_count += 1

    report = EntityLevelReport(
        total_records=len(entities),
        consolidated_count=consolidated_count,
        company_only_count=company_only_count,
        segment_count=segment_count,
        geographic_count=geographic_count,
        unknown_count=unknown_count,
    )

    return results, report
