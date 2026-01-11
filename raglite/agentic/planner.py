"""Workflow planning and query decomposition for multi-step agentic workflows.

This module implements the query complexity classifier and task decomposition
engine for Story 3.5: Multi-Step Workflow Orchestration.

This is a facade module that re-exports functionality from specialized submodules.
"""

# Re-export models and types
# Re-export classification functionality
from raglite.agentic.planner_classifier import classify_query_complexity

# Re-export decomposition functionality
from raglite.agentic.planner_decomposition import _has_circular_dependencies, decompose_query
from raglite.agentic.planner_models import (
    AgentResult,
    AgentTask,
    QueryComplexity,
    WorkflowPlan,
)

# Public API - maintain backward compatibility
__all__ = [
    # Enums and models
    "QueryComplexity",
    "AgentTask",
    "WorkflowPlan",
    "AgentResult",
    # Functions
    "classify_query_complexity",
    "decompose_query",
    "_has_circular_dependencies",  # Used by tests
]
