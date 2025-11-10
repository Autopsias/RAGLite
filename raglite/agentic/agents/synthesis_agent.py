"""Synthesis Agent for multi-source result aggregation and narrative generation.

Story 3.4 AC1-AC3: Implements a @tool decorator-based synthesis agent that
combines retrieval and analysis results into coherent natural language answers
with proper source attribution.
"""

import json
import time
from typing import Any

try:
    from strands import tool
except ImportError:
    # Strands not installed - deferred until Epic 3
    def tool(func):  # type: ignore
        """No-op tool decorator when strands is not available."""
        return func


from raglite.agentic.state import (
    SynthesisResult,
)
from raglite.shared.clients import get_claude_client
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


async def _synthesize_with_claude(
    retrieval_results: list[dict[str, Any]],
    analysis_results: list[dict[str, Any]],
    query: str,
    context: str | None = None,
) -> tuple[str, list[str], list[str]]:
    """Use Claude Sonnet to synthesize multi-source results.

    Args:
        retrieval_results: List of document chunks from retrieval agent
        analysis_results: List of analysis results from analysis agent
        query: Original user query for context
        context: Optional additional context for synthesis

    Returns:
        Tuple of (answer, reasoning_steps, sources)

    Raises:
        Exception: If Claude API fails
    """
    client = get_claude_client()

    # Build context for Claude
    retrieval_context = ""
    sources = []

    if retrieval_results:
        retrieval_context += "\n## Retrieved Documents:\n"
        for idx, chunk in enumerate(retrieval_results, 1):
            chunk_content = chunk.get("content", "")
            chunk_source = chunk.get("source", "Unknown")
            retrieval_context += f"{idx}. {chunk_source}: {chunk_content[:200]}...\n"
            if chunk_source not in sources:
                sources.append(chunk_source)

    analysis_context = ""
    if analysis_results:
        analysis_context += "\n## Analysis Results:\n"
        for idx, result in enumerate(analysis_results, 1):
            calc = result.get("calculation", "")
            value = result.get("formatted_value", "")
            reasoning = result.get("reasoning", "")
            analysis_context += (
                f"{idx}. Calculation: {calc}\n   Value: {value}\n   Reasoning: {reasoning}\n"
            )

    # Build prompt for Claude
    prompt = f"""You are a financial analyst synthesizing information from multiple sources to answer user queries.

Original Query: {query}

{retrieval_context}
{analysis_context}

{f"Additional Context: {context}" if context else ""}

Please synthesize the above information into a clear, coherent answer that:
1. Directly answers the user's query
2. Integrates insights from both retrieved documents and analysis
3. Maintains proper source attribution
4. Provides reasoning for how you combined the information
5. Notes any conflicting information from different sources

Format your response as JSON with the following structure:
{{
    "answer": "Clear, coherent answer to the query",
    "reasoning_steps": ["Step 1: ...", "Step 2: ...", ...],
    "confidence_notes": "Any caveats or confidence issues"
}}"""

    message = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    # Parse Claude's response
    response_text = (
        message.content[0].text if hasattr(message.content[0], "text") else str(message.content[0])
    )

    try:
        # Try to parse as JSON
        parsed = json.loads(response_text)
        answer = parsed.get("answer", response_text)
        reasoning_steps = parsed.get("reasoning_steps", [])
    except (json.JSONDecodeError, KeyError, AttributeError):
        # Fallback: use response as-is
        answer = response_text
        reasoning_steps = ["Direct synthesis from Claude response"]

    return answer, reasoning_steps, sources


@tool
async def synthesis_agent(
    retrieval_results: list[dict],
    analysis_results: list[dict],
    query: str,
    context: str | None = None,
) -> str:
    """Synthesis Agent: Aggregate multi-source results into coherent answer.

    Combines retrieval results (document chunks) and analysis results (calculations)
    into a natural language response with proper source attribution.

    Args:
        retrieval_results: List of document chunks from retrieval agent (JSON dicts)
        analysis_results: List of analysis results from analysis agent (JSON dicts)
        query: Original user query for context
        context: Optional additional context for synthesis

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
        logger.info(
            "Synthesis agent called",
            extra={
                "query_length": len(query),
                "retrieval_count": len(retrieval_results or []),
                "analysis_count": len(analysis_results or []),
                "has_context": context is not None,
            },
        )

        # Validate inputs
        if not query:
            raise ValueError("Query cannot be empty")

        if not retrieval_results and not analysis_results:
            raise ValueError("Synthesis requires at least retrieval_results or analysis_results")

        # Synthesize with Claude
        answer, reasoning_steps, sources = await _synthesize_with_claude(
            retrieval_results=retrieval_results or [],
            analysis_results=analysis_results or [],
            query=query,
            context=context,
        )

        # Build result
        result = SynthesisResult(
            answer=answer,
            reasoning_steps=reasoning_steps,
            sources=sources,
            metadata={
                "retrieval_count": len(retrieval_results or []),
                "analysis_count": len(analysis_results or []),
                "has_context": context is not None,
                "source_count": len(sources),
            },
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

        return result.model_dump_json()

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

        # Return error metadata
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
