"""Metric synonym dictionary for query expansion.

Phase 1.2: Maps user query terms to actual database metric names for synonym expansion.
This bridges the gap between how users ask questions and how metrics are stored.
"""

import logging

logger = logging.getLogger(__name__)


# ============================================================================
# METRIC SYNONYMS DICTIONARY (Phase 1.2)
# Maps user query terms to actual database metric names for synonym expansion.
# This bridges the gap between how users ask questions and how metrics are stored.
# ============================================================================

METRIC_SYNONYMS: dict[str, list[str]] = {
    # ===== ENERGY METRICS =====
    "energy consumption": [
        "Electrical Energy",
        "Thermal Energy",
        "Fuel Energy",
        "Energy Cost",
        "Power Consumption",
        "Total Energy",
    ],
    "energy": [
        "Electrical Energy",
        "Thermal Energy",
        "Fuel Energy",
        "Energy Cost",
        "Power Consumption",
        "kWh",
        "MWh",
        "GJ",
    ],
    "electricity": ["Electrical Energy", "Power Consumption", "kWh", "MWh", "Electric"],
    "thermal energy": ["Thermal Energy", "Heat Consumption", "kcal", "GJ", "Thermal"],
    "power": ["Electrical Energy", "Power Consumption", "kWh", "MWh"],
    # ===== FUEL METRICS (CEMENT INDUSTRY) =====
    "petcoke": [
        "Petcoke Consumption",
        "Pet Coke",
        "Petroleum Coke",
        "Petcoke Cost",
        "Petcoke",
        "Pet coke",
    ],
    "petroleum coke": ["Petcoke", "Pet Coke", "Petroleum Coke", "Petcoke Consumption"],
    "coal": ["Coal Consumption", "Coal Cost", "Coal", "Lignite"],
    "fuel cost": ["Fuel Cost", "Petcoke Cost", "Coal Cost", "Energy Cost", "Fuel"],
    "alternative fuels": [
        "AF Rate",
        "Alternative Fuel",
        "Biomass",
        "Waste Fuel",
        "TSR",
        "Thermal Substitution",
    ],
    "af rate": ["AF Rate", "Alternative Fuel Rate", "TSR", "Thermal Substitution Rate"],
    # ===== FINANCIAL METRICS =====
    "working capital": [
        "Trade Working Capital",
        "Net Working Capital",
        "WC",
        "Working Capital/Turnover",
        "Working Capital",
        "Receivables",
        "Payables",
        "Inventory",
    ],
    "debt": [
        "Financial net debt",
        "Net Debt",
        "Gross Debt",
        "Bank Debt",
        "Total Debt",
        "Financial Debt",
    ],
    "net debt": ["Financial net debt", "Net Debt", "Net Financial Debt"],
    "ebitda": [
        "EBITDA IFRS",
        "EBITDA",
        "Cement Unit Ebitda",
        "Ready-Mix Unit Ebitda",
        "Unit EBITDA",
        "EBITDA Margin",
    ],
    "revenue": ["Revenue", "Sales", "Turnover", "Net Revenue", "Total Revenue"],
    "margin": [
        "Margin",
        "EBITDA Margin",
        "Gross Margin",
        "Net Margin",
        "Profit Margin",
    ],
    "cost": [
        "Cost",
        "Variable Cost",
        "Fixed Cost",
        "Total Cost",
        "Unit Cost",
        "Cost per ton",
    ],
    "variable cost": ["Variable Cost", "Variable Costs", "VC", "Variable"],
    "fixed cost": ["Fixed Cost", "Fixed Costs", "FC", "Fixed"],
    # ===== PRODUCTION METRICS (CEMENT INDUSTRY) =====
    "clinker ratio": [
        "Clinker Factor",
        "Clinker/Cement Ratio",
        "Clinker Ratio",
        "Clinker",
    ],
    "clinker": ["Clinker", "Clinker Factor", "Clinker Production", "Clinker Ratio"],
    "capacity utilization": [
        "Plant Utilization",
        "Kiln Utilization",
        "Capacity Rate",
        "Utilization",
        "Capacity",
    ],
    "utilization": [
        "Utilization",
        "Plant Utilization",
        "Kiln Utilization",
        "Capacity Utilization",
    ],
    "kiln utilization": [
        "Kiln Utilization",
        "Kiln Uptime",
        "Kiln Availability",
        "Kiln Operating Rate",
    ],
    "production volume": [
        "Cement Volume",
        "Clinker Production",
        "Production",
        "Volume",
        "Output",
    ],
    "production": [
        "Production",
        "Volume",
        "Output",
        "Cement Production",
        "Clinker Production",
    ],
    # ===== SUSTAINABILITY METRICS =====
    "co2": [
        "CO2",
        "Emissions",
        "Carbon",
        "CO2 per ton",
        "Scope 1",
        "Scope 2",
        "Scope 3",
    ],
    "emissions": [
        "Emissions",
        "CO2",
        "Carbon Emissions",
        "Scope 1",
        "Scope 2",
        "Scope 3",
        "GHG",
    ],
    "carbon": ["Carbon", "CO2", "Emissions", "Carbon Footprint"],
    "scope 1": ["Scope 1", "Scope1", "Direct Emissions"],
    "scope 2": ["Scope 2", "Scope2", "Indirect Emissions"],
    "scope 3": ["Scope 3", "Scope3", "Value Chain Emissions"],
    # ===== COST STRUCTURE =====
    "cost per ton": ["Cost per ton", "Unit Cost", "EUR/ton", "Cost/ton", "$/ton"],
    "fuel consumption": [
        "Fuel Consumption",
        "kcal/kg",
        "GJ/ton",
        "Fuel",
        "Thermal Consumption",
    ],
    "power cost": ["Power Cost", "Electricity Cost", "EUR/MWh", "Energy Cost"],
    # ===== FINANCIAL RATIOS =====
    "ebitda per ton": ["EBITDA per ton", "Unit EBITDA", "EBITDA/ton"],
    "return on capital": ["ROIC", "Return on Invested Capital", "ROI", "ROCE"],
    "leverage": ["Leverage", "Debt/Equity", "Leverage Ratio", "Gearing"],
    "free cash flow": ["Free Cash Flow", "FCF", "Cash Flow"],
}


