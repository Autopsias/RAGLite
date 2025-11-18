"""Mock Retrieval Agent for testing agentic workflows.

Returns hardcoded document chunks for testing agent coordination
without requiring real Qdrant or database queries (Story 3.1: AC3).
"""

from raglite.agentic.state import AgentState, DocumentChunk
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


class MockRetrievalAgent:
    """Mock agent that simulates document retrieval without real searches.

    AC3: Test workflow: Retrieval Agent returns mock chunks
    """

    def __init__(self) -> None:
        """Initialize the mock retrieval agent."""
        self.name = "MockRetrievalAgent"

    async def __call__(self, state: AgentState) -> AgentState:
        """Process a query and return mock retrieval results.

        Args:
            state: AgentState with query input

        Returns:
            Updated state with retrieval_results populated
        """
        logger.info(
            "Mock retrieval agent processing query",
            extra={"query": state.query, "agent": self.name},
        )

        # Generate mock retrieval results
        mock_results = self._generate_mock_chunks(state.query)

        state.retrieval_results = mock_results
        state.retrieval_score = 0.95  # Mock high confidence score
        state.add_metadata("retrieval_agent", "mock")
        state.add_metadata("retrieval_chunk_count", len(mock_results))

        logger.info(
            "Mock retrieval agent completed",
            extra={
                "chunks_returned": len(mock_results),
                "query": state.query,
            },
        )

        return state

    def _generate_mock_chunks(self, query: str) -> list[DocumentChunk]:
        """Generate mock document chunks for testing.

        Args:
            query: The user's query

        Returns:
            List of mock DocumentChunk objects
        """
        # Hardcoded mock chunks for testing
        chunks = [
            DocumentChunk(
                id="mock_chunk_1",
                content=(
                    "Annual revenue for 2024 reached $5.2 billion, "
                    "representing a 12% increase over 2023. "
                    "Operating expenses were $3.1 billion."
                ),
                source="financial_report_2024.pdf",
                page_number=15,
                chunk_index=0,
                metadata={"section": "Financial Overview", "confidence": 0.98},
            ),
            DocumentChunk(
                id="mock_chunk_2",
                content=(
                    "Net profit margin improved to 18% in Q4 2024, "
                    "driven by operational efficiency initiatives. "
                    "Cash flow from operations was $1.8 billion."
                ),
                source="financial_report_2024.pdf",
                page_number=18,
                chunk_index=1,
                metadata={"section": "Profitability Analysis", "confidence": 0.96},
            ),
            DocumentChunk(
                id="mock_chunk_3",
                content=(
                    "Capital expenditures totaled $420 million in 2024, "
                    "focused on technology infrastructure and R&D. "
                    "Expected ROI is 3.2 years."
                ),
                source="financial_report_2024.pdf",
                page_number=22,
                chunk_index=2,
                metadata={"section": "Capital Allocation", "confidence": 0.94},
            ),
        ]

        return chunks
