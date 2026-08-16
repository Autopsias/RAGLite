"""Unit tests for Eurostat Indicator Data Models and Constants.

Story 6.16: Add Eurostat Construction & Industrial Indicators

This file tests the data models and dataset constants for Eurostat indicators.

Run with: pytest tests/unit/external_data/test_eurostat_indicators_models.py -v
"""

from __future__ import annotations

from datetime import date

import pytest

from raglite.external_data.clients.eurostat import EurostatClient

# These imports will fail until models are implemented (RED phase)
try:
    from raglite.external_data.models import (
        EurostatConstructionOutput,
        EurostatIndustrialProduction,
    )
except ImportError:
    # Expected during RED phase - models don't exist yet
    EurostatConstructionOutput = None  # type: ignore[assignment, misc]
    EurostatIndustrialProduction = None  # type: ignore[assignment, misc]


class TestEurostatIndicatorDataModels:
    """Unit tests for Eurostat indicator data models (AC5).

    Given: Model class definitions
    When: Instances are created with valid/invalid data
    Then: Validation rules are enforced correctly
    """

    def test_ac5_construction_output_model_exists(self) -> None:
        """AC5: EurostatConstructionOutput model exists."""
        assert EurostatConstructionOutput is not None, (
            "EurostatConstructionOutput model must be implemented"
        )

    def test_ac5_industrial_production_model_exists(self) -> None:
        """AC5: EurostatIndustrialProduction model exists."""
        assert EurostatIndustrialProduction is not None, (
            "EurostatIndustrialProduction model must be implemented"
        )

    def test_ac5_construction_output_model_fields(self) -> None:
        """AC5: EurostatConstructionOutput has required fields."""
        if EurostatConstructionOutput is None:
            pytest.skip("Model not yet implemented (RED phase)")

        # Create instance with required fields
        record = EurostatConstructionOutput(
            date=date(2024, 1, 1),
            index_value=105.2,
            country="PT",
            nace_sector="F",
            seasonal_adjustment="SCA",
        )

        assert record.date == date(2024, 1, 1)
        assert record.index_value == 105.2
        assert record.country == "PT"
        assert record.nace_sector == "F"
        assert record.seasonal_adjustment == "SCA"

    def test_ac5_industrial_production_model_fields(self) -> None:
        """AC5: EurostatIndustrialProduction has required fields."""
        if EurostatIndustrialProduction is None:
            pytest.skip("Model not yet implemented (RED phase)")

        record = EurostatIndustrialProduction(
            date=date(2024, 1, 1),
            index_value=98.5,
            country="PT",
            nace_sector="B-D",
            seasonal_adjustment="SCA",
        )

        assert record.date == date(2024, 1, 1)
        assert record.index_value == 98.5
        assert record.country == "PT"
        assert record.nace_sector == "B-D"
        assert record.seasonal_adjustment == "SCA"

    def test_ac5_construction_output_index_value_positive(self) -> None:
        """AC5: Construction output index values must be positive."""
        if EurostatConstructionOutput is None:
            pytest.skip("Model not yet implemented (RED phase)")

        record = EurostatConstructionOutput(
            date=date(2024, 1, 1),
            index_value=105.2,
            country="PT",
            nace_sector="F",
            seasonal_adjustment="SCA",
        )

        assert record.index_value > 0

    def test_ac5_industrial_production_index_value_positive(self) -> None:
        """AC5: Industrial production index values must be positive."""
        if EurostatIndustrialProduction is None:
            pytest.skip("Model not yet implemented (RED phase)")

        record = EurostatIndustrialProduction(
            date=date(2024, 1, 1),
            index_value=98.5,
            country="PT",
            nace_sector="B-D",
            seasonal_adjustment="SCA",
        )

        assert record.index_value > 0


class TestEurostatClientDatasetConstants:
    """Unit tests for Eurostat dataset constants (AC1, AC2).

    Given: EurostatClient class
    When: Accessing dataset constants
    Then: Correct Eurostat dataset codes are defined
    """

    def test_ac1_construction_dataset_constant(self) -> None:
        """AC1: CONSTRUCTION_DATASET constant defined."""
        assert hasattr(EurostatClient, "CONSTRUCTION_DATASET"), (
            "CONSTRUCTION_DATASET constant must be defined"
        )
        assert EurostatClient.CONSTRUCTION_DATASET == "sts_copr_m"

    def test_ac2_industrial_production_dataset_constant(self) -> None:
        """AC2: INDUSTRIAL_PRODUCTION_DATASET constant defined."""
        assert hasattr(EurostatClient, "INDUSTRIAL_PRODUCTION_DATASET"), (
            "INDUSTRIAL_PRODUCTION_DATASET constant must be defined"
        )
        assert EurostatClient.INDUSTRIAL_PRODUCTION_DATASET == "sts_inpr_m"
