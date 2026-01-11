"""Data models and types for workflow planning."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class QueryComplexity(str, Enum):
    """Classification of query complexity (AC1)."""

    SIMPLE = "simple"  # Direct retrieval queries
    ANALYTICAL = "analytical"  # Multi-step analytical queries requiring orchestration


class AgentTask(BaseModel):
    """A single task in a workflow plan (AC2)."""

    task_id: str = Field(..., description="Unique task identifier (e.g., 'task_1')")
    agent_type: str = Field(..., description="Agent type: 'retrieval', 'analysis', or 'synthesis'")
    instruction: str = Field(..., description="Task instruction for the agent")
    depends_on: list[str] = Field(
        default_factory=list, description="Task IDs that must complete before this task"
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional task metadata")


class WorkflowPlan(BaseModel):
    """Complete workflow plan with task DAG (AC2)."""

    query: str = Field(..., description="Original user query")
    complexity: QueryComplexity = Field(..., description="Query complexity classification")
    tasks: list[AgentTask] = Field(..., description="List of tasks in execution order")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Workflow metadata (e.g., estimated_time_ms)"
    )


class AgentResult(BaseModel):
    """Result from a single agent task execution (AC4)."""

    task_id: str = Field(..., description="Task identifier that was executed")
    agent_type: str = Field(..., description="Agent type that executed the task")
    success: bool = Field(..., description="Whether task completed successfully")
    result: Any = Field(default=None, description="Task result data")
    execution_time_ms: int = Field(..., description="Task execution time in milliseconds")
    error_message: str | None = Field(default=None, description="Error message if task failed")
