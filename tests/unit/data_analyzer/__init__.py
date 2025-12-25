"""Data Characteristics Analyzer Test Suite.

This package contains split test modules for the data characteristics analyzer:

AC Tests (from test_data_analyzer.py - 51 tests):
- test_ac1_stationarity.py: 8 tests for AC1 (stationarity detection)
- test_ac2_seasonality.py: 8 tests for AC2 (seasonality detection)
- test_ac3_trend.py: 7 tests for AC3 (trend detection)
- test_ac4_volatility.py: 5 tests for AC4 (volatility measurement)
- test_ac5_quality.py: 5 tests for AC5 (data quality metrics)
- test_ac6_recommendations.py: 12 tests for AC6 (model recommendations)
- test_ac7_exports.py: 6 tests for AC7 (module exports)

Edge Cases (from test_data_analyzer.py - 7 tests):
- test_edge_cases.py: 7 tests for basic edge cases

Expanded Tests (from test_data_analyzer_expanded.py - 35 tests):
- test_boundary_conditions.py: 11 tests for boundary conditions
- test_integration_scenarios.py: 3 tests for component integration
- test_differencing.py: 4 tests for differencing order detection
- test_volatility_edges.py: 3 tests for rolling volatility
- test_error_handling.py: 3 tests for error handling
- test_model_priority.py: 3 tests for model recommendation priority
- test_acf_edges.py: 2 tests for ACF computation
- test_quality_edges.py: 3 tests for data quality edges
- test_rationale_generation.py: 3 tests for rationale strings

Total: 93 tests across 17 modules + 1 conftest.py with 37 shared fixtures

All fixtures are in conftest.py and automatically discovered by pytest.
"""
