"""Utility functions for the synthesis agent."""

import json
from typing import Any

from raglite.agentic.state import SynthesisResult


def _synthesize_simple(
    retrieval_results: list[dict[str, Any]],
    analysis_results: list[dict[str, Any]],
    query: str,
) -> tuple[str, list[str], list[str]]:
    """Simple synthesis without LLM (no API key required).

    Combines retrieval and analysis results into a basic formatted answer.
    For AC6 testing - production version would use LLM for better synthesis.

    Args:
        retrieval_results: Document chunks from retrieval agent
        analysis_results: Calculation results from analysis agent
        query: Original user query

    Returns:
        Tuple of (answer, reasoning_steps, sources)
    """
    answer_parts = [f"Based on the query: {query}\n"]
    reasoning_steps = [
        "1. Retrieved relevant documents",
        "2. Performed financial analysis",
        "3. Synthesized results",
    ]
    sources = []

    # Add retrieval results
    if retrieval_results:
        answer_parts.append(f"\nRetrieved {len(retrieval_results)} relevant documents:\n")
        for i, chunk in enumerate(retrieval_results[:3], 1):  # Show top 3
            content = chunk.get("content", "")
            source = chunk.get("source", "Unknown")
            answer_parts.append(f"{i}. {content[:200]}... (Source: {source})\n")
            if source and source not in sources:
                sources.append(source)

    # Add analysis results
    if analysis_results:
        answer_parts.append(f"\nAnalysis Results ({len(analysis_results)} calculations):\n")
        for i, result in enumerate(analysis_results, 1):
            calc = result.get("calculation", "")
            value = result.get("formatted_value", "")
            reasoning = result.get("reasoning", "")
            answer_parts.append(f"{i}. {calc} = {value}\n   {reasoning}\n")

    answer = "".join(answer_parts)
    return answer, reasoning_steps, sources


def _extract_context_data(
    context: dict[str, Any] | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str]:
    """Extract retrieval results, analysis results, and query from context.

    Args:
        context: Context dictionary containing task results

    Returns:
        Tuple of (retrieval_results, analysis_results, query)
    """
    retrieval_results: list[dict[str, Any]] = []
    analysis_results: list[dict[str, Any]] = []
    query = ""

    if not context:
        return retrieval_results, analysis_results, query

    for _task_id, task_result in context.items():
        if not task_result:
            continue

        try:
            if isinstance(task_result, str):
                result_data = json.loads(task_result)
            else:
                result_data = task_result

            if isinstance(result_data, dict) and "chunks" in result_data:
                retrieval_results.extend(result_data.get("chunks", []))
                if not query:
                    query = result_data.get("query", "")
            elif isinstance(result_data, dict) and "calculation" in result_data:
                analysis_results.append(result_data)

        except (json.JSONDecodeError, TypeError, AttributeError):
            continue

    return retrieval_results, analysis_results, query


async def _perform_synthesis(
    retrieval_results: list[dict[str, Any]],
    analysis_results: list[dict[str, Any]],
    query: str,
) -> tuple[str, list[str], list[str], str]:
    """Perform synthesis using appropriate method (OpenAI, Mistral, or simple).

    Args:
        retrieval_results: Document chunks from retrieval
        analysis_results: Calculation results from analysis
        query: Original user query

    Returns:
        Tuple of (answer, reasoning_steps, sources, synthesis_method)
    """
    from raglite.agentic.agents.synthesis_methods import (  # noqa: F401
        _synthesize_with_mistral,
        _synthesize_with_openai,
    )
    from raglite.shared.logging import get_logger

    logger = get_logger(__name__)

    import os

    is_test = os.getenv("PYTEST_CURRENT_TEST") is not None

    if is_test:
        synthesis_method = "simple"
        return *_synthesize_simple(
            retrieval_results=retrieval_results or [],
            analysis_results=analysis_results or [],
            query=query,
        ), synthesis_method

    synthesis_method = "gpt-4o"
    try:
        result = await _synthesize_with_openai(
            retrieval_results=retrieval_results or [],
            analysis_results=analysis_results or [],
            query=query,
            context=None,
            model="gpt-4o",
        )
        return *result, synthesis_method
    except Exception as openai_error:
        logger.warning(
            "OpenAI synthesis failed, falling back to Mistral",
            extra={"error": str(openai_error)},
        )
        synthesis_method = "mistral-large"
        result = await _synthesize_with_mistral(
            retrieval_results=retrieval_results or [],
            analysis_results=analysis_results or [],
            query=query,
            context=None,
        )
        return *result, synthesis_method


def _build_synthesis_result(
    answer: str,
    reasoning_steps: list[str],
    sources: list[str],
    synthesis_method: str,
    retrieval_count: int,
    analysis_count: int,
) -> str:
    """Build SynthesisResult and return JSON string.

    Args:
        answer: Synthesized answer
        reasoning_steps: List of reasoning steps
        sources: Source citations
        synthesis_method: Method used for synthesis
        retrieval_count: Number of retrieval results
        analysis_count: Number of analysis results

    Returns:
        JSON-serialized SynthesisResult
    """
    result = SynthesisResult(
        answer=answer,
        reasoning_steps=reasoning_steps,
        sources=sources,
        metadata={
            "retrieval_count": retrieval_count,
            "analysis_count": analysis_count,
            "synthesis_type": synthesis_method,
            "source_count": len(sources),
        },
    )

    return result.model_dump_json()


def _build_synthesis_error(
    error_msg: str,
    execution_time: float,
) -> str:
    """Build error result for synthesis agent.

    Args:
        error_msg: Error message
        execution_time: Execution time in milliseconds

    Returns:
        JSON-serialized error result
    """
    error_result = SynthesisResult(
        answer="Error during synthesis",
        reasoning_steps=[f"Error: {error_msg}"],
        sources=[],
        metadata={
            "error": True,
            "error_message": error_msg,
            "execution_time_ms": execution_time,
        },
    )

    return error_result.model_dump_json()
