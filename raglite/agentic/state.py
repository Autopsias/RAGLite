"""State management for agentic workflows.

Defines the AgentState Pydantic model for propagating data between sequential
agents in the orchestration pipeline (Story 3.1: AC4).
"""

from typing import Any

from pydantic import BaseModel, ConfigDict


class DocumentChunk(BaseModel):
    """A chunk of document content with metadata."""

    id: str
    content: str
    source: str
    page_number: int | None = None
    chunk_index: int = 0
    metadata: dict[str, Any] = {}


class AnalysisResult(BaseModel):
    """Result from financial analysis operation (Story 3.3 AC2).

    Captures the calculation, numerical result, formatted display,
    and LLM-generated reasoning for financial analysis types.
    """

    calculation: str  # Formula string (e.g., "(12.0 - 10.0) / 10.0 = 0.20")
    value: float  # Numerical result (e.g., 0.20)
    formatted_value: str  # Human-readable format (e.g., "+20%")
    reasoning: str  # LLM-generated explanation
    data_points_used: dict[str, float]  # Original data dictionary


class SynthesisResult(BaseModel):
    """Result from synthesis operation (Story 3.4 AC2).

    Captures the natural language answer, reasoning steps, sources,
    and metadata from multi-source synthesis operations.
    """

    answer: str  # Final natural language answer
    reasoning_steps: list[str]  # Steps taken to synthesize answer
    sources: list[str]  # Aggregated citations from all agents
    metadata: dict[str, Any]  # Execution metadata (confidence, agent_count, etc.)


class AnalysisOutput(BaseModel):
    """Output from the Analysis Agent."""

    insights: list[str] = []
    entities: list[str] = []
    relationships: list[dict[str, str]] = []
    confidence_score: float = 0.0


class AgentState(BaseModel):
    """Shared state for multi-step agentic workflows.

    This model defines the data structure passed between sequential agents
    in the Retrieval → Analysis → Synthesis pipeline. Each agent consumes
    the previous agent's output and adds to the state.

    AC4: State management functional for multi-step workflows
    """

    # Query input
    query: str

    # Retrieval Agent outputs (Story 3.2)
    retrieval_results: list[DocumentChunk] | None = None
    retrieval_score: float | None = None

    # Analysis Agent outputs (Story 3.3)
    analysis_results: AnalysisOutput | None = None

    # Synthesis Agent output (Story 3.4)
    synthesis_result: str | None = None

    # Execution metadata
    metadata: dict[str, Any] = {}

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def add_metadata(self, key: str, value: Any) -> None:
        """Add execution metadata to state.

        Args:
            key: Metadata key
            value: Metadata value
        """
        self.metadata[key] = value

    def validate_required_fields(self, required_fields: list[str]) -> tuple[bool, str | None]:
        """Validate that required fields are present in state.

        AC4: State validation confirms data integrity across agent boundaries

        Args:
            required_fields: List of field names that must be present

        Returns:
            Tuple of (is_valid, error_message)
        """
        missing_fields = []
        for field in required_fields:
            value = getattr(self, field, None)
            if value is None:
                missing_fields.append(field)

        if missing_fields:
            error_msg = f"Missing required fields: {', '.join(missing_fields)}"
            return False, error_msg

        return True, None
