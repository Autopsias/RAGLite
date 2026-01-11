"""Internal model selection utilities.

These are private implementation details of model_selection.py,
extracted to reduce the main file size below 500 LOC.
"""

# Re-export for backward compatibility (internal use only)
from .cross_validation import _cv_evaluate, _fit_and_predict
from .regressor_alignment import _align_regressors
from .result_selection import _run_cv_comparison, _select_best_from_results

__all__ = [
    "_cv_evaluate",
    "_fit_and_predict",
    "_align_regressors",
    "_run_cv_comparison",
    "_select_best_from_results",
]
