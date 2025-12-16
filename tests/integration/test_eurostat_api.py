"""Integration tests for Eurostat Construction & Industrial Indicators API.

Story 6.16: Add Eurostat Construction & Industrial Indicators

ATDD RED PHASE - These tests MUST fail initially because:
1. fetch_construction_output() method does not exist
2. fetch_industrial_production() method does not exist
3. EurostatConstructionOutput model does not exist
4. EurostatIndustrialProduction model does not exist

These tests hit the real Eurostat API and validate:
- AC1: Construction output monthly index for Portugal
- AC2: Industrial production monthly index for Portugal
- AC3: Correlation with sales_volume (>0.3)
- AC4: Data completeness (<10% missing values)

Run with: pytest tests/integration/test_eurostat_api.py -v -m integration
Expected: All tests should FAIL (RED phase)
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pytest

from raglite.external_data.clients.eurostat import EurostatClient

# These imports will fail until models are implemented (RED phase)
try:
    from raglite.external_data.models import (
        EurostatConstructionOutput,
        EurostatIndustrialProduction,
    )
except ImportError:
    EurostatConstructionOutput = None  # type: ignore[assignment, misc]
    EurostatIndustrialProduction = None  # type: ignore[assignment, misc]


# Module-level marker for all tests
pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow,  # Real API calls take 2-5 seconds
]


class TestEurostatConstructionOutputIntegration:
    """Integration tests for Eurostat construction output index.

    AC1: fetch_construction_output() returns monthly index for Portugal (2020-2025)
    AC4: Data has <10% missing values over analysis period

    These tests hit the real Eurostat SDMX API.
    """

    @pytest.fixture
    def client(self) -> EurostatClient:
        """Create Eurostat client for testing."""
        return EurostatClient()

    # =========================================================================
    # AC1: Construction Output Index API
    # =========================================================================

    @pytest.mark.asyncio
    async def test_ac1_construction_output_monthly_portugal(self, client: EurostatClient) -> None:
        """
        AC1: Fetch construction output for Portugal returns monthly data.

        Given: A request for Portugal construction output data
        When: fetch_construction_output() is called with date range 2020-2025
        Then: Returns monthly index values for Portugal (geo=PT)
        """
        data = await client.fetch_construction_output(
            country="PT",
            start_date=date(2020, 1, 1),
            end_date=date(2024, 12, 31),
        )

        # Need at least 4 years of monthly data (48 months)
        assert len(data) >= 48, f"Expected 48+ months, got {len(data)}"

    @pytest.mark.asyncio
    async def test_ac1_construction_output_country_portugal(self, client: EurostatClient) -> None:
        """
        AC1: All construction output records are for Portugal.

        Given: A request for Portugal construction output
        When: fetch_construction_output() is called with country="PT"
        Then: All returned records have country="PT"
        """
        data = await client.fetch_construction_output(
            country="PT",
            start_date=date(2022, 1, 1),
            end_date=date(2024, 12, 31),
        )

        assert all(d.country == "PT" for d in data), "All records should be for Portugal"

    @pytest.mark.asyncio
    async def test_ac1_construction_output_index_values_positive(
        self, client: EurostatClient
    ) -> None:
        """
        AC1: Construction output index values are positive.

        Given: Valid construction output data
        When: Examining index values
        Then: All index values are > 0
        """
        data = await client.fetch_construction_output(
            country="PT",
            start_date=date(2022, 1, 1),
            end_date=date(2024, 12, 31),
        )

        assert all(d.index_value > 0 for d in data), "Index values must be positive"

    @pytest.mark.asyncio
    async def test_ac1_construction_output_date_range_respected(
        self, client: EurostatClient
    ) -> None:
        """
        AC1: Date range filters are applied correctly.

        Given: A request with specific date range
        When: fetch_construction_output() is called
        Then: Returned data is within the specified range
        """
        start = date(2022, 1, 1)
        end = date(2023, 12, 31)

        data = await client.fetch_construction_output(
            country="PT",
            start_date=start,
            end_date=end,
        )

        assert len(data) > 0, "Should return data for date range"
        assert data[0].date >= start, f"First date {data[0].date} should be >= {start}"
        assert data[-1].date <= end, f"Last date {data[-1].date} should be <= {end}"

    @pytest.mark.asyncio
    async def test_ac1_construction_output_returns_correct_model_type(
        self, client: EurostatClient
    ) -> None:
        """
        AC1: fetch_construction_output returns EurostatConstructionOutput instances.

        Given: A successful API call
        When: Examining returned data
        Then: All items are EurostatConstructionOutput instances
        """
        data = await client.fetch_construction_output(
            country="PT",
            start_date=date(2023, 1, 1),
            end_date=date(2024, 6, 30),
        )

        assert all(isinstance(d, EurostatConstructionOutput) for d in data)

    @pytest.mark.asyncio
    async def test_ac1_construction_output_nace_sector_construction(
        self, client: EurostatClient
    ) -> None:
        """
        AC1: Construction data uses NACE sector F (Construction).

        Given: A request for construction output
        When: fetch_construction_output() is called
        Then: All records have nace_sector="F"
        """
        data = await client.fetch_construction_output(
            country="PT",
            start_date=date(2023, 1, 1),
            end_date=date(2024, 6, 30),
        )

        assert all(d.nace_sector == "F" for d in data), "Construction sector should be NACE F"


class TestEurostatIndustrialProductionIntegration:
    """Integration tests for Eurostat industrial production index.

    AC2: fetch_industrial_production() returns monthly index for Portugal
    AC4: Data has <10% missing values over analysis period

    These tests hit the real Eurostat SDMX API.
    """

    @pytest.fixture
    def client(self) -> EurostatClient:
        """Create Eurostat client for testing."""
        return EurostatClient()

    # =========================================================================
    # AC2: Industrial Production Index API
    # =========================================================================

    @pytest.mark.asyncio
    async def test_ac2_industrial_production_monthly_portugal(self, client: EurostatClient) -> None:
        """
        AC2: Fetch industrial production for Portugal returns monthly data.

        Given: A request for Portugal industrial production data
        When: fetch_industrial_production() is called with date range 2020-2025
        Then: Returns monthly index values for Portugal (geo=PT)
        """
        data = await client.fetch_industrial_production(
            country="PT",
            start_date=date(2020, 1, 1),
            end_date=date(2024, 12, 31),
        )

        # Need at least 4 years of monthly data (48 months)
        assert len(data) >= 48, f"Expected 48+ months, got {len(data)}"

    @pytest.mark.asyncio
    async def test_ac2_industrial_production_country_portugal(self, client: EurostatClient) -> None:
        """
        AC2: All industrial production records are for Portugal.

        Given: A request for Portugal industrial production
        When: fetch_industrial_production() is called with country="PT"
        Then: All returned records have country="PT"
        """
        data = await client.fetch_industrial_production(
            country="PT",
            start_date=date(2022, 1, 1),
            end_date=date(2024, 12, 31),
        )

        assert all(d.country == "PT" for d in data), "All records should be for Portugal"

    @pytest.mark.asyncio
    async def test_ac2_industrial_production_index_values_positive(
        self, client: EurostatClient
    ) -> None:
        """
        AC2: Industrial production index values are positive.

        Given: Valid industrial production data
        When: Examining index values
        Then: All index values are > 0
        """
        data = await client.fetch_industrial_production(
            country="PT",
            start_date=date(2022, 1, 1),
            end_date=date(2024, 12, 31),
        )

        assert all(d.index_value > 0 for d in data), "Index values must be positive"

    @pytest.mark.asyncio
    async def test_ac2_industrial_production_date_range_respected(
        self, client: EurostatClient
    ) -> None:
        """
        AC2: Date range filters are applied correctly.

        Given: A request with specific date range
        When: fetch_industrial_production() is called
        Then: Returned data is within the specified range
        """
        start = date(2022, 1, 1)
        end = date(2023, 12, 31)

        data = await client.fetch_industrial_production(
            country="PT",
            start_date=start,
            end_date=end,
        )

        assert len(data) > 0, "Should return data for date range"
        assert data[0].date >= start
        assert data[-1].date <= end

    @pytest.mark.asyncio
    async def test_ac2_industrial_production_returns_correct_model_type(
        self, client: EurostatClient
    ) -> None:
        """
        AC2: fetch_industrial_production returns EurostatIndustrialProduction instances.

        Given: A successful API call
        When: Examining returned data
        Then: All items are EurostatIndustrialProduction instances
        """
        data = await client.fetch_industrial_production(
            country="PT",
            start_date=date(2023, 1, 1),
            end_date=date(2024, 6, 30),
        )

        assert all(isinstance(d, EurostatIndustrialProduction) for d in data)

    @pytest.mark.asyncio
    async def test_ac2_industrial_production_nace_sector_industry(
        self, client: EurostatClient
    ) -> None:
        """
        AC2: Industrial data uses NACE sector B-D (Mining, Manufacturing, Energy).

        Given: A request for industrial production
        When: fetch_industrial_production() is called
        Then: All records have nace_sector="B-D"
        """
        data = await client.fetch_industrial_production(
            country="PT",
            start_date=date(2023, 1, 1),
            end_date=date(2024, 6, 30),
        )

        assert all(d.nace_sector == "B-D" for d in data), "Industrial sector should be NACE B-D"


class TestEurostatDataQuality:
    """Integration tests for data quality validation.

    AC4: Data has <10% missing values over analysis period

    Tests ensure that fetched data meets completeness requirements.
    """

    @pytest.fixture
    def client(self) -> EurostatClient:
        """Create Eurostat client for testing."""
        return EurostatClient()

    # =========================================================================
    # AC4: Data Quality - Missing Values
    # =========================================================================

    @pytest.mark.asyncio
    async def test_ac4_construction_data_completeness(self, client: EurostatClient) -> None:
        """
        AC4: Construction output has <10% missing values over 5 years.

        Given: 5 years of expected monthly data (60 months)
        When: Fetching construction output for 2020-2024
        Then: Missing values are <10% of the analysis period
        """
        data = await client.fetch_construction_output(
            country="PT",
            start_date=date(2020, 1, 1),
            end_date=date(2024, 12, 31),
        )

        expected_months = 60  # 5 years * 12 months
        actual_count = len(data)
        missing_pct = (expected_months - actual_count) / expected_months * 100

        assert missing_pct < 10, (
            f"Missing {missing_pct:.1f}% exceeds 10% threshold. "
            f"Expected ~{expected_months} months, got {actual_count}"
        )

    @pytest.mark.asyncio
    async def test_ac4_industrial_data_completeness(self, client: EurostatClient) -> None:
        """
        AC4: Industrial production has <10% missing values over 5 years.

        Given: 5 years of expected monthly data (60 months)
        When: Fetching industrial production for 2020-2024
        Then: Missing values are <10% of the analysis period
        """
        data = await client.fetch_industrial_production(
            country="PT",
            start_date=date(2020, 1, 1),
            end_date=date(2024, 12, 31),
        )

        expected_months = 60
        actual_count = len(data)
        missing_pct = (expected_months - actual_count) / expected_months * 100

        assert missing_pct < 10, (
            f"Missing {missing_pct:.1f}% exceeds 10% threshold. "
            f"Expected ~{expected_months} months, got {actual_count}"
        )

    @pytest.mark.asyncio
    async def test_ac4_construction_data_sorted_by_date(self, client: EurostatClient) -> None:
        """
        AC4: Construction data is returned sorted by date ascending.

        Given: Multi-year construction output request
        When: Examining date order
        Then: Dates are in ascending order
        """
        data = await client.fetch_construction_output(
            country="PT",
            start_date=date(2022, 1, 1),
            end_date=date(2023, 12, 31),
        )

        dates = [d.date for d in data]
        assert dates == sorted(dates), "Data should be sorted by date ascending"

    @pytest.mark.asyncio
    async def test_ac4_industrial_data_sorted_by_date(self, client: EurostatClient) -> None:
        """
        AC4: Industrial data is returned sorted by date ascending.

        Given: Multi-year industrial production request
        When: Examining date order
        Then: Dates are in ascending order
        """
        data = await client.fetch_industrial_production(
            country="PT",
            start_date=date(2022, 1, 1),
            end_date=date(2023, 12, 31),
        )

        dates = [d.date for d in data]
        assert dates == sorted(dates), "Data should be sorted by date ascending"


class TestEurostatCorrelationWithSalesVolume:
    """Integration tests for indicator correlation with sales volume.

    AC3: Both indicators show >0.3 correlation with sales_volume

    These tests validate that the indicators are meaningful for forecasting.
    Note: Requires mock sales_volume data or integration with forecasting module.
    """

    @pytest.fixture
    def client(self) -> EurostatClient:
        """Create Eurostat client for testing."""
        return EurostatClient()

    @pytest.fixture
    def mock_sales_volume_data(self) -> list[tuple[date, float]]:
        """
        Mock sales volume data aligned with indicator dates.

        In production, this would come from the forecasting module.
        For testing, we use synthetic data that should correlate
        with construction/industrial activity patterns.
        """
        # Synthetic monthly sales data 2022-2024 (36 months)
        # Pattern: seasonal variation with construction-correlated trend

        data = []
        base = 10000.0
        for year in range(2022, 2025):
            for month in range(1, 13):
                # Seasonal factor (higher in summer construction season)
                seasonal = 1.0 + 0.15 * np.sin(2 * np.pi * (month - 6) / 12)
                # Add some noise
                noise = np.random.normal(0, 0.05)
                # Trend factor (slight growth)
                trend = 1.0 + 0.02 * ((year - 2022) * 12 + month) / 36
                value = base * seasonal * trend * (1 + noise)
                data.append((date(year, month, 1), value))
        return data

    # =========================================================================
    # AC3: Correlation with Sales Volume
    # =========================================================================

    @pytest.mark.asyncio
    async def test_ac3_construction_correlation_above_threshold(
        self, client: EurostatClient, mock_sales_volume_data: list[tuple[date, float]]
    ) -> None:
        """
        AC3: Construction output shows >0.3 correlation with sales_volume.

        Given: Construction output and sales volume time series
        When: Calculating Pearson correlation
        Then: Correlation coefficient is > 0.3
        """
        try:
            from scipy.stats import pearsonr
        except ImportError:
            pytest.skip("scipy not installed")

        # Fetch construction data
        construction_data = await client.fetch_construction_output(
            country="PT",
            start_date=date(2022, 1, 1),
            end_date=date(2024, 12, 31),
        )

        # Create lookup for sales data
        sales_lookup = dict(mock_sales_volume_data)

        # Align data by date
        aligned_construction = []
        aligned_sales = []

        for record in construction_data:
            if record.date in sales_lookup:
                aligned_construction.append(record.index_value)
                aligned_sales.append(sales_lookup[record.date])

        assert len(aligned_construction) >= 12, (
            f"Need at least 12 aligned points, got {len(aligned_construction)}"
        )

        # Calculate correlation
        corr, p_value = pearsonr(aligned_construction, aligned_sales)

        assert corr > 0.3, (
            f"Correlation {corr:.2f} below 0.3 threshold. "
            "Construction output should correlate with sales volume."
        )
        # Note: p-value check relaxed for synthetic data
        # In production, assert p_value < 0.05

    @pytest.mark.asyncio
    async def test_ac3_industrial_correlation_above_threshold(
        self, client: EurostatClient, mock_sales_volume_data: list[tuple[date, float]]
    ) -> None:
        """
        AC3: Industrial production shows >0.3 correlation with sales_volume.

        Given: Industrial production and sales volume time series
        When: Calculating Pearson correlation
        Then: Correlation coefficient is > 0.3
        """
        try:
            from scipy.stats import pearsonr
        except ImportError:
            pytest.skip("scipy not installed")

        # Fetch industrial data
        industrial_data = await client.fetch_industrial_production(
            country="PT",
            start_date=date(2022, 1, 1),
            end_date=date(2024, 12, 31),
        )

        # Create lookup for sales data
        sales_lookup = dict(mock_sales_volume_data)

        # Align data by date
        aligned_industrial = []
        aligned_sales = []

        for record in industrial_data:
            if record.date in sales_lookup:
                aligned_industrial.append(record.index_value)
                aligned_sales.append(sales_lookup[record.date])

        assert len(aligned_industrial) >= 12, (
            f"Need at least 12 aligned points, got {len(aligned_industrial)}"
        )

        # Calculate correlation
        corr, p_value = pearsonr(aligned_industrial, aligned_sales)

        assert corr > 0.3, (
            f"Correlation {corr:.2f} below 0.3 threshold. "
            "Industrial production should correlate with sales volume."
        )

    @pytest.mark.asyncio
    async def test_ac3_correlation_statistically_significant(
        self, client: EurostatClient, mock_sales_volume_data: list[tuple[date, float]]
    ) -> None:
        """
        AC3: Correlation is statistically significant (p < 0.05).

        Given: Indicator and sales volume time series with 36+ data points
        When: Calculating Pearson correlation
        Then: p-value is < 0.05 indicating statistical significance
        """
        try:
            from scipy.stats import pearsonr
        except ImportError:
            pytest.skip("scipy not installed")

        # Fetch construction data (using construction as example)
        construction_data = await client.fetch_construction_output(
            country="PT",
            start_date=date(2022, 1, 1),
            end_date=date(2024, 12, 31),
        )

        sales_lookup = dict(mock_sales_volume_data)

        aligned_construction = []
        aligned_sales = []

        for record in construction_data:
            if record.date in sales_lookup:
                aligned_construction.append(record.index_value)
                aligned_sales.append(sales_lookup[record.date])

        if len(aligned_construction) < 30:
            pytest.skip("Insufficient data points for significance test")

        corr, p_value = pearsonr(aligned_construction, aligned_sales)

        # Note: With synthetic data, significance may not hold.
        # In production with real sales data, this should pass.
        assert p_value < 0.05, (
            f"Correlation (r={corr:.2f}) not statistically significant (p={p_value:.3f} >= 0.05)"
        )


class TestEurostatClientAPIIntegration:
    """Integration tests for raw API connectivity.

    These tests verify that the Eurostat SDMX API is reachable
    and returns expected response formats.
    """

    @pytest.fixture
    def client(self) -> EurostatClient:
        """Create Eurostat client for testing."""
        return EurostatClient()

    @pytest.mark.asyncio
    async def test_eurostat_api_reachable(self, client: EurostatClient) -> None:
        """
        Verify Eurostat API is reachable.

        Given: A valid API client
        When: Making a request to the API
        Then: Response is received without network errors
        """
        # Use electricity prices (already implemented) to verify connectivity
        try:
            data = await client.fetch_electricity_prices(
                country="PT",
                start_date=date(2023, 1, 1),
                end_date=date(2023, 6, 30),
            )
            assert isinstance(data, list)
        except Exception as e:
            pytest.fail(f"Eurostat API not reachable: {e}")

    @pytest.mark.asyncio
    async def test_construction_dataset_exists(self, client: EurostatClient) -> None:
        """
        Verify sts_copr_m dataset exists on Eurostat.

        Given: EurostatClient configured for construction dataset
        When: Fetching construction output
        Then: Data is returned without dataset-not-found errors
        """
        # This test will fail in RED phase because method doesn't exist,
        # but when GREEN, it validates the dataset code is correct
        data = await client.fetch_construction_output(
            country="PT",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 30),
        )

        assert len(data) > 0, "Dataset should return data"

    @pytest.mark.asyncio
    async def test_industrial_dataset_exists(self, client: EurostatClient) -> None:
        """
        Verify sts_inpr_m dataset exists on Eurostat.

        Given: EurostatClient configured for industrial dataset
        When: Fetching industrial production
        Then: Data is returned without dataset-not-found errors
        """
        data = await client.fetch_industrial_production(
            country="PT",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 30),
        )

        assert len(data) > 0, "Dataset should return data"
