"""Database and data dictionary test data factories.

Provides factory functions for generating PostgreSQL table rows and Epic 3
data dictionary structures with realistic financial metrics and entities.
"""

import os
from typing import Any

from faker import Faker

_FAKER_SEED = int(os.getenv("FAKER_SEED", "42"))
fake = Faker()
Faker.seed(_FAKER_SEED)


def create_financial_table_row(**overrides: Any) -> dict[str, Any]:
    """Create sample financial table row with realistic values.

    Args:
        **overrides: Override specific fields

    Returns:
        Dictionary representing a PostgreSQL financial_tables row

    Example:
        row = create_financial_table_row()
        row = create_financial_table_row(entity="Apple Inc", metric="Revenue")
    """
    entities = ["Company A", "Company B", "Division X", "Division Y", "Segment Alpha"]
    metrics = ["Revenue", "EBITDA", "Net Income", "Operating Expenses", "Cash Flow"]
    units = ["USD millions", "EUR millions", "GBP millions", "percentage", "count"]
    periods = ["Q1", "Q2", "Q3", "Q4", "FY", "H1", "H2"]

    defaults = {
        "entity": fake.random_element(entities),
        "metric": fake.random_element(metrics),
        "value": fake.pydecimal(left_digits=6, right_digits=2, positive=True),
        "unit": fake.random_element(units),
        "period": fake.random_element(periods),
        "fiscal_year": fake.random_int(2020, 2025),
        "page_number": fake.random_int(1, 50),
    }
    defaults.update(overrides)
    return defaults


def create_financial_table_rows(count: int, **overrides: Any) -> list[dict[str, Any]]:
    """Create multiple financial table rows.

    Args:
        count: Number of rows to create
        **overrides: Override fields for ALL rows

    Returns:
        List of dictionaries representing PostgreSQL rows
    """
    return [create_financial_table_row(**overrides) for _ in range(count)]


def create_sql_table_row(**overrides: Any) -> dict[str, Any]:
    """Create PostgreSQL financial_tables row for testing.

    Args:
        **overrides: Override specific fields

    Returns:
        Dictionary representing database row

    Example:
        row = create_sql_table_row(
            entity="Apple Inc",
            metric="Revenue",
            value=100.5,
            period="Q3-24"
        )
    """
    entities = ["Secil Group", "Company A", "Division X", "Segment Alpha"]
    metrics = ["EBITDA", "Revenue", "Cost per ton", "Operating margin", "Cash flow"]
    units = ["EUR millions", "USD millions", "EUR/ton", "percentage", "count"]

    defaults = {
        "id": fake.random_int(1, 10000),
        "entity": fake.random_element(entities),
        "metric": fake.random_element(metrics),
        "value": float(fake.pydecimal(left_digits=5, right_digits=2, positive=True)),
        "unit": fake.random_element(units),
        "period": f"Q{fake.random_int(1, 4)}-{fake.random_int(23, 25)}",
        "fiscal_year": fake.random_int(2023, 2025),
        "page_number": fake.random_int(1, 100),
        "source_document": f"Financial_Report_{fake.year()}.pdf",
    }
    defaults.update(overrides)
    return defaults


def create_sql_table_rows(count: int, **overrides: Any) -> list[dict[str, Any]]:
    """Create multiple PostgreSQL table rows.

    Args:
        count: Number of rows to create
        **overrides: Override fields for ALL rows

    Returns:
        List of database row dictionaries
    """
    return [create_sql_table_row(**overrides) for _ in range(count)]


# Epic 3 Data Dictionary Factories
def create_inspection_catalog(**overrides: Any) -> dict[str, Any]:
    """Create sample database inspection catalog for Epic 3 tests.

    Args:
        **overrides: Override specific fields

    Returns:
        Dictionary representing inspection catalog structure

    Example:
        catalog = create_inspection_catalog()
        catalog = create_inspection_catalog(total_rows=170142)
    """
    metrics = [
        "EBITDA",
        "Revenue",
        "Variable Cost",
        "Fixed Cost",
        "Operating Margin",
        "Cash Flow",
    ]
    periods = [
        "Aug-25",
        "Sep-25",
        "Jul-25",
        "Aug-25 YTD",
        "Sep-25 YTD",
        "Q3-25",
    ]
    entities = [
        "Portugal Cement",
        "Tunisia Cement",
        "Secil Angola",
        "Currency (1000 EUR)",
        "Adrianopolis",
        "Pomerode",
    ]
    currencies = ["EUR"]

    defaults = {
        "metrics": metrics,
        "periods": periods,
        "entities": entities,
        "currencies": currencies,
        "total_rows": fake.random_int(100000, 200000),
    }
    defaults.update(overrides)
    return defaults


def create_database_query_result(**overrides: Any) -> list[dict[str, Any]]:
    """Create mock database query result for inspection tests.

    Args:
        **overrides: Override specific fields

    Returns:
        List of dictionaries representing database rows

    Example:
        # Mock metrics query result
        result = create_database_query_result(field="metric", values=["EBITDA", "Revenue"])
    """
    field = overrides.get("field", "metric")
    values = overrides.get("values", ["EBITDA", "Revenue", "Variable Cost"])

    return [{field: value} for value in values]
