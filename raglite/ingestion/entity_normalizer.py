"""Entity normalizer for canonical entity name mapping.

Phase 2.1: This module provides entity normalization to map raw entity names
from extracted tables to canonical forms. This addresses the 22-88% entity
coverage variance identified in the data quality assessment.

Root Cause Addressed:
- Working Capital: Only 22% entity coverage due to variations like
  "PT", "Portugal", "Portugal Cement", "Cimento de Portugal"
- Need consistent entity names for reliable SQL queries

Usage:
    from raglite.ingestion.entity_normalizer import normalize_entity

    raw_entity = "PT"
    canonical = normalize_entity(raw_entity)  # Returns "Portugal"
"""

import logging
import re

logger = logging.getLogger(__name__)


# ============================================================================
# ENTITY CANONICAL MAPPINGS
# Maps raw entity variations to canonical forms for consistent database storage.
# ============================================================================

ENTITY_CANONICAL_MAP: dict[str, str] = {
    # ===== PORTUGAL VARIATIONS =====
    "PT": "Portugal",
    "Portugal Cement": "Portugal",
    "Cimento de Portugal": "Portugal",
    "Secil Portugal": "Portugal",
    "SECIL Portugal": "Portugal",
    "Secil PT": "Portugal",
    "Port.": "Portugal",
    "Portug.": "Portugal",
    "PORTUGAL": "Portugal",
    # Note: Sub-regions like "Portugal Cape Verde", "Portugal Group Madeira" are kept separate
    # User may request aggregation in the future, but for data quality, keeping them distinct
    # ===== BRAZIL VARIATIONS =====
    "BR": "Brazil",
    "Brasil": "Brazil",
    "Brazil Cement": "Brazil",
    "BRAZIL": "Brazil",
    "Secil Brazil": "Brazil",
    "Secil Brasil": "Brazil",
    # ===== TUNISIA VARIATIONS =====
    "TN": "Tunisia",
    "Tunisie": "Tunisia",
    "Tunisia Cement": "Tunisia",
    "TUNISIA": "Tunisia",
    "Secil Tunisia": "Tunisia",
    "Secil Tunisie": "Tunisia",
    "Tunísia": "Tunisia",
    # ===== LEBANON VARIATIONS =====
    "LB": "Lebanon",
    "Liban": "Lebanon",
    "Lebanon Cement": "Lebanon",
    "LEBANON": "Lebanon",
    "Secil Lebanon": "Lebanon",
    "Secil Liban": "Lebanon",
    "Líbano": "Lebanon",
    # ===== ANGOLA VARIATIONS =====
    "AO": "Angola",
    "Angola Cement": "Angola",
    "ANGOLA": "Angola",
    "Secil Angola": "Angola",
    # ===== CAPE VERDE VARIATIONS =====
    "CV": "Cape Verde",
    "Cabo Verde": "Cape Verde",
    "Cape Verde Cement": "Cape Verde",
    "CAPE VERDE": "Cape Verde",
    "Secil Cape Verde": "Cape Verde",
    # ===== GROUP/CONSOLIDATED VARIATIONS =====
    "Conso": "Group",
    "CONSO": "Group",
    "Consolidated": "Group",
    "Group Total": "Group",
    "Secil GROUP": "Group",
    "Secil Group": "Group",
    "SECIL GROUP": "Group",
    "Total Group": "Group",
    "GROUP": "Group",
    "Total": "Group",
    "TOTAL": "Group",
    "Groupe": "Group",
    "Consolidado": "Group",
    # ===== READY-MIX VARIATIONS =====
    "Ready-Mix": "Ready-Mix",
    "RMC": "Ready-Mix",
    "Betão Pronto": "Ready-Mix",
    "Concrete": "Ready-Mix",
    "Ready Mix": "Ready-Mix",
    "READY-MIX": "Ready-Mix",
    # ===== CEMENT UNIT VARIATIONS =====
    "Cement Unit": "Cement",
    "Cement": "Cement",
    "CEMENT": "Cement",
    "Cimento": "Cement",
    # ===== TRADING VARIATIONS =====
    "Trading": "Trading",
    "TRADING": "Trading",
    "Secil Trading": "Trading",
    "Cimpor Trading": "Trading",
    # ===== PARENT COMPANY VARIATIONS =====
    "CIMPOR": "Cimpor",
    "Cimpor": "Cimpor",
    "InterCement": "InterCement",
    "Intercement": "InterCement",
    "INTERCIMENT": "InterCement",
    "Secil": "Secil",
    "SECIL": "Secil",
}

