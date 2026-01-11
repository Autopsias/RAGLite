"""Synthesis Agent for multi-source result aggregation and narrative generation.

Story 3.4 AC1-AC3: Implements a @tool decorator-based synthesis agent that
combines retrieval and analysis results into coherent natural language answers
with proper source attribution.
"""

import time
from typing import Any

try:
    from strands import tool
except ImportError:
    # Strands not installed - deferred until Epic 3
    def tool(func):  # type: ignore
        """No-op tool decorator when strands is not available."""
        return func


from raglite.agentic.agents.synthesis_methods import (  # noqa: F401
    OPENAI_AVAILABLE,
    AsyncOpenAI,
    _synthesize_with_mistral,
    _synthesize_with_openai,
)
from raglite.agentic.agents.synthesis_utils import (  # noqa: F401
    _build_synthesis_error,
    _build_synthesis_result,
    _extract_context_data,
    _perform_synthesis,
    _synthesize_simple,
)
from raglite.shared.clients import get_mistral_client  # noqa: F401
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


@tool
async def synthesis_agent(
    instruction: str,
    context: dict[str, Any] | None = None,
) -> str:
    """Synthesis Agent: Aggregate multi-source results into coherent answer.

    Combines retrieval results (document chunks) and analysis results (calculations)
    into a natural language response with proper source attribution.

    Args:
        instruction: Task instruction (contains the query and synthesis directive)
        context: Context data from previous agents containing:
            - retrieval results from retrieval_agent tasks
            - analysis results from analysis_agent tasks
            - original query string

    Returns:
        JSON string containing:
        {
            "answer": Natural language final answer,
            "reasoning_steps": List of synthesis steps taken,
            "sources": Aggregated source citations from all agents,
            "metadata": Execution metadata (confidence, agent_count, etc.)
        }

    Synthesis Patterns:
        - Retrieval-only: Summarize document chunks into coherent answer
        - Retrieval + Analysis: Integrate calculations with document evidence
        - Multi-source conflict resolution: Handle contradictions with citations
    """
    start_time = time.time()
    success = False
    error_msg = None

    try:
        retrieval_results, analysis_results, query = _extract_context_data(context)

        if not query:
            query = instruction

        logger.info(
            "Synthesis agent called",
            extra={
                "instruction_length": len(instruction),
                "query_length": len(query),
                "retrieval_count": len(retrieval_results),
                "analysis_count": len(analysis_results),
                "context_keys": list(context.keys()) if context else [],
            },
        )

        if not query:
            raise ValueError("Query cannot be empty")

        if not retrieval_results and not analysis_results:
            raise ValueError("Synthesis requires at least retrieval_results or analysis_results")

        answer, reasoning_steps, sources, synthesis_method = await _perform_synthesis(
            retrieval_results, analysis_results, query
        )

        success = True
        execution_time = (time.time() - start_time) * 1000

        logger.info(
            "Synthesis agent completed",
            extra={
                "success": success,
                "execution_time_ms": execution_time,
                "answer_length": len(answer),
                "reasoning_steps": len(reasoning_steps),
                "sources": len(sources),
            },
        )

        return _build_synthesis_result(
            answer,
            reasoning_steps,
            sources,
            synthesis_method,
            len(retrieval_results),
            len(analysis_results),
        )

    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        error_msg = str(e)

        logger.error(
            "Synthesis agent failed",
            extra={
                "success": success,
                "execution_time_ms": execution_time,
                "error": error_msg,
                "error_type": type(e).__name__,
            },
        )

        return _build_synthesis_error(error_msg, execution_time)
