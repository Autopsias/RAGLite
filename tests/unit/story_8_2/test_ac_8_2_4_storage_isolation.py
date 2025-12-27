"""AC-8.2.4 ATDD Tests: Storage Operations Isolated and Testable.

Story 8.2: External Data Client Refactoring

Given storage.py mixes multiple concerns (CRUD, freshness, tier2, model weights, model selection)
When the refactoring is complete
Then storage operations are isolated into domain-specific modules:
  - Core CRUD operations
  - Freshness tracking
  - Tier 2 data storage
  - Model weight storage
  - Model selection caching

Verification:
- Each domain has its own module with focused responsibility
- Modules can be imported independently
- Each module has corresponding unit tests
- No circular dependencies between storage modules
"""

from __future__ import annotations

import ast

import pytest

from tests.unit.story_8_2.conftest import (
    HARD_LOC_LIMIT,
    STORAGE_PACKAGE,
    count_lines_simple,
)

pytestmark = [pytest.mark.unit]


class TestAC824StorageModulesExist:
    """[AC-8.2.4] Verify storage modules are isolated."""

    def test_ac_8_2_4_storage_package_exists(self) -> None:
        """[TEST-AC-8.2.4-A] storage/ package should exist.

        Given refactoring is complete
        When we check raglite/external_data/storage/
        Then the directory exists with __init__.py
        """
        assert STORAGE_PACKAGE.exists(), f"Storage package not found at {STORAGE_PACKAGE}"
        assert (STORAGE_PACKAGE / "__init__.py").exists(), "storage/__init__.py not found"

    def test_ac_8_2_4_core_module_exists(self) -> None:
        """[TEST-AC-8.2.4-B] storage/core.py should exist for CRUD operations.

        Expected: ~350 LOC with ExternalDataStorage class core methods
        """
        core_file = STORAGE_PACKAGE / "core.py"
        assert core_file.exists(), f"storage/core.py not found at {core_file}"

        loc = count_lines_simple(core_file)
        assert loc < HARD_LOC_LIMIT, f"storage/core.py has {loc} LOC, expected < {HARD_LOC_LIMIT}"

    def test_ac_8_2_4_freshness_module_exists(self) -> None:
        """[TEST-AC-8.2.4-C] storage/freshness.py should exist.

        Expected: ~250 LOC with freshness tracking methods
        """
        freshness_file = STORAGE_PACKAGE / "freshness.py"
        assert freshness_file.exists(), f"storage/freshness.py not found at {freshness_file}"

        loc = count_lines_simple(freshness_file)
        assert loc < HARD_LOC_LIMIT, (
            f"storage/freshness.py has {loc} LOC, expected < {HARD_LOC_LIMIT}"
        )

    def test_ac_8_2_4_tier2_module_exists(self) -> None:
        """[TEST-AC-8.2.4-D] storage/tier2.py should exist.

        Expected: ~270 LOC with tier 2 data storage methods
        """
        tier2_file = STORAGE_PACKAGE / "tier2.py"
        assert tier2_file.exists(), f"storage/tier2.py not found at {tier2_file}"

        loc = count_lines_simple(tier2_file)
        assert loc < HARD_LOC_LIMIT, f"storage/tier2.py has {loc} LOC, expected < {HARD_LOC_LIMIT}"

    def test_ac_8_2_4_model_weights_module_exists(self) -> None:
        """[TEST-AC-8.2.4-E] storage/model_weights.py should exist.

        Expected: ~200 LOC with model weight storage methods
        """
        weights_file = STORAGE_PACKAGE / "model_weights.py"
        assert weights_file.exists(), f"storage/model_weights.py not found at {weights_file}"

        loc = count_lines_simple(weights_file)
        assert loc < HARD_LOC_LIMIT, (
            f"storage/model_weights.py has {loc} LOC, expected < {HARD_LOC_LIMIT}"
        )

    def test_ac_8_2_4_model_selection_module_exists(self) -> None:
        """[TEST-AC-8.2.4-F] storage/model_selection.py should exist.

        Expected: ~350 LOC with model selection caching methods
        """
        selection_file = STORAGE_PACKAGE / "model_selection.py"
        assert selection_file.exists(), f"storage/model_selection.py not found at {selection_file}"

        loc = count_lines_simple(selection_file)
        assert loc < HARD_LOC_LIMIT, (
            f"storage/model_selection.py has {loc} LOC, expected < {HARD_LOC_LIMIT}"
        )

    def test_ac_8_2_4_constants_module_exists(self) -> None:
        """[TEST-AC-8.2.4-G] storage/constants.py should exist.

        Expected: ~60 LOC with TIER2_SOURCES and thresholds
        """
        constants_file = STORAGE_PACKAGE / "constants.py"
        assert constants_file.exists(), f"storage/constants.py not found at {constants_file}"

        loc = count_lines_simple(constants_file)
        assert loc < HARD_LOC_LIMIT, (
            f"storage/constants.py has {loc} LOC, expected < {HARD_LOC_LIMIT}"
        )


