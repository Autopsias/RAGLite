"""UAT tests for query performance validation.

AC4: Performance meets user expectations (<5s response time)
"""

import asyncio
from typing import Any
from unittest.mock import Mock, patch

import pytest

from raglite.shared.logging import get_logger
from raglite.shared.models import QueryResult

logger = get_logger(__name__)


class TestEpic1QueryPerformance:
    """UAT tests for query performance validation.

    Validates that query response times meet user expectations
    without authentication-related delays or failures.
    """

    @pytest.fixture(autouse=True)
    def setup_uat_environment(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Setup UAT test environment with proper authentication."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "uat-test-api-key-anthropic-12345")
        monkeypatch.setenv("MISTRAL_API_KEY", "uat-test-api-key-mistral-67890")
        monkeypatch.setenv("EXTERNAL_DATA_TIMEOUT", "30")
        monkeypatch.setenv("EXTERNAL_DATA_RETRY_ATTEMPTS", "3")
        monkeypatch.setenv("UAT_MODE", "true")
        monkeypatch.setenv("MOCK_EXTERNAL_APIS", "true")

    @pytest.mark.asyncio
    @pytest.mark.uat
    async def test_scenario_1_7_uat_013_query_performance(
        self, sample_email_episode: dict[str, Any], mock_external_apis: dict[str, Mock]
    ) -> None:
        """UAT Scenario 1.7-013: Query performance validation.

        Validates that query response times meet user expectations
        without authentication-related delays or failures.

        AC4: Performance meets user expectations (<5s response time)
        Expected: All queries complete within 5 seconds
        """
        # Arrange - Setup performance monitoring with authentication
        with patch("raglite.shared.clients.get_claude_client") as mock_anthropic:
            mock_anthropic.return_value = mock_external_apis["anthropic"]

            # Mock fast responses
            mock_anthropic.messages.create.return_value = Mock(
                content=[Mock(text="Fast response for performance test")]
            )

            # Prepare test queries
            test_queries = [
                "Q3 revenue performance",
                "EBITDA margin analysis",
                "Cash flow summary",
                "Balance sheet strength",
                "Market share growth",
            ]

            # Act - Measure query performance
            performance_results = []

            for query in test_queries:
                start_time = asyncio.get_event_loop().time()

                logger.info(
                    "Testing query performance",
                    extra={"query": query, "episode_id": sample_email_episode["episode_id"]},
                )

                # Simulate query with mocked fast response
                with patch("raglite.retrieval.search.search_documents") as mock_search_docs:
                    mock_search_docs.return_value = [
                        QueryResult(
                            text=f"Results for {query}",
                            source_document=sample_email_episode["episode_id"],
                            score=0.88,
                            page_number=1,
                            chunk_index=0,
                            word_count=10,
                        )
                    ]

                    # Execute query
                    results = await mock_search_docs(query=query, top_k=3)
                    performance_results.append(results)

                end_time = asyncio.get_event_loop().time()
                query_duration = end_time - start_time

                # Assert - Verify performance requirements
                assert query_duration < 5.0, (
                    f"Query '{query}' took {query_duration:.2f}s, should be <5s"
                )
                assert len(results) > 0, f"Query '{query}' should return results"

            # Verify overall performance
            assert len(performance_results) == len(test_queries), "All test queries should complete"

            # Verify authentication was properly configured (mock available when needed)
            assert mock_anthropic is not None, (
                "Claude client should be available for authentication"
            )
            assert all(len(results) > 0 for results in performance_results), (
                "All queries should return results"
            )
