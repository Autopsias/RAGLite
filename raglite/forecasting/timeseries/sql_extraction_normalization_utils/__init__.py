"""Utilities for SQL extraction normalization."""

from __future__ import annotations

# Import from sibling file to avoid circular import
import sys
from pathlib import Path

# Add parent directory to path to import sibling module
_parent_dir = Path(__file__).resolve().parent.parent
if str(_parent_dir) not in sys.path:
    sys.path.insert(0, str(_parent_dir))

from sql_extraction_normalization_utils import (  # noqa: E402
    filter_year_end_only_points,
    interpolate_missing_months,
)

from ._normalization import (  # noqa: E402
    normalize_ebitda_pre_ytd,
    normalize_units_and_filter_outliers,
)
from ._postprocessing import apply_percentage_bounds, convert_cost_to_absolute  # noqa: E402
from ._preprocessing import convert_ytd_to_monthly, deduplicate_points  # noqa: E402

__all__ = [
    "deduplicate_points",
    "convert_ytd_to_monthly",
    "normalize_ebitda_pre_ytd",
    "normalize_units_and_filter_outliers",
    "apply_percentage_bounds",
    "convert_cost_to_absolute",
    "filter_year_end_only_points",
    "interpolate_missing_months",
]