def expand_metric_synonyms(query: str) -> list[str]:
    """Expand user query terms to database metric names using synonym dictionary.

    Phase 1.2: This function enables SQL queries to find metrics even when users
    use different terminology than what's stored in the database.

    Args:
        query: Natural language query from user

    Returns:
        List of expanded metric names that should be searched in the database.
        Returns empty list if no synonyms match.

    Example:
        >>> expand_metric_synonyms("What is the energy consumption?")
        ['Electrical Energy', 'Thermal Energy', 'Fuel Energy', 'Energy Cost', ...]

        >>> expand_metric_synonyms("Show me petcoke costs")
        ['Petcoke Consumption', 'Pet Coke', 'Petroleum Coke', 'Petcoke Cost', ...]
    """
    expanded: list[str] = []
    query_lower = query.lower()

    for user_term, db_terms in METRIC_SYNONYMS.items():
        # Check if user term appears in the query
        if user_term in query_lower:
            # Add all database terms for this synonym
            for term in db_terms:
                if term not in expanded:
                    expanded.append(term)

    logger.debug(
        "Metric synonyms expanded",
        extra={
            "query": query[:100],
            "expanded_count": len(expanded),
            "expanded_terms": expanded[:10] if expanded else [],  # Log first 10
        },
    )

    return expanded


def get_metric_ilike_pattern(expanded_terms: list[str]) -> str:
    """Generate SQL ILIKE ANY pattern from expanded metric terms.

    Phase 1.2: Creates a PostgreSQL ILIKE ANY clause for fuzzy matching
    multiple metric synonyms.

    Args:
        expanded_terms: List of metric names from expand_metric_synonyms()

    Returns:
        SQL pattern string for use in WHERE clause.

    Example:
        >>> get_metric_ilike_pattern(['Electrical Energy', 'Thermal Energy'])
        "metric ILIKE ANY(ARRAY['%Electrical Energy%', '%Thermal Energy%'])"
    """
    if not expanded_terms:
        return ""

    # Create ILIKE patterns for each term
    patterns = [f"'%{term}%'" for term in expanded_terms]
    return f"metric ILIKE ANY(ARRAY[{', '.join(patterns)}])"
