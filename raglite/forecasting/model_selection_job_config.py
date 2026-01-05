"""
Configuration and constants for model selection job.

This module contains variable configuration, energy crisis regime constants,
and variable lists for batch processing.
"""

import pandas as pd

# Variable configuration for data fetching
# Maps variable names to extraction method and DB aliases
VARIABLE_CONFIG: dict[str, dict] = {
    # Internal SECIL metrics (from financial_tables)
    "revenue": {
        "type": "internal",
        "aliases": ["Turnover+VAT", "Turnover", "turnover", "revenue"],
        "aggregation": "max",
    },
    "ebitda": {
        "type": "internal",
        "aliases": ["EBITDA", "ebitda", "Cement Unit Ebitda"],
        "aggregation": "sum",
    },
    "sales_volume": {
        "type": "internal",
        "aliases": ["Sales Volumes", "sales volumes", "Volume IM - kton"],
        "aggregation": "sum",
    },
    "thermal_cost": {
        "type": "internal",
        "aliases": ["Thermal Energy", "thermal energy", "fuel_cost"],
        "aggregation": "sum",
    },
    "variable_cost": {
        "type": "internal",
        "aliases": ["Variable Cost", "variable cost"],
        "aggregation": "sum",
    },
    "capacity_utilization": {
        "type": "internal",
        "aliases": ["Capacity Utilization", "capacity_utilization", "Ratio"],
        "aggregation": "max",
    },
    "avg_selling_price": {
        "type": "internal",
        "aliases": ["Sales Price IM", "avg_selling_price", "Average Selling Price"],
        "aggregation": "max",
    },
    # External database metrics (from external_data_points)
    "ttf_gas_price": {
        "type": "external_db",
        "metric_name": "ttf_gas_price",
        # HIGH UNCERTAINTY: 2022 energy crisis caused +211% mean shift, 99% CV
        "uncertainty": "high",
        "uncertainty_reason": "2022 energy crisis regime change",
    },
    "petcoke_price": {
        "type": "external_db",
        "metric_name": "petcoke_price",
    },
    "co2_eua_price": {
        "type": "external_db",
        "metric_name": "co2_eua_price",
    },
    # External API metrics (from regressor fetch)
    "electricity_cost": {
        "type": "external_api",
        "metric_name": "ren_electricity",
        # BEST PERFORMER: MASE 0.44 (56% better than naive)
        "quality": "excellent",
        "quality_note": "Best performing variable with MASE 0.44",
    },
    "diesel": {
        "type": "external_api",
        "metric_name": "diesel",
    },
    "api2_coal": {
        "type": "external_api",
        "metric_name": "api2_coal",
        # HIGH UNCERTAINTY: Correlated with energy crisis, 54% CV
        "uncertainty": "high",
        "uncertainty_reason": "2022 energy crisis and geopolitical disruptions",
    },
    # NOTE: eurostat_electricity removed - only 9 semi-annual data points (need 12+)
    # Use electricity_cost (ren_electricity) for Portuguese electricity prices instead
    "gdp_growth": {
        "type": "external_api",
        "metric_name": "gdp_growth",
    },
    "inflation": {
        "type": "external_api",
        "metric_name": "inflation",
    },
    "euribor_3m": {
        "type": "external_api",
        "metric_name": "euribor_3m",
        # HIGH UNCERTAINTY: ECB policy regime change from -0.5% to +4%
        "uncertainty": "high",
        "uncertainty_reason": "ECB rate policy regime change 2022-2023",
    },
    "construction_output": {
        "type": "external_api",
        "metric_name": "construction_output",
    },
    "building_permits": {
        "type": "external_api",
        "metric_name": "building_permits",
        # BEST PERFORMER: MASE 0.79 (21% better than naive)
        "quality": "excellent",
        "quality_note": "Second best performing variable with MASE 0.79",
    },
    "construction_confidence": {
        "type": "external_api",
        "metric_name": "construction_confidence",
    },
    "industrial_production": {
        "type": "external_api",
        "metric_name": "industrial_production",
    },
}

# All variables for batch processing
ALL_VARIABLES = list(VARIABLE_CONFIG.keys())

# Epic 7 Enhancement: Energy crisis regime detection
# Based on Exa research: Structural breaks in energy markets require regime-aware modeling
ENERGY_CRISIS_START = pd.Timestamp("2022-02-01")  # Russia-Ukraine conflict
ENERGY_CRISIS_PEAK = pd.Timestamp("2022-08-31")  # Peak TTF prices
ENERGY_CRISIS_END = pd.Timestamp("2023-06-30")  # Prices stabilized

# Variables that are affected by energy crisis regime
ENERGY_AFFECTED_VARIABLES = [
    "ttf_gas_price",
    "api2_coal",
    "co2_eua_price",
    "electricity_cost",
    "thermal_cost",
    "diesel",
    "euribor_3m",  # ECB rate changes in response to inflation
]
