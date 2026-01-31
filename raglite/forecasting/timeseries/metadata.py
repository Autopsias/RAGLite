"""Timeseries extraction - Constants, exceptions, and utilities.

Part of Story 8.1 refactoring to split timeseries_extract.py.
"""

from typing import TYPE_CHECKING

from raglite.shared.logging import get_logger

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


class ExtractionError(Exception):
    """Exception raised when time-series extraction fails."""

    pass


class UnitMixingError(ExtractionError):
    """Raised when unit mixing is too severe for forecasting.

    Phase 5 enhancement: When value swing exceeds 20x, data quality is too
    poor for reliable forecasting and must be fixed first.

    Attributes:
        metric: Name of the metric with unit mixing
        swing_ratio: Ratio of max/min values
        max_val: Maximum value found
        min_val: Minimum value found
    """

    def __init__(self, metric: str, swing_ratio: float, max_val: float, min_val: float) -> None:
        self.metric = metric
        self.swing_ratio = swing_ratio
        self.max_val = max_val
        self.min_val = min_val
        super().__init__(
            f"Unit mixing too severe for '{metric}': swing={swing_ratio:.1f}x "
            f"(max={max_val:.1f}, min={min_val:.1f}). "
            "Run data quality fixes (scripts/fix_ebitda_scale_v2.py) before forecasting."
        )


class MetricValidationError(ExtractionError):
    """Exception for metric validation failures.

    Story 5.0.4 AC3: Structured error with available metrics list.

    Raised when a metric exists in the database but has insufficient data points
    for reliable forecasting (<8 data points required).

    DATABASE FIX (2025-12-03): Now inherits from ExtractionError to maintain
    backward compatibility with existing test assertions.

    Attributes:
        metric_name: Name of the metric that failed validation
        data_points_found: Number of data points actually found
        minimum_required: Minimum data points required (typically 8)
        available_metrics: List of alternative metrics that have sufficient data
    """

    def __init__(
        self,
        metric_name: str,
        data_points_found: int,
        minimum_required: int,
        available_metrics: list[str],
    ):
        """Initialize MetricValidationError with detailed context.

        Args:
            metric_name: Name of the metric that failed
            data_points_found: Actual number of data points found
            minimum_required: Minimum data points required for forecasting
            available_metrics: List of metrics with sufficient data (for suggestions)
        """
        self.metric_name = metric_name
        self.data_points_found = data_points_found
        self.minimum_required = minimum_required
        self.available_metrics = available_metrics

        # Construct helpful error message
        available_list = ", ".join(available_metrics[:5]) if available_metrics else "none"
        if len(available_metrics) > 5:
            available_list += f" (and {len(available_metrics) - 5} more)"

        super().__init__(
            f"Metric '{metric_name}' has {data_points_found} data points "
            f"(minimum {minimum_required} required for reliable forecasting). "
            f"Available metrics with sufficient data: {available_list}"
        )


EBITDA_ENTITY_PATTERNS = {
    # Geographic entities (consolidated by country)
    # Primary pattern for Qdrant text search - uses "EBITDA IFRS {Country}" format
    # which contains YTD values in newer document formats (Dec 2025+)
    "portugal": "EBITDA IFRS Portugal",
    "tunisia": "EBITDA IFRS Tunisia",
    "angola": "EBITDA IFRS Angola",
    "brazil": "EBITDA IFRS Brazil",
    "lebanon": "EBITDA IFRS Lebanon",
    # Segment totals (not consolidated GROUP)
    "cement_portugal": "Cement EBITDA IFRS",
    "concrete": "Concrete EBITDA IFRS",
    "aggregates": "Aggregates EBITDA IFRS",
}

# Alternate patterns for backward compatibility with older documents
# Some documents use "{Country} EBITDA IFRS" instead of "EBITDA IFRS {Country}"
EBITDA_ENTITY_PATTERNS_ALT = {
    "portugal": "Portugal EBITDA IFRS",
    "tunisia": "Tunisia EBITDA IFRS",
    "angola": "Angola EBITDA IFRS",
    "brazil": "Brazil EBITDA IFRS",
    "lebanon": "Lebanon EBITDA IFRS",
}


EBITDA_VALUE_THRESHOLDS = {
    "portugal": 10000,  # €10M+ YTD
    "tunisia": 5000,  # €5M+ YTD
    "angola": 50000,  # €50M+ YTD
    "brazil": 50000,  # €50M+ YTD
    "lebanon": 500,  # €500K+ YTD
    "cement_portugal": 50000,  # €50M+ YTD
    "concrete": 500,  # Smaller segment
    "aggregates": 5000,  # €5M+ YTD
}


