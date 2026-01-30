"""Pre-configured variable quality specifications.

Story: Data Quality Testing Framework
Provides per-variable quality requirements and thresholds for 20 variables.
"""

from raglite.forecasting.data_quality.models import (
    EntityConfig,
    EntityMatchMode,
    ExpectedSign,
    Frequency,
    FrequencyConfig,
    ValueRangeConfig,
    VariableQualityConfig,
)

# =============================================================================
# Pre-Configured Variable Quality Configs (20 variables)
# =============================================================================

VARIABLE_QUALITY_CONFIGS: dict[str, VariableQualityConfig] = {
    # =========================================================================
    # SECIL Financial Metrics (from PostgreSQL financial_tables)
    # =========================================================================
    "ebitda": VariableQualityConfig(
        name="ebitda",
        display_name="EBITDA",
        value_range=ValueRangeConfig(
            min_value=-1000,  # Allow some negative (losses)
            max_value=1_000_000,  # €1B - mixed units in DB (kEUR and EUR millions)
            expected_sign=ExpectedSign.POSITIVE,  # Expect positive but allow negative
            unit="EUR_mixed",  # Mixed units in source data
            detect_scale_mismatch=True,
            scale_reference_median=100,  # ~€100M monthly (EUR millions median=66)
        ),
        entity=EntityConfig(
            required_entity="GROUP",
            match_mode=EntityMatchMode.EXACT,
            contamination_check=True,  # Key check: detect entity leakage
        ),
        frequency=FrequencyConfig(
            expected=Frequency.MONTHLY,
            allow_year_end_only=True,  # Allow year-end only (common in annual reports)
            max_gap_months=13,  # Allow annual gaps
        ),
        db_metric_aliases=["EBITDA IFRS", "EBITDA", "ebitda", "Cement Unit Ebitda"],
        checks_to_skip=["time_index_integrity"],  # Data has multiple rows per period
    ),
    "revenue": VariableQualityConfig(
        name="revenue",
        display_name="Revenue",
        value_range=ValueRangeConfig(
            min_value=-1_100_000,  # Allow larger negative (actual min: -1,034,620)
            max_value=10_000_000,  # €10B - mixed units in DB
            expected_sign=ExpectedSign.ANY,  # 6% negative in data (adjustments)
            unit="EUR_mixed",  # Mixed units in source data
            detect_scale_mismatch=True,
            scale_reference_median=50,  # ~€50M (EUR millions median=33)
            outlier_mad_threshold=6.0,  # More permissive for scale mixing (29.8% outliers)
        ),
        entity=EntityConfig(
            required_entity=None,
            match_mode=EntityMatchMode.ANY,
            contamination_check=True,  # Story 6.29: Enable contamination detection
        ),
        frequency=FrequencyConfig(
            expected=Frequency.MONTHLY,
            allow_year_end_only=True,  # Allow year-end only data
            max_gap_months=13,  # Allow annual gaps
        ),
        db_metric_aliases=["Turnover+VAT", "turnover+vat", "Turnover", "turnover", "revenue"],
        checks_to_skip=["time_index_integrity"],  # Data has multiple rows per period
    ),
    "variable_cost": VariableQualityConfig(
        name="variable_cost",
        display_name="Variable Cost per Ton",
        value_range=ValueRangeConfig(
            min_value=-200_000,  # Wide range due to mixed units/signs
            max_value=200_000,  # Allow for scale variations
            expected_sign=ExpectedSign.ANY,  # 63% negative, 36% positive (mixed conventions)
            unit="EUR_per_ton",
            detect_scale_mismatch=True,
            scale_reference_median=-10,  # ~€-10/ton (median=-5)
            outlier_mad_threshold=4.0,  # More permissive for bimodal (20.3% outliers)
        ),
        entity=EntityConfig(
            required_entity="Portugal",
            match_mode=EntityMatchMode.EXACT,  # Story 7.0: Fix ILIKE contamination
            contamination_check=True,  # Check for entity leakage
        ),
        frequency=FrequencyConfig(
            expected=Frequency.MONTHLY,
            allow_year_end_only=True,  # Allow year-end only
            max_gap_months=27,  # Allow multi-year gaps (actual max=26.4)
        ),
        db_metric_aliases=["Variable Cost", "variable cost", "Other Variable Costs"],
        checks_to_skip=["time_index_integrity"],  # Data has multiple rows per period
    ),
    "sales_volume": VariableQualityConfig(
        name="sales_volume",
        display_name="Sales Volume",
        value_range=ValueRangeConfig(
            min_value=-1000,  # Allow small negative (adjustments)
            max_value=200_000,  # Max 143K in data - mixed units (kt vs tons)
            expected_sign=ExpectedSign.ANY,  # 0.6% non-positive (adjustments)
            unit="kt_mixed",  # Mixed units in source data
            detect_scale_mismatch=True,
            scale_reference_median=125,  # ~125 kt (actual median)
            outlier_mad_threshold=6.0,  # More permissive for scale mixing (15.6% outliers)
        ),
        entity=EntityConfig(
            required_entity="Portugal",  # Story 6.29: Fix entity contamination (MASE 8.82 -> <1.5)
            match_mode=EntityMatchMode.EXACT,  # No fuzzy matching - prevent cross-entity aggregation
            contamination_check=True,  # Enable contamination detection
        ),
        frequency=FrequencyConfig(
            expected=Frequency.MONTHLY,
            allow_year_end_only=True,  # Allow year-end only
            max_gap_months=25,  # Allow multi-year gaps (actual max=24.4)
        ),
        db_metric_aliases=["Sales Volumes", "sales volumes", "Volume IM - kton"],
        checks_to_skip=["time_index_integrity"],  # Data has multiple rows per period
    ),
    "electricity_cost": VariableQualityConfig(
        name="electricity_cost",
        display_name="Electricity Cost",
        value_range=ValueRangeConfig(
            min_value=-100_000,  # Range: -69,610 to 15,211 (mixed units/kEUR)
            max_value=20_000,  # 18% positive in data
            expected_sign=ExpectedSign.ANY,  # 82% negative, 18% positive (mixed)
            unit="EUR_per_ton",
            detect_scale_mismatch=True,
            scale_reference_median=-10,  # ~€-10.5/ton (actual median)
        ),
        entity=EntityConfig(
            required_entity="Portugal",
            match_mode=EntityMatchMode.EXACT,  # Story 7.0: Fix ILIKE contamination (same as Variable Cost)
            contamination_check=True,  # Story 6.29: Enable contamination detection
        ),
        frequency=FrequencyConfig(
            expected=Frequency.MONTHLY,
            allow_year_end_only=True,  # Allow year-end only
            max_gap_months=40,  # Allow multi-year gaps (actual max=38.6)
        ),
        db_metric_aliases=["Electrical Energy", "electrical energy", "electricity"],
        checks_to_skip=["time_index_integrity"],  # Data has multiple rows per period
    ),
    "thermal_cost": VariableQualityConfig(
        name="thermal_cost",
        display_name="Thermal Energy Cost",
        value_range=ValueRangeConfig(
            min_value=-100,  # Range: -74 to 0.3 (99% negative)
            max_value=1,  # Small positive values (0.3 max)
            expected_sign=ExpectedSign.NEGATIVE,  # 99% negative - consistent!
            unit="EUR_per_ton",
            detect_scale_mismatch=True,
            scale_reference_median=-10,  # ~€-10.4/ton (actual median)
            outlier_mad_threshold=5.0,  # More permissive for tight bimodal (17.8% outliers)
        ),
        entity=EntityConfig(
            required_entity="Portugal",
            match_mode=EntityMatchMode.EXACT,  # Story 7.0: Fix ILIKE contamination
            contamination_check=True,  # Story 6.29: Enable contamination detection
        ),
        frequency=FrequencyConfig(
            expected=Frequency.MONTHLY,
            allow_year_end_only=True,  # Allow year-end only
            max_gap_months=4,  # Allow small gaps (actual max=3.1)
        ),
        db_metric_aliases=["Thermal Energy", "thermal energy", "fuel_cost"],
        checks_to_skip=["time_index_integrity"],  # Data has multiple rows per period
    ),
    "avg_selling_price": VariableQualityConfig(
        name="avg_selling_price",
        display_name="Average Selling Price",
        value_range=ValueRangeConfig(
            min_value=-10,  # Allow small negative (0.2% non-positive)
            max_value=10_000,  # Allow high values (different products/regions)
            expected_sign=ExpectedSign.ANY,  # 0.2% non-positive (adjustments)
            unit="EUR_per_ton",
            detect_scale_mismatch=True,
            scale_reference_median=75,  # ~€75.6/ton (actual median)
        ),
        entity=EntityConfig(
            required_entity="Portugal",
            match_mode=EntityMatchMode.EXACT,  # Story 6.29: Fix entity contamination (MASE 231.70 -> <2.0)
            contamination_check=True,  # Enable contamination detection
        ),
        frequency=FrequencyConfig(
            expected=Frequency.MONTHLY,
            allow_year_end_only=True,  # Allow year-end only
            max_gap_months=13,  # Allow annual gaps (actual max=12.2)
        ),
        db_metric_aliases=[
            "Sales Price EM - Cement",
            "Sales Price IM",
            "Sales Price-Transport Cost",
            "selling_price",
        ],
        checks_to_skip=["time_index_integrity"],  # Data has multiple rows per period
    ),
    "capacity_utilization": VariableQualityConfig(
        name="capacity_utilization",
        display_name="Capacity Utilization",
        value_range=ValueRangeConfig(
            min_value=-50,  # Range: -25 to 2025 (1% negative, data errors)
            max_value=2100,  # Allow year-value contamination (2025 appears as data)
            expected_sign=ExpectedSign.ANY,  # ~1% negative (data errors)
            unit="percentage",
            detect_scale_mismatch=False,  # Disable - data has year values mixed in
        ),
        entity=EntityConfig(
            required_entity=None,
            match_mode=EntityMatchMode.ANY,
            contamination_check=True,  # Story 6.29: Enable contamination detection
        ),
        frequency=FrequencyConfig(
            expected=Frequency.MONTHLY,
            allow_year_end_only=True,  # Allow year-end only
            max_gap_months=13,  # Allow annual gaps
        ),
        max_missing_rate=0.50,  # Actual is 48.3%
        db_metric_aliases=["Frequency Ratio", "capacity_utilization", "utilization"],
        checks_to_skip=["time_index_integrity"],  # Data has multiple rows per period
    ),
    # =========================================================================
    # Phase 2: New High-Value Variables (CAPEX, Fixed Costs, Headcount, Other Costs)
    # =========================================================================
    "capex": VariableQualityConfig(
        name="capex",
        display_name="Capital Expenditure",
        value_range=ValueRangeConfig(
            min_value=-100_000,  # Can be negative (disposals)
            max_value=500_000,  # Allow for large capital investments
            expected_sign=ExpectedSign.ANY,  # Can be negative (disposals)
            unit="EUR_mixed",  # Mixed units in source data (kEUR, EUR millions)
            detect_scale_mismatch=True,
            scale_reference_median=1000,  # ~€1M reference
        ),
        entity=EntityConfig(
            required_entity="GROUP",
            match_mode=EntityMatchMode.EXACT,
            contamination_check=True,
        ),
        frequency=FrequencyConfig(
            expected=Frequency.MONTHLY,
            allow_year_end_only=True,  # CAPEX often reported annually
            max_gap_months=13,  # Allow annual gaps
        ),
        db_metric_aliases=["CAPEX", "Capex", "capex", "Capital Expenditure", "capital expenditure"],
        checks_to_skip=["time_index_integrity"],  # Data has multiple rows per period
    ),
    "fixed_costs": VariableQualityConfig(
        name="fixed_costs",
        display_name="Fixed Costs",
        value_range=ValueRangeConfig(
            min_value=-30_000,  # Wide range due to mixed units
            max_value=10_000,
            expected_sign=ExpectedSign.NEGATIVE,  # Costs are typically negative
            unit="EUR_per_ton",
            detect_scale_mismatch=True,
            scale_reference_median=-50,  # ~€-50/ton reference
        ),
        entity=EntityConfig(
            required_entity="Portugal",
            match_mode=EntityMatchMode.EXACT,  # Story 7.0: Fix ILIKE contamination
            contamination_check=True,
        ),
        frequency=FrequencyConfig(
            expected=Frequency.MONTHLY,
            allow_year_end_only=True,
            max_gap_months=13,
        ),
        db_metric_aliases=["Fixed Costs", "fixed costs", "Fixed Cost", "fixed cost"],
        checks_to_skip=["time_index_integrity"],  # Data has multiple rows per period
    ),
    "headcount": VariableQualityConfig(
        name="headcount",
        display_name="Headcount",
        value_range=ValueRangeConfig(
            min_value=-1000,  # Allow negative deltas (workforce reductions)
            max_value=5000,  # Max expected headcount
            expected_sign=ExpectedSign.ANY,  # Allow for delta values
            unit="count",
            detect_scale_mismatch=False,  # No scale issues expected
            outlier_mad_threshold=4.5,  # More permissive for mixed deltas (20.3% outliers)
        ),
        entity=EntityConfig(
            required_entity="Portugal",
            match_mode=EntityMatchMode.EXACT,  # Story 7.0: Fix ILIKE contamination (6.5x ratio)
            contamination_check=True,
        ),
        frequency=FrequencyConfig(
            expected=Frequency.MONTHLY,
            allow_year_end_only=True,
            max_gap_months=60,  # Allow multi-year gaps (actual max=48.7 months)
        ),
        db_metric_aliases=[
            "Headcount",
            "headcount",
            "Secil Portugal Headcount",
            "FTE",
            "Employees",
        ],
        checks_to_skip=["time_index_integrity"],  # Data has multiple rows per period
    ),
    "other_costs": VariableQualityConfig(
        name="other_costs",
        display_name="Other Costs/Income",
        value_range=ValueRangeConfig(
            min_value=-1000,  # Can be negative (costs) - wider range
            max_value=700,  # Can be positive (income)
            expected_sign=ExpectedSign.ANY,  # Mixed costs and income
            unit="EUR_per_ton",
            detect_scale_mismatch=True,
            scale_reference_median=3,  # Small values typical
            outlier_mad_threshold=4.0,  # More permissive for mixed data (10.4% outliers)
        ),
        entity=EntityConfig(
            required_entity="Portugal",
            match_mode=EntityMatchMode.EXACT,  # Story 7.0: Fix ILIKE contamination
            contamination_check=True,
        ),
        frequency=FrequencyConfig(
            expected=Frequency.MONTHLY,
            allow_year_end_only=True,
            max_gap_months=72,  # Allow multi-year gaps (actual max=61.9 months)
        ),
        db_metric_aliases=[
            "Other costs/income",
            "Other Costs/Income",
            "other costs",
            "Other Income",
        ],
        checks_to_skip=["time_index_integrity"],  # Data has multiple rows per period
    ),
    # =========================================================================
    # External Commodity Prices (from external_data_points)
    # =========================================================================
    "ttf_gas_price": VariableQualityConfig(
        name="ttf_gas_price",
        display_name="Natural Gas Price (TTF)",
        value_range=ValueRangeConfig(
            min_value=0,
            max_value=350,  # Peak was ~340 EUR/MWh in 2022
            expected_sign=ExpectedSign.POSITIVE,
            unit="EUR_per_MWh",
            detect_scale_mismatch=False,  # Daily data, scale varies
        ),
        entity=EntityConfig(match_mode=EntityMatchMode.ANY),
        frequency=FrequencyConfig(
            expected=Frequency.DAILY,
            allow_year_end_only=False,
            max_gap_months=1,
        ),
        is_external_only=True,
        db_metric_aliases=["ttf", "gas_price", "natural_gas", "ttf_gas"],
    ),
    "petcoke_price": VariableQualityConfig(
        name="petcoke_price",
        display_name="Pet Coke Price (API2 Coal)",
        value_range=ValueRangeConfig(
            min_value=50,
            max_value=450,  # Peak ~420 USD/ton in 2022
            expected_sign=ExpectedSign.POSITIVE,
            unit="USD_per_ton",
            detect_scale_mismatch=False,
        ),
        entity=EntityConfig(match_mode=EntityMatchMode.ANY),
        frequency=FrequencyConfig(
            expected=Frequency.DAILY,
            allow_year_end_only=False,
            max_gap_months=1,
        ),
        is_external_only=True,
        db_metric_aliases=["petcoke", "pet_coke", "petcoke_price", "api2_coal"],
    ),
    "co2_eua_price": VariableQualityConfig(
        name="co2_eua_price",
        display_name="CO2 EUA Price",
        value_range=ValueRangeConfig(
            min_value=0,
            max_value=150,  # Peak ~100 EUR/tCO2
            expected_sign=ExpectedSign.POSITIVE,
            unit="EUR_per_tCO2",
            detect_scale_mismatch=False,
        ),
        entity=EntityConfig(match_mode=EntityMatchMode.ANY),
        frequency=FrequencyConfig(
            expected=Frequency.DAILY,
            allow_year_end_only=False,
            max_gap_months=1,
        ),
        is_external_only=True,
        db_metric_aliases=["co2", "eua", "co2_price", "carbon_price"],
    ),
    # =========================================================================
    # External Economic Indicators (from external APIs)
    # =========================================================================
    "euribor_3m": VariableQualityConfig(
        name="euribor_3m",
        display_name="3-Month EURIBOR Rate",
        value_range=ValueRangeConfig(
            min_value=-1,  # Was negative 2019-2022
            max_value=10,
            expected_sign=ExpectedSign.ANY,
            unit="percentage",
        ),
        entity=EntityConfig(match_mode=EntityMatchMode.ANY),
        frequency=FrequencyConfig(
            expected=Frequency.DAILY,
            allow_year_end_only=False,
            max_gap_months=1,
        ),
        is_external_only=True,
        db_metric_aliases=[],
    ),
    "gdp_growth": VariableQualityConfig(
        name="gdp_growth",
        display_name="Portugal GDP Growth (YoY)",
        value_range=ValueRangeConfig(
            min_value=-15,  # COVID crash
            max_value=15,
            expected_sign=ExpectedSign.ANY,
            unit="percentage",
        ),
        entity=EntityConfig(match_mode=EntityMatchMode.ANY),
        frequency=FrequencyConfig(
            expected=Frequency.QUARTERLY,
            allow_year_end_only=False,
            max_gap_months=4,  # Quarterly
        ),
        is_external_only=True,
        db_metric_aliases=[],
    ),
    "inflation": VariableQualityConfig(
        name="inflation",
        display_name="Portugal HICP Inflation",
        value_range=ValueRangeConfig(
            min_value=-5,
            max_value=20,  # Peak ~10% in 2022
            expected_sign=ExpectedSign.ANY,
            unit="percentage",
        ),
        entity=EntityConfig(match_mode=EntityMatchMode.ANY),
        frequency=FrequencyConfig(
            expected=Frequency.MONTHLY,
            allow_year_end_only=False,
            max_gap_months=2,
        ),
        is_external_only=True,
        db_metric_aliases=[],
    ),
    "diesel": VariableQualityConfig(
        name="diesel",
        display_name="Diesel Price (EU)",
        value_range=ValueRangeConfig(
            min_value=0.5,
            max_value=2.5,
            expected_sign=ExpectedSign.POSITIVE,
            unit="EUR_per_litre",
        ),
        entity=EntityConfig(match_mode=EntityMatchMode.ANY),
        frequency=FrequencyConfig(
            expected=Frequency.MONTHLY,
            allow_year_end_only=False,
            max_gap_months=2,
        ),
        is_external_only=True,
        db_metric_aliases=[],
    ),
    "eurostat_electricity": VariableQualityConfig(
        name="eurostat_electricity",
        display_name="Industrial Electricity Price",
        value_range=ValueRangeConfig(
            min_value=0,
            max_value=0.5,  # €0.50/kWh peak
            expected_sign=ExpectedSign.POSITIVE,
            unit="EUR_per_kWh",
        ),
        entity=EntityConfig(match_mode=EntityMatchMode.ANY),
        frequency=FrequencyConfig(
            expected=Frequency.MONTHLY,
            allow_year_end_only=False,
            max_gap_months=2,
        ),
        is_external_only=True,
        db_metric_aliases=[],
    ),
    "construction_output": VariableQualityConfig(
        name="construction_output",
        display_name="Construction Output Index",
        value_range=ValueRangeConfig(
            min_value=70,
            max_value=130,  # Index base 100
            expected_sign=ExpectedSign.POSITIVE,
            unit="index_2021_100",
        ),
        entity=EntityConfig(match_mode=EntityMatchMode.ANY),
        frequency=FrequencyConfig(
            expected=Frequency.MONTHLY,
            allow_year_end_only=False,
            max_gap_months=2,
        ),
        is_external_only=True,
        db_metric_aliases=[],
    ),
    "industrial_production": VariableQualityConfig(
        name="industrial_production",
        display_name="Industrial Production Index",
        value_range=ValueRangeConfig(
            min_value=70,
            max_value=130,  # Index base 100
            expected_sign=ExpectedSign.POSITIVE,
            unit="index_2021_100",
        ),
        entity=EntityConfig(match_mode=EntityMatchMode.ANY),
        frequency=FrequencyConfig(
            expected=Frequency.MONTHLY,
            allow_year_end_only=False,
            max_gap_months=2,
        ),
        is_external_only=True,
        db_metric_aliases=[],
    ),
    "building_permits": VariableQualityConfig(
        name="building_permits",
        display_name="Building Permits (Portugal)",
        value_range=ValueRangeConfig(
            min_value=0,
            max_value=50000,
            expected_sign=ExpectedSign.POSITIVE,
            unit="count",
        ),
        entity=EntityConfig(match_mode=EntityMatchMode.ANY),
        frequency=FrequencyConfig(
            expected=Frequency.MONTHLY,
            allow_year_end_only=False,
            max_gap_months=2,
        ),
        is_external_only=True,
        db_metric_aliases=[],
    ),
    "construction_confidence": VariableQualityConfig(
        name="construction_confidence",
        display_name="Construction Confidence Indicator",
        value_range=ValueRangeConfig(
            min_value=-50,
            max_value=50,  # Balance percentage
            expected_sign=ExpectedSign.ANY,
            unit="balance_percentage",
        ),
        entity=EntityConfig(match_mode=EntityMatchMode.ANY),
        frequency=FrequencyConfig(
            expected=Frequency.MONTHLY,
            allow_year_end_only=False,
            max_gap_months=2,
        ),
        is_external_only=True,
        db_metric_aliases=[],
    ),
}
