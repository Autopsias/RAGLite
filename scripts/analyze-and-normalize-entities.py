#!/usr/bin/env python3
"""Analyze entities and generate canonical name mappings.

This script implements Phase 2 of Migration 001: Hybrid Entity Model.
- Analyzes all distinct entities in financial_tables
- Applies normalization rules based on section context
- Populates entity_mappings dimension table
- Prepares data for entity_normalized column population

Based on production patterns from FinRAG (EMNLP 2024) and Bloomberg NLP.
"""

import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from raglite.shared.clients import get_postgresql_connection
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


# Known country divisions (from section context analysis)
COUNTRY_ENTITIES = {
    "Portugal",
    "Brazil",
    "Tunisia",
    "Lebanon",
    "Angola",
    "Mozambique",
    "South Africa",
    "Egypt",
}

# Group-level entities
GROUP_ENTITIES = {"Group", "Total", "TOTAL"}

# Technical/meta entities (keep as raw)
TECHNICAL_PATTERNS = [
    r"Currency.*",
    r".*Ratio.*",
    r"B Aug-\d{2}",
    r"Aug-\d{2}",
    r".*HEADCOUNT.*",
    r".*Structure.*",
]


def normalize_entity(raw_entity: str, section_context: str | None) -> str | None:
    """
    Generate canonical entity name from raw entity and section context.

    Args:
        raw_entity: Raw entity extracted from table
        section_context: Section heading providing context

    Returns:
        Canonical entity name or None (keep raw)

    Examples:
        normalize_entity("Portugal", "1.1.1 Portugal") → "Portugal Cement"
        normalize_entity("Brazil", "1.1.2 Brazil") → "Brazil Cement"
        normalize_entity("Group", "GROUP TOTAL") → "Secil Group"
        normalize_entity("Currency (1000 EUR)", None) → None
    """
    if not raw_entity:
        return None

    # Pattern 1: Technical entities - keep raw
    for pattern in TECHNICAL_PATTERNS:
        if re.match(pattern, raw_entity, re.IGNORECASE):
            return None

    # Pattern 2: Country divisions
    if raw_entity in COUNTRY_ENTITIES:
        # Check if section context confirms it's a country division
        if section_context and raw_entity in section_context:
            return f"{raw_entity} Cement"
        # Even without section context, known countries get "Cement" suffix
        return f"{raw_entity} Cement"

    # Pattern 3: Group entities
    if raw_entity in GROUP_ENTITIES:
        if raw_entity.upper() == "TOTAL":
            return "Secil Group Total"
        return "Secil Group"

    # Pattern 4: Unknown entities - keep raw (conservative approach)
    return None


def extract_aliases(raw_entity: str, canonical_name: str) -> list[str]:
    """
    Generate alias variations for entity matching.

    Args:
        raw_entity: Raw entity
        canonical_name: Canonical name

    Returns:
        List of alias variations

    Examples:
        extract_aliases("Portugal", "Portugal Cement")
        → ["Portugal", "PT", "Portugal Cem", "Portugal Cement"]
    """
    aliases = [raw_entity]  # Always include raw form

    # Add canonical name
    if canonical_name and canonical_name != raw_entity:
        aliases.append(canonical_name)

    # Add country code for known countries
    country_codes = {
        "Portugal": "PT",
        "Brazil": "BR",
        "Tunisia": "TN",
        "Lebanon": "LB",
        "Angola": "AO",
    }
    if raw_entity in country_codes:
        aliases.append(country_codes[raw_entity])

    # Add abbreviated form of canonical name
    if canonical_name and " " in canonical_name:
        # "Portugal Cement" → "Portugal Cem"
        words = canonical_name.split()
        if len(words) == 2:
            abbreviated = f"{words[0]} {words[1][:3]}"
            aliases.append(abbreviated)

    return list(set(aliases))  # Remove duplicates


def infer_entity_type(raw_entity: str, canonical_name: str | None) -> str:
    """
    Infer entity type for categorization.

    Args:
        raw_entity: Raw entity
        canonical_name: Canonical name (if normalized)

    Returns:
        Entity type: division, country, group, technical

    Examples:
        infer_entity_type("Portugal", "Portugal Cement") → "division"
        infer_entity_type("Group", "Secil Group") → "group"
        infer_entity_type("Currency (1000 EUR)", None) → "technical"
    """
    if raw_entity in COUNTRY_ENTITIES:
        return "division"
    if raw_entity in GROUP_ENTITIES:
        return "group"
    if canonical_name is None:
        return "technical"
    return "entity"


