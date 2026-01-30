"""Mock client fixtures for testing.

This module provides global mock fixtures for external clients (Mistral API, etc.)
to prevent actual API calls during testing and ensure test isolation.
"""

from contextlib import ExitStack
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(scope="session")
def mock_mistral_api_globally():
    """Mock Mistral API client globally across all tests.

    This fixture patches all modules that import get_mistral_client to prevent
    actual API calls during testing. It must be applied as an autouse fixture
    in the conftest.py to ensure all tests are isolated from external API calls.

    Yields:
        MagicMock: Mock instance that can be used in tests
    """

    mock_client_instance = MagicMock()
    # Configure mock client behavior
    mock_client_instance.messages.return_value = MagicMock()
    mock_client_instance.messages.create.return_value = MagicMock(
        content=[MagicMock(text="Mock response")],
        id="mock-id",
        model="mistral-large-latest",
    )

    with ExitStack() as stack:
        # Patch all modules that import get_mistral_client
        # Agentic agents
        mock_synthesis_agent = stack.enter_context(
            patch("raglite.agentic.agents.synthesis_agent.get_mistral_client")
        )
        mock_synthesis_methods = stack.enter_context(
            patch("raglite.agentic.agents.synthesis_methods.get_mistral_client")
        )

        # Forecasting modules
        mock_forecasting_hybrid_init = stack.enter_context(
            patch("raglite.forecasting.hybrid.__init__.get_mistral_client")
        )
        mock_ensemble = stack.enter_context(
            patch("raglite.forecasting.hybrid.ensemble.get_mistral_client")
        )
        mock_core = stack.enter_context(
            patch("raglite.forecasting.timeseries.core.get_mistral_client")
        )

        # Ingestion modules
        mock_async_batch_legacy = stack.enter_context(
            patch(
                "raglite.ingestion.adaptive_table.unit_inference.async_batch._legacy.get_mistral_client"
            )
        )
        mock_llm_inference = stack.enter_context(
            patch(
                "raglite.ingestion.adaptive_table.unit_inference.llm_inference.get_mistral_client"
            )
        )
        mock_pdf_processing_init = stack.enter_context(
            patch("raglite.ingestion.document_ingestion.pdf_processing.__init__.get_mistral_client")
        )
        mock_pdf_processing_legacy = stack.enter_context(
            patch("raglite.ingestion.document_ingestion.pdf_processing._legacy.get_mistral_client")
        )
        mock_embedding_init = stack.enter_context(
            patch("raglite.ingestion.embedding_generation.__init__.get_mistral_client")
        )

        # Insights modules
        mock_anomalies = stack.enter_context(patch("raglite.insights.anomalies.get_mistral_client"))
        mock_proactive_synthesis = stack.enter_context(
            patch("raglite.insights.proactive_modules.synthesis.get_mistral_client")
        )
        mock_recommendations_synthesis = stack.enter_context(
            patch("raglite.insights.recommendations.synthesis.get_mistral_client")
        )
        mock_trends = stack.enter_context(patch("raglite.insights.trends.get_mistral_client"))

        # Retrieval modules
        mock_metadata_filter = stack.enter_context(
            patch("raglite.retrieval.query_classifier.metadata_filter.get_mistral_client")
        )
        mock_sql_generation = stack.enter_context(
            patch("raglite.retrieval.query_classifier.sql_generation.get_mistral_client")
        )
        mock_enrichment = stack.enter_context(
            patch("raglite.retrieval.search.enrichment.get_mistral_client")
        )

        # Assign return values for all mocks
        mock_synthesis_agent.return_value = mock_client_instance
        mock_synthesis_methods.return_value = mock_client_instance
        mock_forecasting_hybrid_init.return_value = mock_client_instance
        mock_ensemble.return_value = mock_client_instance
        mock_core.return_value = mock_client_instance
        mock_async_batch_legacy.return_value = mock_client_instance
        mock_llm_inference.return_value = mock_client_instance
        mock_pdf_processing_init.return_value = mock_client_instance
        mock_pdf_processing_legacy.return_value = mock_client_instance
        mock_embedding_init.return_value = mock_client_instance
        mock_anomalies.return_value = mock_client_instance
        mock_proactive_synthesis.return_value = mock_client_instance
        mock_recommendations_synthesis.return_value = mock_client_instance
        mock_trends.return_value = mock_client_instance
        mock_metadata_filter.return_value = mock_client_instance
        mock_sql_generation.return_value = mock_client_instance
        mock_enrichment.return_value = mock_client_instance

        yield mock_client_instance
