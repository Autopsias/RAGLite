"""Entity level classification for ingestion pipeline.

Classifies financial entities into levels:
- CONSOLIDATED: Group-level aggregated data
- COMPANY_ONLY: Individual company data
- SEGMENT: Business segment data
- GEOGRAPHIC: Geographic region data
- UNKNOWN: Cannot determine level
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


def classify_entity_level(
    entity: str,
    table_title: str | None = None,
) -> ClassifiedEntityLevel:
    """Classify an entity string into its entity level.

    Classification hierarchy (checked first to last):
    0. Empty/whitespace/unknown patterns -> UNKNOWN
    1. Entity pattern (consolidated, company, segment, geographic) - highest priority
    2. Table title context (secondary signal)
    3. Default: UNKNOWN (conservative approach)

    Args:
        entity: Entity string to classify
        table_title: Optional table title for context

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

    # Step 1: Check entity patterns (highest priority)

    # Check consolidated patterns
    for pattern in CONSOLIDATED_PATTERNS:
        if re.search(pattern, entity_lower):
            return ClassifiedEntityLevel(
                original=entity,
                entity_level=EntityLevel.CONSOLIDATED,
                source="entity_pattern",
            )

    # Check company patterns
    for pattern in COMPANY_PATTERNS:
        if re.search(pattern, entity_lower):
            return ClassifiedEntityLevel(
                original=entity,
                entity_level=EntityLevel.COMPANY_ONLY,
                source="entity_pattern",
            )

    # Check geographic patterns (country/region names)
    # Use word boundaries to avoid false positives (e.g., "uk" matching "Duke")
    for geo_entity in GEOGRAPHIC_ENTITIES:
        if re.search(rf"\b{re.escape(geo_entity)}\b", entity_lower):
            logger.debug(f"Matched geographic entity '{geo_entity}' in '{entity}'")
            return ClassifiedEntityLevel(
                original=entity,
                entity_level=EntityLevel.GEOGRAPHIC,
                source="entity_pattern",
            )

    # Check segment patterns
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
) -> ClassifiedEntityLevel:
    """Cache wrapper for classify_entity_level.

    Args:
        normalized_entity: Whitespace-stripped entity string
        normalized_table_title: Whitespace-stripped table title (or None)

    Returns:
        ClassifiedEntityLevel result
    """
    return classify_entity_level(normalized_entity, normalized_table_title)


def classify_entity_levels_batch(
    entities: list[str],
    table_titles: list[str | None] | None = None,
) -> tuple[list[ClassifiedEntityLevel], EntityLevelReport]:
    """Classify a batch of entity strings.

    Args:
        entities: List of entity strings to classify
        table_titles: Optional list of table titles (same length as entities, or None)

    Returns:
        Tuple of (list of ClassifiedEntityLevel, EntityLevelReport)

    Raises:
        ValueError: If table_titles length doesn't match entities length

    Examples:
        >>> results, report = classify_entity_levels_batch(["GROUP", "Portugal", "SECIL"])
        >>> len(results)
        3
        >>> report.total_records
        3
    """
    if table_titles is not None and len(table_titles) != len(entities):
        raise ValueError(
            f"table_titles and entities must have the same length (got {len(table_titles)} and {len(entities)})"
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

        # Normalize inputs for caching
        normalized_entity = entity.strip() if entity else ""
        normalized_table_title = table_title.strip() if table_title else None

        # Classify with caching
        result = _classify_cached(normalized_entity, normalized_table_title)
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
