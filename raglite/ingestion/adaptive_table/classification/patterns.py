"""
Pattern definitions for table classification.

This module contains financial, entity, and temporal patterns used for
table orientation detection and header classification.
"""

from __future__ import annotations


def _get_general_financial_patterns() -> list[str]:
    """Get general financial and operational metric patterns.

    Returns:
        List of general financial metric pattern strings
    """
    return [
        # Core financial metrics
        "EBITDA",
        "EBIT",
        "Revenue",
        "Sales",
        "Turnover",
        "Margin",
        "Profit",
        "Loss",
        "Cost",
        "Expense",
        "Income",
        "Debt",
        "Cash",
        "Asset",
        "Liability",
        "Equity",
        # Operational metrics
        "Volume",
        "Production",
        "Capacity",
        "Utilization",
        "Efficiency",
        "Productivity",
        # Investment metrics
        "CAPEX",
        "OPEX",
        "Investment",
        "Expenditure",
        "Spending",
        # Market metrics
        "Price",
        "Rate",
        "Ratio",
        "Yield",
        "Return",
        # Performance metrics
        "ROE",
        "ROA",
        "ROI",
        "ROCE",
        "EPS",
        "P/E",
        "Dividend",
        "FCF",
        # Tax & accounting
        "Tax",
        "Depreciation",
        "Amortization",
        "Impairment",
        # Working capital
        "Receivable",
        "Payable",
        "Inventory",
        "Working Capital",
        # Additional patterns
        "Interest",
        "Net",
        "Gross",
        "Operating",
        "COGS",
        "SG&A",
    ]


def _get_cement_industry_patterns() -> list[str]:
    """Get cement industry specific metric patterns.

    Returns:
        List of cement industry metric pattern strings
    """
    return [
        # Fuels - CRITICAL for petcoke queries
        "Petcoke",
        "Pet Coke",
        "Petroleum Coke",
        "Coal",
        "Lignite",
        "Natural Gas",
        "Fuel Oil",
        "Alternative Fuel",
        "AF Rate",
        "Biomass",
        # Production metrics
        "Clinker",
        "Clinker Factor",
        "Clinker Ratio",
        "Slag",
        "Fly Ash",
        "Gypsum",
        "Limestone",
        "Kiln",
        "Raw Mill",
        "Cement Mill",
        # Sustainability
        "CO2",
        "Emissions",
        "Carbon",
        "Scope 1",
        "Scope 2",
        "Scope 3",
        "TSR",
        "Thermal Substitution",
        # Units
        "kcal/kg",
        "GJ/ton",
        "kWh/ton",
        "MTPA",
        "TPD",
    ]


def get_metric_patterns() -> list[str]:
    """Get financial metric patterns for table analysis.

    Returns:
        List of metric pattern strings combining general and industry-specific patterns
    """
    return _get_general_financial_patterns() + _get_cement_industry_patterns()


def get_entity_patterns() -> list[str]:
    """Get entity patterns for table analysis.

    Returns:
        List of entity pattern strings
    """
    return [
        "GROUP",
        "PORTUGAL",
        "ANGOLA",
        "TUNISIA",
        "LEBANON",
        "BRAZIL",
        "Entity",
        "Company",
        "Country",
        "Region",
        "Division",
        "Segment",
        "Business",
        "Unit",
        "Branch",
        "Subsidiary",
        "Cement",
        "Madeira",
        "Cape Verde",
        "Nederland",
        "Secil",
    ]


def get_temporal_patterns() -> list[str]:
    """Get temporal patterns for header analysis.

    Returns:
        List of temporal pattern strings
    """
    return [
        "YTD",
        "Q1",
        "Q2",
        "Q3",
        "Q4",
        "2024",
        "2025",
        "2023",
        "2022",
        "2021",
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
        "Year",
        "Period",
        "Month",
        "Quarter",
        "Budget",
        "B ",
        "Aug-",
    ]
