"""
ATDD tests for Story 7b-5: Model Selection Slash Commands & Subagent.

FACADE FILE: This file re-exports all tests from split modules for backward compatibility.

The actual tests have been split into:
- test_model_selection_command.py: Slash command and subagent file tests
- test_model_selection_api.py: Function signature and API tests
- test_model_selection_execution.py: Execution logic and error handling
- test_model_selection_reports.py: Report generation and progress logging
- test_model_selection_edge_cases.py: Edge cases and performance tests

TDD RED Phase: These tests should FAIL until implementation is complete.

This test file covers:
- AC-7b.5.1: Slash Command Definition
- AC-7b.5.2: Model-Selection-Executor Subagent
- AC-7b.5.3: run_batch_model_selection() Python Function
- AC-7b.5.4: Parallel Execution (4 Workers)
- AC-7b.5.5: Cache Results in PostgreSQL
- AC-7b.5.6: Generate JSON + Markdown Report
- AC-7b.5.7: Progress Logging with Status Updates
- AC-7b.5.8: Runtime Less Than 120 Minutes (P2 - Performance test)

Priority levels:
- P0: Critical path tests (must pass for story completion)
- P1: Important scenarios (should pass)
- P2: Edge cases and performance tests
"""

from __future__ import annotations

# Import all test classes from API tests
from tests.unit.test_model_selection_api import (
    TestCandidateModelsImport,
    TestModelSelectionJobModuleExists,
    TestParallelExecution,
    TestRunBatchModelSelection,
)

# Re-export all test classes from split modules for backward compatibility
# This allows existing test runners and CI to continue using the original import path
# Import all test classes from command tests
from tests.unit.test_model_selection_command import (
    TestSlashCommandFile,
    TestSubagentFile,
)

# Import all test classes from edge case tests
from tests.unit.test_model_selection_edge_cases import (
    TestEdgeCases,
    TestRuntimePerformance,
)

# Import all test classes from execution tests
from tests.unit.test_model_selection_execution import (
    TestCacheResults,
    TestErrorHandling,
    TestRunSingleVariableSelection,
    TestSingleVariableSelection,
)

# Import all test classes from report tests
from tests.unit.test_model_selection_reports import (
    TestProgressLogging,
    TestReportGeneration,
    TestReportStructure,
)

__all__ = [
    # Command tests
    "TestSlashCommandFile",
    "TestSubagentFile",
    # API tests
    "TestModelSelectionJobModuleExists",
    "TestRunBatchModelSelection",
    "TestParallelExecution",
    "TestCandidateModelsImport",
    # Execution tests
    "TestRunSingleVariableSelection",
    "TestSingleVariableSelection",
    "TestCacheResults",
    "TestErrorHandling",
    # Report tests
    "TestReportGeneration",
    "TestProgressLogging",
    "TestReportStructure",
    # Edge case tests
    "TestEdgeCases",
    "TestRuntimePerformance",
]
