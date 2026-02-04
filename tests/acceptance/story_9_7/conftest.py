"""Shared fixtures for Story 9.7 ATDD tests.

These fixtures provide test data for re-ingestion and validation tests.
"""

import pytest


@pytest.fixture
def sample_document_list() -> list[str]:
    """Sample list of production PDF documents (subset for testing).

    In the real implementation, this should contain all 33 production PDFs.
    """
    return [
        "2024-09 Performance Review CONSO_v1.pdf",
        "2024-12 Performance Review CONSO_v1.pdf",
        "2025-03 Performance Review CONSO_v1.pdf",
        "BdC-Quarterly-Report-1Q25.pdf",
        "Novobanco_1Q2025_Quarterly-Report.pdf",
    ]


@pytest.fixture
def sample_classification_ground_truth() -> dict:
    """Sample ground truth for classification accuracy validation.

    Format matches expected structure in tests/fixtures/classification_ground_truth.json.
    """
    return {
        "version": "1.0",
        "created": "2026-02-01",
        "entries": [
            {
                "document": "2024-12 Performance Review CONSO_v1.pdf",
                "page": 12,
                "table_index": 0,
                "row_index": 5,
                "period": "Dec-24",
                "entity": "Portugal Cement",
                "expected_period_type": "monthly_actual",
                "expected_value_type": "actual",
                "expected_entity_level": "company_only",
            },
            {
                "document": "2024-12 Performance Review CONSO_v1.pdf",
                "page": 15,
                "table_index": 1,
                "row_index": 2,
                "period": "YTD Dec-24",
                "entity": "GROUP",
                "expected_period_type": "ytd_actual",
                "expected_value_type": "actual",
                "expected_entity_level": "consolidated",
            },
            {
                "document": "BdC-Quarterly-Report-1Q25.pdf",
                "page": 8,
                "table_index": 0,
                "row_index": 3,
                "period": "Budget 2025",
                "entity": "Total",
                "expected_period_type": "budget",
                "expected_value_type": "budget",
                "expected_entity_level": "consolidated",
            },
        ],
    }


@pytest.fixture
def sample_coverage_report() -> dict:
    """Sample coverage report structure for validation.

    Represents expected output from validate-classification-coverage.py.
    """
    return {
        "total_rows": 78759,
        "period_type_nulls": 0,
        "value_type_nulls": 0,
        "entity_level_nulls": 0,
        "coverage_percentage": 100.0,
        "breakdown": {
            "period_type": {
                "monthly_actual": {"count": 45000, "percentage": 57.1},
                "ytd_actual": {"count": 20000, "percentage": 25.4},
                "budget": {"count": 10000, "percentage": 12.7},
                "unknown": {"count": 3759, "percentage": 4.8},
            }
        },
    }


@pytest.fixture
def sample_accuracy_report() -> dict:
    """Sample accuracy report structure for validation.

    Represents expected output from validate-classification-accuracy.py.
    """
    return {
        "ground_truth_count": 50,
        "metrics": {
            "period_type": {"expected": 95.0, "actual": 96.0, "status": "PASS"},
            "value_type": {"expected": 90.0, "actual": 92.0, "status": "PASS"},
            "entity_level": {"expected": 90.0, "actual": 91.0, "status": "PASS"},
        },
        "misclassifications": [],
    }


@pytest.fixture
def sample_performance_metrics() -> dict:
    """Sample performance metrics structure.

    Represents expected output from re-ingestion performance tracking.
    """
    return {
        "total_documents": 33,
        "total_duration_seconds": 3600.0,
        "total_pages": 1200,
        "total_tables": 500,
        "total_rows": 78759,
        "average_rows_per_second": 21.9,
        "classification_overhead_percentage": 15.0,
        "per_document": [
            {
                "document": "2024-12 Performance Review CONSO_v1.pdf",
                "pages": 45,
                "tables": 20,
                "rows": 3500,
                "duration_seconds": 120.0,
                "rows_per_second": 29.2,
            }
        ],
    }