class TestAC824IndependentImports:
    """[AC-8.2.4] Verify modules can be imported independently."""

    def test_ac_8_2_4_core_importable(self) -> None:
        """[TEST-AC-8.2.4-H] storage.core can be imported independently.

        Given storage/core.py exists
        When we import it
        Then no import errors occur
        """
        try:
            import raglite.external_data.storage.core  # type: ignore[attr-defined]
        except ImportError as e:
            pytest.fail(f"Failed to import storage.core: {e}")

    def test_ac_8_2_4_freshness_importable(self) -> None:
        """[TEST-AC-8.2.4-I] storage.freshness can be imported independently."""
        try:
            import raglite.external_data.storage.freshness  # type: ignore[attr-defined]
        except ImportError as e:
            pytest.fail(f"Failed to import storage.freshness: {e}")

    def test_ac_8_2_4_tier2_importable(self) -> None:
        """[TEST-AC-8.2.4-J] storage.tier2 can be imported independently."""
        try:
            import raglite.external_data.storage.tier2  # type: ignore[attr-defined]
        except ImportError as e:
            pytest.fail(f"Failed to import storage.tier2: {e}")

    def test_ac_8_2_4_model_weights_importable(self) -> None:
        """[TEST-AC-8.2.4-K] storage.model_weights can be imported independently."""
        try:
            import raglite.external_data.storage.model_weights  # type: ignore[attr-defined]
        except ImportError as e:
            pytest.fail(f"Failed to import storage.model_weights: {e}")

    def test_ac_8_2_4_model_selection_importable(self) -> None:
        """[TEST-AC-8.2.4-L] storage.model_selection can be imported independently."""
        try:
            import raglite.external_data.storage.model_selection  # type: ignore[attr-defined]
        except ImportError as e:
            pytest.fail(f"Failed to import storage.model_selection: {e}")

    def test_ac_8_2_4_constants_importable(self) -> None:
        """[TEST-AC-8.2.4-M] storage.constants can be imported independently."""
        try:
            import raglite.external_data.storage.constants  # type: ignore[attr-defined]
        except ImportError as e:
            pytest.fail(f"Failed to import storage.constants: {e}")


class TestAC824NoCircularDependencies:
    """[AC-8.2.4] Verify no circular dependencies between storage modules."""

    def test_ac_8_2_4_no_circular_deps_in_storage(self) -> None:
        """[TEST-AC-8.2.4-N] Storage modules should have no circular deps.

        Given all storage modules exist
        When we analyze imports
        Then no circular import patterns exist
        """
        if not STORAGE_PACKAGE.exists():
            pytest.fail(f"Storage package not found at {STORAGE_PACKAGE}")

        modules = [
            "core",
            "freshness",
            "tier2",
            "model_weights",
            "model_selection",
            "constants",
        ]

        # Build import graph
        import_graph: dict[str, set[str]] = {}

        for module_name in modules:
            module_file = STORAGE_PACKAGE / f"{module_name}.py"
            if not module_file.exists():
                continue

            content = module_file.read_text()
            tree = ast.parse(content)

            imports: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if "raglite.external_data.storage" in alias.name:
                            # Extract the last part (module name)
                            parts = alias.name.split(".")
                            if parts[-1] in modules:
                                imports.add(parts[-1])
                elif isinstance(node, ast.ImportFrom):
                    if node.module and "raglite.external_data.storage" in node.module:
                        parts = node.module.split(".")
                        if parts[-1] in modules:
                            imports.add(parts[-1])

            import_graph[module_name] = imports

        # Check for cycles using DFS
        def has_cycle(node: str, visited: set, path: set) -> list | None:
            visited.add(node)
            path.add(node)

            for neighbor in import_graph.get(node, set()):
                if neighbor not in visited:
                    cycle = has_cycle(neighbor, visited, path)
                    if cycle is not None:
                        return [node] + cycle
                elif neighbor in path:
                    return [node, neighbor]

            path.remove(node)
            return None

        visited: set[str] = set()
        for module_name in modules:
            if module_name not in visited:
                cycle = has_cycle(module_name, visited, set())
                if cycle:
                    pytest.fail(f"Circular dependency detected: {' -> '.join(cycle)}")

    def test_ac_8_2_4_constants_has_no_internal_imports(self) -> None:
        """[TEST-AC-8.2.4-O] constants.py should not import other storage modules.

        Constants module should be a leaf node with no internal deps.
        """
        constants_file = STORAGE_PACKAGE / "constants.py"
        if not constants_file.exists():
            pytest.fail(f"storage/constants.py not found at {constants_file}")

        content = constants_file.read_text()
        tree = ast.parse(content)

        internal_imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if "raglite.external_data.storage" in alias.name:
                        internal_imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module and "raglite.external_data.storage" in node.module:
                    # Ignore self-imports from __init__
                    if not node.module.endswith("storage"):
                        internal_imports.append(node.module)

        assert not internal_imports, (
            f"constants.py has internal imports (should be leaf node): {internal_imports}"
        )


