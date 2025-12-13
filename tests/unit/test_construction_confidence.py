"""Unit tests for EC construction confidence regressor.

Story 6.19: EC Construction Confidence Index
- AC1: Eurostat Construction Confidence Method
- AC2: Data Model
- AC3: Regressor Integration
"""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, patch

import pandas as pd
import pytest

from raglite.external_data.models import ECConstructionConfidence


class TestECConstructionConfidenceModel:
    """AC2: Data Model tests."""

    def test_model_with_all_fields(self) -> None:
        """AC2.1: Model with all indicators."""
        record = ECConstructionConfidence(
            date=date(2024, 1, 1),
            confidence_index=-4.5,
            employment_expectations=2.8,
            order_books=-10.8,
            country="PT",
        )
        assert record.confidence_index == -4.5
        assert record.employment_expectations == 2.8
        assert record.order_books == -10.8
        assert record.country == "PT"

    def test_model_with_optional_fields_none(self) -> None:
        """AC2.2: Model with only required fields."""
        record = ECConstructionConfidence(
            date=date(2024, 1, 1),
            confidence_index=-4.5,
            country="PT",
        )
        assert record.confidence_index == -4.5
        assert record.employment_expectations is None
        assert record.order_books is None


class TestEurostatConstructionConfidenceMethod:
    """AC1: Eurostat Construction Confidence Method tests."""

    def test_eurostat_client_has_construction_confidence_method(self) -> None:
        """AC1.1: EurostatClient has fetch_construction_confidence method."""
        from raglite.external_data.clients.eurostat import EurostatClient

        client = EurostatClient()
        assert hasattr(client, "fetch_construction_confidence")
        assert callable(client.fetch_construction_confidence)

    def test_eurostat_client_has_correct_dataset(self) -> None:
        """AC1.2: Uses correct dataset code ei_bsbu_m_r2."""
        from raglite.external_data.clients.eurostat import EurostatClient

        assert hasattr(EurostatClient, "CONSTRUCTION_CONFIDENCE_DATASET")
        assert EurostatClient.CONSTRUCTION_CONFIDENCE_DATASET == "ei_bsbu_m_r2"


class TestConstructionConfidenceRegressor:
    """AC3: Regressor Integration tests."""

    @pytest.mark.asyncio
    async def test_construction_confidence_regressor_returns_series(self) -> None:
        """AC3.1: Regressor returns pd.Series with DatetimeIndex."""
        mock_data = [
            ECConstructionConfidence(
                date=date(2024, 1, 1),
                confidence_index=-4.5,
                employment_expectations=2.8,
                order_books=-10.8,
                country="PT",
            ),
            ECConstructionConfidence(
                date=date(2024, 2, 1),
                confidence_index=-3.2,
                employment_expectations=3.1,
                order_books=-9.5,
                country="PT",
            ),
        ]

        with patch("raglite.external_data.clients.eurostat.EurostatClient") as mock_eurostat:
            mock_client = AsyncMock()
            mock_client.fetch_construction_confidence.return_value = mock_data
            mock_eurostat.return_value = mock_client

            from raglite.forecasting.regressor_fetch import fetch_single_regressor

            result = await fetch_single_regressor(
                "construction_confidence",
                start_date=date(2024, 1, 1),
                end_date=date(2024, 6, 30),
            )

        assert result is not None
        assert isinstance(result, pd.Series)
        assert isinstance(result.index, pd.DatetimeIndex)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_construction_confidence_regressor_values(self) -> None:
        """AC3.2: Regressor returns correct confidence index values."""
        mock_data = [
            ECConstructionConfidence(
                date=date(2024, 1, 1),
                confidence_index=-4.5,
                country="PT",
            ),
            ECConstructionConfidence(
                date=date(2024, 2, 1),
                confidence_index=-3.2,
                country="PT",
            ),
        ]

        with patch("raglite.external_data.clients.eurostat.EurostatClient") as mock_eurostat:
            mock_client = AsyncMock()
            mock_client.fetch_construction_confidence.return_value = mock_data
            mock_eurostat.return_value = mock_client

            from raglite.forecasting.regressor_fetch import fetch_single_regressor

            result = await fetch_single_regressor(
                "construction_confidence",
                start_date=date(2024, 1, 1),
                end_date=date(2024, 6, 30),
            )

        assert result is not None
        assert result.loc[pd.Timestamp("2024-01-01")] == -4.5
        assert result.loc[pd.Timestamp("2024-02-01")] == -3.2

    @pytest.mark.asyncio
    async def test_construction_confidence_regressor_returns_none_on_empty_data(
        self,
    ) -> None:
        """AC3.3: Regressor returns None when no data available."""
        with patch("raglite.external_data.clients.eurostat.EurostatClient") as mock_eurostat:
            mock_client = AsyncMock()
            mock_client.fetch_construction_confidence.return_value = []
            mock_eurostat.return_value = mock_client

            from raglite.forecasting.regressor_fetch import fetch_single_regressor

            result = await fetch_single_regressor(
                "construction_confidence",
                start_date=date(2024, 1, 1),
                end_date=date(2024, 6, 30),
            )

        assert result is None


class TestConstructionConfidenceRegistration:
    """AC4: Registration tests."""

    def test_construction_confidence_in_available_regressors(self) -> None:
        """construction_confidence should be in AVAILABLE_REGRESSORS."""
        from raglite.forecasting.regressor_config import AVAILABLE_REGRESSORS

        assert "construction_confidence" in AVAILABLE_REGRESSORS
