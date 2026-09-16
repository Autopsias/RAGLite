"""Test fixtures for Epic 1 UAT validation tests.

This module contains all pytest fixtures used in Epic 1 validation tests.
"""

from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest


@pytest.fixture
def sample_email_episode() -> dict[str, Any]:
    """Sample email episode data for UAT testing.

    Represents a realistic financial email episode with metadata
    that users would typically process through the system.
    """
    return {
        "episode_id": "email_2024_q3_financial_review",
        "subject": "Q3 2024 Financial Performance Review",
        "sender": "investor.relations@company.com",
        "recipients": ["board@company.com", "investors@company.com"],
        "date": datetime(2024, 10, 15, 14, 30),
        "content": """
            Q3 2024 Financial Performance Summary

            Revenue: €1,234,567,890 (+12.3% YoY)
            EBITDA: €345,678,901 (+8.7% YoY)
            Net Income: €234,567,890 (+15.2% YoY)

            Key Highlights:
            - Strong revenue growth across all segments
            - Improved operational efficiency
            - Increased market share in core markets

            Forward Guidance:
            - Q4 2024 revenue expected: €1.3B
            - Full-year 2024 EBITDA margin: 28%
            """,
        "attachments": [
            {"name": "Q3_2024_Financial_Statements.pdf", "size": 2048576},
            {"name": "Investor_Presentation_Q3_2024.pptx", "size": 5242880},
        ],
        "metadata": {
            "document_type": "earnings_release",
            "quarter": "Q3",
            "year": 2024,
            "industry": "manufacturing",
            "market_cap": "large_cap",
        },
    }


@pytest.fixture
def mock_external_apis() -> dict[str, Mock]:
    """Mock external APIs to prevent 401 authentication errors.

    Fix 4: Comprehensive mocking of all external service calls
    that could potentially fail with authentication errors.
    """
    mocks = {}

    # Mock Anthropic API
    mocks["anthropic"] = AsyncMock()
    mocks["anthropic"].messages.create.return_value = Mock(
        content=[
            Mock(
                text="Q3 2024 financial results show strong performance with revenue growth of 12.3%"
            )
        ]
    )

    # Mock Mistral API
    mocks["mistral"] = AsyncMock()
    mocks["mistral"].chat.complete.return_value = Mock(
        choices=[Mock(message=Mock(content="Financial performance analysis completed"))]
    )

    # Mock external data clients
    mocks["external_data"] = AsyncMock()
    mocks["external_data"].fetch.return_value = {
        "status": "success",
        "data": {"revenue": 1234567890, "ebitda": 345678901},
    }

    return mocks