def main() -> None:
    """Analyze entities and build canonical name mappings."""
    logger.info("=" * 80)
    logger.info("ENTITY ANALYSIS & NORMALIZATION")
    logger.info("=" * 80)
    logger.info("")

    conn = get_postgresql_connection()
    cursor = conn.cursor()

    try:
        # Step 1: Analyze distinct entities
        logger.info("Step 1/4: Analyzing distinct entities...")
        cursor.execute("""
            SELECT
                entity,
                COUNT(*) as row_count
            FROM financial_tables
            WHERE entity IS NOT NULL
            GROUP BY entity
            ORDER BY COUNT(*) DESC;
        """)
        entity_data = cursor.fetchall()

        logger.info(f"Found {len(entity_data)} distinct entities")
        logger.info("")

        # Step 2: Generate canonical name mappings
        logger.info("Step 2/4: Generating canonical name mappings...")

        # Entity data is already aggregated
        entity_aggregated: dict[str, tuple[str | None, int]] = {}
        for entity, row_count in entity_data:
            # No section context available, use None
            entity_aggregated[entity] = (None, row_count)

        # Apply normalization rules
        mappings = []
        normalized_count = 0
        raw_count = 0

        for entity, (section_context, row_count) in entity_aggregated.items():
            canonical_name = normalize_entity(entity, section_context)

            if canonical_name:
                normalized_count += 1
                aliases = extract_aliases(entity, canonical_name)
                entity_type = infer_entity_type(entity, canonical_name)

                mappings.append(
                    {
                        "canonical_name": canonical_name,
                        "raw_entity": entity,
                        "aliases": aliases,
                        "entity_type": entity_type,
                        "section_context": None,  # Not available in current schema
                        "row_count": row_count,
                    }
                )
            else:
                raw_count += 1

        logger.info("Normalization results:")
        logger.info(f"  Normalized: {normalized_count} entities")
        logger.info(f"  Raw (kept as-is): {raw_count} entities")
        logger.info(f"  Coverage: {normalized_count / (normalized_count + raw_count) * 100:.1f}%")
        logger.info("")

        # Step 3: Show sample mappings
        logger.info("Step 3/4: Sample canonical name mappings...")
        logger.info("")

        # Group by entity type
        by_type = defaultdict(list)
        for mapping in mappings:
            by_type[mapping["entity_type"]].append(mapping)

        for entity_type, type_mappings in sorted(by_type.items()):
            logger.info(f"{entity_type.upper()} ({len(type_mappings)} entities):")
            for mapping in sorted(type_mappings, key=lambda x: x["row_count"], reverse=True)[:5]:
                logger.info(
                    f"  {mapping['raw_entity']:20} → {mapping['canonical_name']:30} ({mapping['row_count']:,} rows)"
                )
                logger.info(f"    Aliases: {', '.join(mapping['aliases'])}")
            logger.info("")

        # Step 4: Populate entity_mappings table
        logger.info("Step 4/4: Populating entity_mappings dimension table...")

        # Clear existing mappings
        cursor.execute("DELETE FROM entity_mappings")

        # Insert new mappings
        for mapping in mappings:
            cursor.execute(
                """
                INSERT INTO entity_mappings
                    (canonical_name, raw_mentions, entity_type, section_context)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (canonical_name) DO NOTHING;
            """,
                (
                    mapping["canonical_name"],
                    mapping["aliases"],
                    mapping["entity_type"],
                    mapping["section_context"],
                ),
            )

        conn.commit()
        logger.info(f"✅ Inserted {len(mappings)} entity mappings")
        logger.info("")

        # Verification
        logger.info("=" * 80)
        logger.info("VERIFICATION")
        logger.info("=" * 80)

        cursor.execute("SELECT COUNT(*) FROM entity_mappings")
        mapping_count = cursor.fetchone()[0]
        logger.info(f"Total mappings in database: {mapping_count}")

        cursor.execute("""
            SELECT entity_type, COUNT(*) as count
            FROM entity_mappings
            GROUP BY entity_type
            ORDER BY count DESC;
        """)
        type_distribution = cursor.fetchall()

        logger.info("")
        logger.info("Entity type distribution:")
        for entity_type, count in type_distribution:
            logger.info(f"  {entity_type}: {count}")

        logger.info("")
        logger.info("=" * 80)
        logger.info("SUCCESS")
        logger.info("=" * 80)
        logger.info("✅ Entity analysis and normalization complete!")
        logger.info("")
        logger.info("Next step:")
        logger.info("  Run: python scripts/populate-entity-normalized.py")

    except Exception as e:
        logger.error(f"❌ Entity analysis failed: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()
