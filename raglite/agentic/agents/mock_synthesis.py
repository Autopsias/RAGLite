"""Mock Synthesis Agent for testing agentic workflows.

Returns hardcoded synthesis results for testing agent coordination
without requiring real LLM calls (Story 3.1: AC3).
"""

from raglite.agentic.state import AgentState
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


class MockSynthesisAgent:
    """Mock agent that synthesizes results without real LLM calls.

    AC3: Test workflow: Synthesis Agent returns mock synthesis
    """

    def __init__(self) -> None:
        """Initialize the mock synthesis agent."""
        self.name = "MockSynthesisAgent"

    async def __call__(self, state: AgentState) -> AgentState:
        """Process retrieval results and return mock synthesis.

        Args:
            state: AgentState with retrieval_results populated

        Returns:
            Updated state with synthesis_result populated
        """
        logger.info(
            "Mock synthesis agent processing retrieval results",
            extra={
                "query": state.query,
                "agent": self.name,
                "chunks_available": (
                    len(state.retrieval_results) if state.retrieval_results else 0
                ),
            },
        )

        # Validate that retrieval results are present
        if not state.retrieval_results:
            logger.warning(
                "Mock synthesis agent: no retrieval results available",
                extra={"query": state.query},
            )
            state.synthesis_result = "Unable to synthesize without retrieval results."
            return state

        # Generate mock synthesis
        synthesis = self._generate_mock_synthesis(state)

        state.synthesis_result = synthesis
        state.add_metadata("synthesis_agent", "mock")
        state.add_metadata("synthesis_type", "mock")

        logger.info(
            "Mock synthesis agent completed",
            extra={
                "query": state.query,
                "synthesis_length": len(synthesis),
            },
        )

        return state

    def _generate_mock_synthesis(self, state: AgentState) -> str:
        """Generate mock synthesis from retrieval results.

        Args:
            state: AgentState with retrieval_results

        Returns:
            Mock synthesis string
        """
        if not state.retrieval_results:
            return "No synthesis available."

        # Create mock synthesis from retrieved chunks
        chunk_summaries = [f"- {chunk.content[:80]}..." for chunk in state.retrieval_results[:3]]

        synthesis = (
            f"Based on the retrieved data from financial documents, here is the analysis:\n\n"
            f"{chr(10).join(chunk_summaries)}\n\n"
            f"The financial data indicates strong performance with revenue growth of 12%, "
            f"improved profit margins, and strategic capital investments. "
            f"The company demonstrates solid operational efficiency and cash generation capabilities."
        )

        return synthesis
