"""CatBoost hyperparameter configuration.

Story 6.12: CatBoost default hyperparameter grid for time-series forecasting.
"""

# Story 6.12: CatBoost default hyperparameter grid
# CatBoost parameters tuned for time-series forecasting with categorical support
CATBOOST_PARAM_GRID = {
    "iterations": [300, 500, 800],
    "learning_rate": [0.01, 0.03, 0.1],
    "depth": [4, 6, 8],
    "l2_leaf_reg": [1, 3, 5],
}

# Fast mode for testing (reduced grid)
CATBOOST_PARAM_GRID_FAST = {
    "iterations": [500],
    "learning_rate": [0.03],
    "depth": [6],
    "l2_leaf_reg": [3],
}
