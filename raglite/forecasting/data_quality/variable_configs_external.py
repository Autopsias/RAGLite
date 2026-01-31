"""External variable quality specifications.

Story: Data Quality Testing Framework
Provides per-variable quality requirements for external data sources.
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
# External Commodity Prices (from external_data_points)
# =============================================================================

EXTERNAL_COMMODITY_CONFIGS: dict[str, VariableQualityConfig] = {
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
}

# =============================================================================
# External Economic Indicators (from external APIs)
# =============================================================================

EXTERNAL_ECONOMIC_CONFIGS: dict[str, VariableQualityConfig] = {
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
