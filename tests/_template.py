"""
Test file template showing correct pytestmark placement.

CRITICAL: pytestmark MUST be placed AFTER all imports to avoid E402 violations.

Root Cause:
    pytestmark is module-level code that executes at import time.
    When placed before or between imports, it violates ruff E402 (import not at top of file).

Correct Pattern:
    1. All imports first (standard lib, third-party, local)
    2. Blank line
    3. pytestmark declaration
    4. Blank line
    5. Test code

Example:
"""

# ============ STANDARD LIBRARY IMPORTS ============

# ============ THIRD-PARTY IMPORTS ============
import pytest

# ============ LOCAL IMPORTS ============


# ============ PYTEST MARKER (AFTER ALL IMPORTS) ============
pytestmark = pytest.mark.integration  # CORRECT: After imports


# ============ TESTS ============
class TestExample:
    """Example test class."""

    def test_example(self):
        """Example test method."""
        assert True


# ============ COMMON PATTERNS ============

# Pattern 1: Single marker
# pytestmark = pytest.mark.integration

# Pattern 2: Multiple markers (use list)
# pytestmark = [pytest.mark.integration, pytest.mark.slow]

# Pattern 3: Conditional marker (rare, avoid)
# pytestmark = pytest.mark.skipif(condition, reason="...")

# ============ WRONG PATTERNS (DO NOT USE) ============

# WRONG: pytestmark before imports
# pytestmark = pytest.mark.integration  # ❌ VIOLATES E402
# import pytest  # Import after module-level code

# WRONG: pytestmark between imports
# import pytest
# pytestmark = pytest.mark.integration  # ❌ VIOLATES E402
# from qdrant_client import QdrantClient  # Import after module-level code
