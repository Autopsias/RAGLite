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
from raglite.shared.clients import get_mistral_client
from raglite.shared.logging import get_logger

logger = get_logger(__name__)

# OpenAI client availability (optional fallback)
try:
    from openai import AsyncOpenAI

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


def _synthesize_simple(
    retrieval_results: list[dict[str, Any]],
    analysis_results: list[dict[str, Any]],
    query: str,
) -> str:
    """Simple synthesis without LLM (no API key required).

    Combines retrieval and analysis results into a basic formatted answer.
    For AC6 testing - production version would use LLM for better synthesis.

    Args:
        retrieval_results: Document chunks from retrieval agent
        analysis_results: Calculation results from analysis agent
        query: Original user query

    Returns:
        Formatted answer string
    """
    answer_parts = [f"Based on the query: {query}\n"]

    # Add retrieval results
    if retrieval_results:
        answer_parts.append(f"\nRetrieved {len(retrieval_results)} relevant documents:\n")
        for i, chunk in enumerate(retrieval_results[:3], 1):  # Show top 3
            content = chunk.get("content", "")
            source = chunk.get("source", "Unknown")
            answer_parts.append(f"{i}. {content[:200]}... (Source: {source})\n")

    # Add analysis results
    if analysis_results:
        answer_parts.append(f"\nAnalysis Results ({len(analysis_results)} calculations):\n")
        for i, result in enumerate(analysis_results, 1):
            calc = result.get("calculation", "")
            value = result.get("formatted_value", "")
            reasoning = result.get("reasoning", "")
            answer_parts.append(f"{i}. {calc} = {value}\n   {reasoning}\n")

    return "".join(answer_parts)


async def _synthesize_with_mistral(
    retrieval_results: list[dict[str, Any]],
    analysis_results: list[dict[str, Any]],
    query: str,
    context: str | None = None,
) -> tuple[str, list[str], list[str]]:
    """Use Mistral AI to synthesize multi-source results.

    Args:
        retrieval_results: List of document chunks from retrieval agent
        analysis_results: List of analysis results from analysis agent
        query: Original user query for context
        context: Optional additional context for synthesis

    Returns:
        Tuple of (answer, reasoning_steps, sources)

    Raises:
        Exception: If Mistral API fails
    """
    client = get_mistral_client()

    # Build context for Mistral
    retrieval_context = ""
    sources = []

    if retrieval_results:
        retrieval_context += "\n## Retrieved Documents:\n"
        for idx, chunk in enumerate(retrieval_results, 1):
            chunk_content = chunk.get("content", "")
            chunk_source = chunk.get("source", "Unknown")
            retrieval_context += f"{idx}. {chunk_source}: {chunk_content}\n"
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

    # Build prompt for Mistral
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

    # Call Mistral API (upgraded to Large for better financial reasoning)
    response = client.chat.complete(
        model="mistral-large-latest",
        messages=[{"role": "user", "content": prompt}],
    )

    # Parse Mistral's response
    response_text = response.choices[0].message.content if response.choices else ""

    try:
        # Try to parse as JSON
        parsed = json.loads(response_text)
        answer = parsed.get("answer", response_text)
        reasoning_steps = parsed.get("reasoning_steps", [])
    except (json.JSONDecodeError, KeyError, AttributeError):
        # Fallback: use response as-is
        answer = response_text
        reasoning_steps = ["Direct synthesis from Mistral response"]

    return answer, reasoning_steps, sources