# Additional fuzzy patterns for partial matching
ENTITY_FUZZY_PATTERNS: list[tuple[str, str]] = [
    # Pattern, Canonical name
    (r"\bportug", "Portugal"),
    (r"\bbrasil|\bbrazil", "Brazil"),
    (r"\btunis", "Tunisia"),
    (r"\bleban|\bliban", "Lebanon"),
    (r"\bangol", "Angola"),
    (r"\bcabo\s*verde|\bcape\s*verde", "Cape Verde"),
    (r"\bconso|\bgroup|\btotal", "Group"),
    (r"\bready[\s-]*mix|\brmix|\bbetao", "Ready-Mix"),
    (r"\bcement|\bcimento", "Cement"),
    (r"\btrad(?:ing)?", "Trading"),
]


def normalize_entity(raw_entity: str | None) -> str | None:
    """Map raw entity name to canonical form.

    Phase 2.1: Normalizes entity variations to consistent canonical names.
    This improves entity coverage from 22-88% to expected 70-95%.

    Args:
        raw_entity: Raw entity name from table extraction

    Returns:
        Canonical entity name, or original if no mapping found.
        Returns None if input is None or empty.

    Examples:
        >>> normalize_entity("PT")
        'Portugal'
        >>> normalize_entity("Brasil")
        'Brazil'
        >>> normalize_entity("Secil GROUP")
        'Group'
        >>> normalize_entity("Unknown Entity")
        'Unknown Entity'
    """
    if not raw_entity:
        return None

    # Strip whitespace
    raw_entity = raw_entity.strip()
    if not raw_entity:
        return None

    # Direct lookup (exact match)
    if raw_entity in ENTITY_CANONICAL_MAP:
        canonical = ENTITY_CANONICAL_MAP[raw_entity]
        logger.debug(
            "Entity normalized (exact match)",
            extra={"raw": raw_entity, "canonical": canonical},
        )
        return canonical

    # Case-insensitive lookup
    for key, canonical in ENTITY_CANONICAL_MAP.items():
        if key.lower() == raw_entity.lower():
            logger.debug(
                "Entity normalized (case-insensitive)",
                extra={"raw": raw_entity, "canonical": canonical},
            )
            return canonical

    # Fuzzy pattern matching
    raw_lower = raw_entity.lower()
    for pattern, canonical in ENTITY_FUZZY_PATTERNS:
        if re.search(pattern, raw_lower, re.IGNORECASE):
            logger.debug(
                "Entity normalized (fuzzy pattern)",
                extra={"raw": raw_entity, "canonical": canonical, "pattern": pattern},
            )
            return canonical

    # No match found - return original
    logger.debug(
        "Entity not normalized (no match)",
        extra={"raw": raw_entity},
    )
    return raw_entity


def get_entity_aliases(canonical_entity: str) -> list[str]:
    """Get all known aliases for a canonical entity name.

    Useful for generating SQL ILIKE patterns that match all variations.

    Args:
        canonical_entity: Canonical entity name (e.g., "Portugal")

    Returns:
        List of all raw entity names that map to this canonical entity.

    Example:
        >>> get_entity_aliases("Portugal")
        ['PT', 'Portugal Cement', 'Cimento de Portugal', 'Secil Portugal', ...]
    """
    aliases = []
    for raw, canonical in ENTITY_CANONICAL_MAP.items():
        if canonical == canonical_entity:
            aliases.append(raw)

    # Always include the canonical name itself
    if canonical_entity not in aliases:
        aliases.append(canonical_entity)

    return aliases


def get_entity_exact_match_clause(canonical_entity: str) -> str:
    """Generate SQL IN clause for exact entity matching (no wildcards).

    Story 6.28: Exact matching prevents entity contamination discovered in audit.
    ILIKE '%portugal%' matches 560 rows vs exact match returns ~50 rows.

    Args:
        canonical_entity: Canonical entity name (e.g., "Portugal", "Group")

    Returns:
        SQL IN clause string for use in WHERE clause.

    Example:
        >>> get_entity_exact_match_clause("Portugal")
        "entity IN ('Portugal', 'PT', 'Portugal Cement', ...)"
    """
    # Get all known aliases for this entity
    aliases = get_entity_aliases(canonical_entity)

    if not aliases:
        return f"entity = '{canonical_entity}'"

    # Use exact IN clause - no wildcards
    quoted_aliases = [f"'{alias}'" for alias in aliases]
    return f"entity IN ({', '.join(quoted_aliases)})"


