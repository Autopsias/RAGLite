"""Mock agents for testing agentic workflows.

Provides mock Retrieval and Synthesis agents that return hardcoded results
for testing the orchestration framework without real LLM calls (Story 3.1: AC3).
"""

from raglite.agentic.agents.mock_retrieval import MockRetrievalAgent
from raglite.agentic.agents.mock_synthesis import MockSynthesisAgent

__all__ = [
    "MockRetrievalAgent",
    "MockSynthesisAgent",
]