METRIC_CATEGORY_MAP = {
    # Financial metrics
    "revenue": "Revenue",
    "turnover": "Revenue",
    "sales": "Revenue",
    "ebitda": "EBITDA",
    # Volume metrics
    "sales_volume": "Production Volume",
    "production_volume": "Production Volume",
    "capacity_utilization": "Production Volume",
    # Cost metrics
    "variable_cost": "Operating Expenses",
    "operating_expenses": "Operating Expenses",
    "fixed_costs": "Operating Expenses",
    # Other
    "cash_flow": "Cash Flow",
    "capex": "Capital Expenditure",
}


METRIC_SEARCH_PATTERNS = {
    "revenue": ["Turnover", "Revenue"],
    "turnover": ["Turnover", "Revenue"],
    "sales_volume": ["Sales Volumes", "Sales Volume", "Sales kton"],
    "variable_cost": ["Variable Cost", "Variable Costs"],
    "capacity_utilization": ["Frequency Ratio", "Capacity Utilization"],
    "ebitda": ["EBITDA IFRS", "EBITDA"],
    "cash_flow": ["Cash Flow", "Operating Cash Flow"],
    "capex": ["Capital Expenditure", "CAPEX"],
}


ENTITY_PATTERNS = {
    "portugal": ["Portugal", "PT", "Custos Variáveis", "EUR/ton", "EUR/m³"],
    "tunisia": ["Tunisia", "TN", "TND", "Tunisie", "TND/ton"],
    "brazil": ["Brazil", "BR", "BRL", "Brasil", "BRL/ton"],
}


CURRENCY_TO_EUR = {
    "TND": 0.31,  # 1 TND ≈ 0.31 EUR (Tunisian Dinar to Euro)
    "BRL": 0.18,  # 1 BRL ≈ 0.18 EUR (Brazilian Real to Euro)
    "EUR": 1.0,  # 1 EUR = 1 EUR (Portugal, baseline)
}


def detect_entity(text: str) -> str | None:
    """Detect geographic entity from chunk text.

    Story 6.15: Identifies Portugal/Tunisia/Brazil from context patterns
    to filter Variable Cost data by entity.

    Args:
        text: Chunk text to analyze for entity indicators

    Returns:
        Canonical entity name ('portugal', 'tunisia', 'brazil') or None if undetectable

    Example:
        >>> detect_entity("Portugal Variable Cost EUR/ton")
        'portugal'
        >>> detect_entity("Brazil BRL/ton Custos")
        'brazil'
        >>> detect_entity("Unknown text")
        None
    """
    import re

    text_upper = text.upper()

    # Priority order: Check country-specific patterns first (country names, currencies)
    # then fall back to language patterns (which may be shared)

    # Check Tunisia patterns first (most specific: TND currency, Tunisia/Tunisie country names)
    for pattern in ENTITY_PATTERNS["tunisia"]:
        # M1 FIX: Use word boundaries to avoid false positives (e.g., "TN" vs "TNT")
        pattern_upper = pattern.upper()
        if len(pattern_upper) <= 3:  # Short patterns like "TN", "BR", "PT" need word boundaries
            if re.search(rf"\b{re.escape(pattern_upper)}\b", text_upper):
                return "tunisia"
        else:
            if pattern_upper in text_upper:
                return "tunisia"

    # Check Brazil patterns (BRL currency, Brazil/Brasil country name)
    for pattern in ENTITY_PATTERNS["brazil"]:
        pattern_upper = pattern.upper()
        if len(pattern_upper) <= 3:  # Short patterns like "BR" need word boundaries
            if re.search(rf"\b{re.escape(pattern_upper)}\b", text_upper):
                return "brazil"
        else:
            if pattern_upper in text_upper:
                return "brazil"

    # Check Portugal patterns (EUR currency, Portugal/PT)
    # Note: "Custos Variáveis" can appear in both Portugal and Brazil contexts,
    # so we check it last after more specific indicators
    for pattern in ENTITY_PATTERNS["portugal"]:
        pattern_upper = pattern.upper()
        if len(pattern_upper) <= 3:  # Short patterns like "PT" need word boundaries
            if re.search(rf"\b{re.escape(pattern_upper)}\b", text_upper):
                return "portugal"
        else:
            if pattern_upper in text_upper:
                return "portugal"

    return None  # Unknown entity
