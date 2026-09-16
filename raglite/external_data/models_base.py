"""Base types and enums for external data sources.

Story 6.1: Tier 1 External Data Source Integration
Epic 8: Technical Debt Reduction - Split from monolithic models.py
"""

from __future__ import annotations

from enum import StrEnum


class DataFrequency(StrEnum):
    """Frequency of data updates."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


class DataSource(StrEnum):
    """External data source identifiers."""

    INE = "INE"
    ATIC = "ATIC"
    BPSTAT = "BPstat"
    OMIE = "OMIE"
    EU_OIL_BULLETIN = "EU_Oil_Bulletin"
    IPMA = "IPMA"
    BASEGOV = "BaseGov"
    COMMODITIES = "Commodities"
