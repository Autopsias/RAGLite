"""TFT training job for APScheduler.

Story 6.14 AC3: Weekly TFT training job (Sunday 2am UTC, before backtest at 3am).

This module provides a facade for backward compatibility during refactoring.
"""

# Re-export all public items for backward compatibility
from .job_scheduler import (
    _execute_tft_training_job,
    _test_job_status,
    _test_training_data,
    create_tft_training_job,
)
from .job_status import get_training_job_status
from .test_helpers import execute_tft_training
from .weekly_training import MIN_DATA_POINTS, run_weekly_tft_training

__all__ = [
    "MIN_DATA_POINTS",
    "_execute_tft_training_job",
    "_test_job_status",
    "_test_training_data",
    "create_tft_training_job",
    "execute_tft_training",
    "get_training_job_status",
    "run_weekly_tft_training",
]
