"""LLM-based synthesis methods for the synthesis agent.

Contains OpenAI and Mistral synthesis implementations.
"""

import json
from typing import Any

# OpenAI client availability (optional fallback)
try:
    from openai import AsyncOpenAI

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from raglite.shared.clients import get_mistral_client
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


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
    # Ensure response_text is not None for type checker
    if response_text is None:
        response_text = ""

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
    # Ensure response_text is not None for type checker
    if response_text is None:
        response_text = ""

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