def get_entity_ilike_pattern(canonical_entity: str, escape_percent: bool = True) -> str:
    """Generate SQL ILIKE ANY pattern for an entity and all its aliases.

    Phase 2.1: Creates a PostgreSQL ILIKE ANY clause for fuzzy matching
    all entity variations.

    Story 6.10.3 Fix: Added escape_percent parameter to handle psycopg2's
    % interpretation when using parameterized queries. When the pattern is
    used in a query with %s placeholders, % must be escaped as %%.

    Args:
        canonical_entity: Canonical entity name (e.g., "Portugal")
        escape_percent: If True (default), escape % as %% for psycopg2 compatibility.
            Set to False if using non-parameterized queries.

    Returns:
        SQL pattern string for use in WHERE clause.

    Example:
        >>> get_entity_ilike_pattern("Portugal")
        "entity ILIKE ANY(ARRAY['%%Portugal%%', '%%PT%%', '%%Cimento de Portugal%%'])"
    """
    aliases = get_entity_aliases(canonical_entity)

    # Use %% for psycopg2 compatibility (escapes to single % in final SQL)
    pct = "%%" if escape_percent else "%"

    if not aliases:
        return f"entity ILIKE '{pct}{canonical_entity}{pct}'"

    # Create ILIKE patterns for each alias
    patterns = [f"'{pct}{alias}{pct}'" for alias in aliases]
    return f"entity ILIKE ANY(ARRAY[{', '.join(patterns)}])"


def get_all_canonical_entities() -> list[str]:
    """Get list of all canonical entity names.

    Returns:
        Sorted list of unique canonical entity names.

    Example:
        >>> get_all_canonical_entities()
        ['Angola', 'Brazil', 'Cape Verde', 'Cement', 'Cimpor', 'Group', ...]
    """
    return sorted(set(ENTITY_CANONICAL_MAP.values()))


# Entity synonym dictionary for query expansion (mirrors METRIC_SYNONYMS pattern)
ENTITY_SYNONYMS: dict[str, list[str]] = {
    "portugal": ["Portugal", "PT", "Portugal Cement", "Secil Portugal"],
    "brazil": ["Brazil", "BR", "Brasil", "Brazil Cement", "Secil Brazil"],
    "tunisia": ["Tunisia", "TN", "Tunisie", "Tunisia Cement", "Secil Tunisia"],
    "lebanon": ["Lebanon", "LB", "Liban", "Lebanon Cement", "Secil Lebanon"],
    "angola": ["Angola", "AO", "Angola Cement", "Secil Angola"],
    "cape verde": ["Cape Verde", "CV", "Cabo Verde", "Cape Verde Cement"],
    "group": ["Group", "Conso", "Consolidated", "Total", "Secil GROUP"],
    "ready-mix": ["Ready-Mix", "RMC", "Ready Mix", "Concrete", "Betão Pronto"],
    "cement": ["Cement", "Cement Unit", "Cimento"],
    "trading": ["Trading", "Secil Trading", "Cimpor Trading"],
}


def expand_entity_synonyms(query: str) -> list[str]:
    """Expand user query terms to database entity names using synonym dictionary.

    Phase 2.1: This function enables SQL queries to find entities even when users
    use different terminology than what's stored in the database.

    Args:
        query: Natural language query from user

    Returns:
        List of expanded entity names that should be searched in the database.
        Returns empty list if no synonyms match.

    Example:
        >>> expand_entity_synonyms("What is the revenue for Portugal?")
        ['Portugal', 'PT', 'Portugal Cement', 'Secil Portugal']
    """
    expanded: list[str] = []
    query_lower = query.lower()

    for user_term, db_terms in ENTITY_SYNONYMS.items():
        # Check if user term appears in the query
        if user_term in query_lower:
            # Add all database terms for this synonym
            for term in db_terms:
                if term not in expanded:
                    expanded.append(term)

    logger.debug(
        "Entity synonyms expanded",
        extra={
            "query": query[:100],
            "expanded_count": len(expanded),
            "expanded_terms": expanded[:10] if expanded else [],
        },
    )

    return expanded