async def _synthesize_with_openai(
    retrieval_results: list[dict[str, Any]],
    analysis_results: list[dict[str, Any]],
    query: str,
    context: str | None = None,
    model: str = "gpt-4o",
) -> tuple[str, list[str], list[str]]:
    """Use OpenAI GPT-4o to synthesize multi-source results (primary synthesis method).

    Args:
        retrieval_results: List of document chunks from retrieval agent
        analysis_results: List of analysis results from analysis agent
        query: Original user query for context
        context: Optional additional context for synthesis
        model: OpenAI model to use (default: gpt-4o)

    Returns:
        Tuple of (answer, reasoning_steps, sources)

    Raises:
        Exception: If OpenAI API fails or not available
    """
    if not OPENAI_AVAILABLE:
        raise ImportError("openai package not installed. Install with: pip install openai")

    import os

    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")

    client = AsyncOpenAI(api_key=openai_api_key)

    # Build context for OpenAI (same as Mistral)
    retrieval_context = ""
    sources = []

    if retrieval_results:
        retrieval_context += "\n## Retrieved Documents:\n"
        for idx, chunk in enumerate(retrieval_results, 1):
            chunk_content = chunk.get("content", "")
            chunk_source = chunk.get("source", "Unknown")
            retrieval_context += f"{idx}. {chunk_source}: {chunk_content}\n"
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

    # Build prompt for OpenAI
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

    # Call OpenAI API
    response = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )

    # Parse OpenAI's response
    response_text = response.choices[0].message.content if response.choices else ""

    try:
        # Try to parse as JSON
        parsed = json.loads(response_text)
        answer = parsed.get("answer", response_text)
        reasoning_steps = parsed.get("reasoning_steps", [])
    except (json.JSONDecodeError, KeyError, AttributeError):
        # Fallback: use response as-is
        answer = response_text
        reasoning_steps = ["Direct synthesis from OpenAI response"]

    return answer, reasoning_steps, sources


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
        # Extract data from context (orchestrator passes previous agent results here)
        context = context or {}

        # Parse context to extract retrieval results, analysis results, and query
        retrieval_results: list[dict[str, Any]] = []
        analysis_results: list[dict[str, Any]] = []
        query = ""

        # Iterate through context values to find agent results
        for _task_id, task_result in context.items():
            if not task_result:
                continue

            # Try to parse JSON result
            try:
                if isinstance(task_result, str):
                    result_data = json.loads(task_result)
                else:
                    result_data = task_result

                # Check if this is retrieval results
                if isinstance(result_data, dict) and "chunks" in result_data:
                    retrieval_results.extend(result_data.get("chunks", []))
                    if not query:
                        query = result_data.get("query", "")

                # Check if this is analysis results
                elif isinstance(result_data, dict) and "calculation" in result_data:
                    analysis_results.append(result_data)

            except (json.JSONDecodeError, TypeError, AttributeError):
                # Skip results that can't be parsed
                continue

        # If query not found in context, extract from instruction
        if not query:
            # Instruction typically contains the original query
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

        # Validate inputs
        if not query:
            raise ValueError("Query cannot be empty")

        if not retrieval_results and not analysis_results:
            raise ValueError("Synthesis requires at least retrieval_results or analysis_results")

        # Use OpenAI GPT-4o as primary synthesis (stable, proven quality)
        # GPT-4o: 75.9% MATH, lower hallucination, $15/M output - reliable for production
        synthesis_method = "gpt-4o"
        try:
            answer, reasoning_steps, sources = await _synthesize_with_openai(
                retrieval_results=retrieval_results or [],
                analysis_results=analysis_results or [],
                query=query,
                context=None,
                model="gpt-4o",
            )
        except Exception as openai_error:
            # OpenAI failed - try Mistral as fallback (reverse fallback)
            logger.warning(
                "OpenAI synthesis failed, falling back to Mistral",
                extra={"error": str(openai_error)},
            )
            synthesis_method = "mistral-large"
            answer, reasoning_steps, sources = await _synthesize_with_mistral(
                retrieval_results=retrieval_results or [],
                analysis_results=analysis_results or [],
                query=query,
                context=None,
            )

        # Build result
        result = SynthesisResult(
            answer=answer,
            reasoning_steps=reasoning_steps,
            sources=sources,
            metadata={
                "retrieval_count": len(retrieval_results or []),
                "analysis_count": len(analysis_results or []),
                "synthesis_type": synthesis_method,  # Track which synthesis was used
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
