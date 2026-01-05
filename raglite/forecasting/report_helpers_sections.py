"""Report section generators for validation reports."""

from __future__ import annotations

from typing import Any

import pandas as pd
from structlog import get_logger

from raglite.forecasting.report_helpers_base import (
    MetricAssessment,
    ModelSelectionTable,
    ReportSection,
)
from raglite.shared.models import ForecastResult, ForecastVariable