class TestAC824FocusedResponsibility:
    """[AC-8.2.4] Verify each module has focused responsibility."""

    def test_ac_8_2_4_core_has_crud_methods(self) -> None:
        """[TEST-AC-8.2.4-P] storage/core.py should have CRUD methods.

        Expected: create_source, get_source, insert_data_points, query_data_points
        """
        core_file = STORAGE_PACKAGE / "core.py"
        if not core_file.exists():
            pytest.fail(f"storage/core.py not found at {core_file}")

        content = core_file.read_text()
        expected_methods = [
            "create_source",
            "get_source",
            "insert_data_points",
        ]

        for method in expected_methods:
            assert method in content, f"Expected CRUD method '{method}' not found in core.py"

    def test_ac_8_2_4_freshness_has_tracking_methods(self) -> None:
        """[TEST-AC-8.2.4-Q] storage/freshness.py should have freshness methods.

        Expected: is_fresh, get_freshness, get_stale_sources
        """
        freshness_file = STORAGE_PACKAGE / "freshness.py"
        if not freshness_file.exists():
            pytest.fail(f"storage/freshness.py not found at {freshness_file}")

        content = freshness_file.read_text()
        expected_patterns = ["is_fresh", "freshness", "stale"]

        found = any(pattern in content.lower() for pattern in expected_patterns)
        assert found, (
            f"Freshness-related methods not found in freshness.py. "
            f"Expected patterns: {expected_patterns}"
        )

    def test_ac_8_2_4_tier2_has_tier2_methods(self) -> None:
        """[TEST-AC-8.2.4-R] storage/tier2.py should have tier 2 methods.

        Expected: tier2 storage methods, TIER2_SOURCES usage
        """
        tier2_file = STORAGE_PACKAGE / "tier2.py"
        if not tier2_file.exists():
            pytest.fail(f"storage/tier2.py not found at {tier2_file}")

        content = tier2_file.read_text()
        expected_patterns = ["tier2", "tier_2", "store_"]

        found = any(pattern in content.lower() for pattern in expected_patterns)
        assert found, (
            f"Tier 2-related methods not found in tier2.py. Expected patterns: {expected_patterns}"
        )

    def test_ac_8_2_4_model_weights_has_weight_methods(self) -> None:
        """[TEST-AC-8.2.4-S] storage/model_weights.py should have weight methods.

        Expected: save_weights, get_weights, delete_weights
        """
        weights_file = STORAGE_PACKAGE / "model_weights.py"
        if not weights_file.exists():
            pytest.fail(f"storage/model_weights.py not found at {weights_file}")

        content = weights_file.read_text()
        expected_patterns = ["weight", "save", "get"]

        found_count = sum(1 for p in expected_patterns if p in content.lower())
        assert found_count >= 2, (
            f"Weight-related methods not found in model_weights.py. "
            f"Expected patterns: {expected_patterns}"
        )

    def test_ac_8_2_4_model_selection_has_cache_methods(self) -> None:
        """[TEST-AC-8.2.4-T] storage/model_selection.py should have cache methods.

        Expected: cache_selection, get_cached_selection, invalidate
        """
        selection_file = STORAGE_PACKAGE / "model_selection.py"
        if not selection_file.exists():
            pytest.fail(f"storage/model_selection.py not found at {selection_file}")

        content = selection_file.read_text()
        expected_patterns = ["cache", "selection", "invalidate"]

        found_count = sum(1 for p in expected_patterns if p in content.lower())
        assert found_count >= 2, (
            f"Cache-related methods not found in model_selection.py. "
            f"Expected patterns: {expected_patterns}"
        )
