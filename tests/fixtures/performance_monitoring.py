"""Performance monitoring hooks for pytest test sessions.

This module contains pytest hooks for monitoring test suite performance:
- Session start/finish timing
- Performance budget validation against baseline
- Actionable guidance for performance regressions

These hooks are loaded by pytest via pytest_plugins in the root conftest.py.
"""

import json
import logging
import time
from pathlib import Path

from _pytest.main import Session

logger = logging.getLogger(__name__)

# Track session start time for performance monitoring
_session_start_time: float | None = None


def pytest_sessionstart(session: Session) -> None:
    """Record session start time for performance monitoring.

    Args:
        session: pytest session object
    """
    global _session_start_time
    _session_start_time = time.time()


def pytest_sessionfinish(session: Session, exitstatus: int) -> None:
    """Check test suite duration against performance budget.

    PERFORMANCE MONITORING (2025-12-07):
    - Compares actual duration against tests/performance_baseline.json
    - Warns if budget exceeded by >25%
    - Provides actionable guidance for performance regressions

    This hook prevents recurring performance regressions by making
    slowdowns visible immediately after test runs.

    Args:
        session: pytest session object
        exitstatus: pytest exit status code
    """
    global _session_start_time
    if _session_start_time is None:
        return

    elapsed_seconds = time.time() - _session_start_time

    # Load performance baseline
    baseline_path = Path(__file__).parent.parent / "performance_baseline.json"
    if not baseline_path.exists():
        return

    try:
        with open(baseline_path) as f:
            baseline = json.load(f)

        # Determine which budget to check based on test count
        passed = session.testscollected - session.testsfailed - getattr(session, "skipped", 0)

        # Check integration tests budget (most common)
        budget_name = "integration_skip_ingestion"
        if budget_name in baseline.get("budgets", {}):
            budget = baseline["budgets"][budget_name]
            max_seconds = budget["max_seconds"]

            # Only check if we ran a significant number of tests
            if passed > 50:  # Likely running integration suite
                if elapsed_seconds > max_seconds:
                    overage_pct = ((elapsed_seconds - max_seconds) / max_seconds) * 100

                    print(f"\n{'=' * 80}")
                    print("PERFORMANCE WARNING: Test suite exceeded time budget")
                    print(f"{'=' * 80}")
                    print(f"  Actual time:    {elapsed_seconds:.1f}s")
                    print(f"  Budget:         {max_seconds}s ({budget['description']})")
                    print(f"  Overage:        +{overage_pct:.1f}%")
                    print("")
                    print("  Possible causes:")
                    print("    - Missing @pytest.mark.preserve_collection on read-only tests")
                    print("    - Over-aggressive restoration in ensure_qdrant_test_isolation")
                    print("    - New slow tests without @pytest.mark.slow marker")
                    print("")
                    print("  To investigate:")
                    print("    pytest tests/integration/ --skip-ingestion --durations=20")
                    print(f"{'=' * 80}\n")

                elif elapsed_seconds < max_seconds * 0.7:
                    # Test suite was faster than expected - good!
                    print(
                        f"\n✅ Test suite completed in {elapsed_seconds:.1f}s (budget: {max_seconds}s)"
                    )

    except Exception as e:
        # Don't fail tests due to performance monitoring errors
        logger.debug(f"Performance monitoring skipped: {e}")
