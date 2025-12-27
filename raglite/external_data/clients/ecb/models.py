"""ECB data models.

Story 8.2 Task 5: ECB client refactoring
"""

from dataclasses import dataclass
from datetime import date


@dataclass
class EuriborRate:
    """EURIBOR interest rate data point."""

    date: date
    rate_pct: float  # Interest rate as percentage (e.g., -0.5 or 3.5)
    tenor: str  # "3M", "6M", or "12M"


@dataclass
class ECBGDPGrowth:
    """GDP growth rate data point.

    Story 6.17 AC1: GDP growth for forecasting construction demand.
    """

    date: date
    growth_pct: float  # YoY growth as percentage (e.g., 2.5 for 2.5%)
    country: str  # ISO 2-letter code (PT for Portugal)
    frequency: str = "Q"  # Q=Quarterly, M=Monthly (after interpolation)


@dataclass
class ECBInflation:
    """HICP inflation index data point.

    Story 6.17 AC2: HICP inflation for pricing and cost forecasting.
    """

    date: date
    index_value: float  # HICP index (2015=100)
    country: str  # ISO 2-letter code
    yoy_change_pct: float | None = None  # YoY % change (calculated)
