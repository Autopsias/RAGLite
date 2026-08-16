"""Unit tests for Query Intelligence features (Phase 5).

Story 5.0.7: Tests for metric name extraction, entity resolution,
and query reformulation fallback chain.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest


class TestMetricNameExtraction:
    """Test Phase 5.1: Metric name extraction via get_metric_names()."""

    @pytest.mark.asyncio
    async def test_get_metric_names_returns_strings(self):
        """Test get_metric_names returns list of strings."""
        from raglite.forecasting.metrics import MetricInfo
        from raglite.retrieval.search import get_metric_names

        # Mock list_available_metrics to return test data
        mock_metrics = [
            MetricInfo(name="Revenue", data_point_count=10, can_forecast=True),
            MetricInfo(name="EBITDA", data_point_count=8, can_forecast=True),
            MetricInfo(name="Variable Cost", data_point_count=5, can_forecast=False),
        ]

        with patch(
            "raglite.forecasting.metrics.list_available_metrics",
            new_callable=AsyncMock,
            return_value=mock_metrics,
        ):
            names = await get_metric_names()

        assert isinstance(names, list)
        assert all(isinstance(n, str) for n in names)
        assert "Revenue" in names
        assert "EBITDA" in names
        assert "Variable Cost" in names

    @pytest.mark.asyncio
    async def test_get_metric_names_uses_cache(self):
        """Test get_metric_names passes use_cache parameter."""
        from raglite.forecasting.metrics import MetricInfo
        from raglite.retrieval.search import get_metric_names

        mock_metrics = [
            MetricInfo(name="Test Metric", data_point_count=10, can_forecast=True),
        ]

        with patch(
            "raglite.forecasting.metrics.list_available_metrics",
            new_callable=AsyncMock,
            return_value=mock_metrics,
        ) as mock_fn:
            # Call with cache enabled (default)
            await get_metric_names()
            mock_fn.assert_called_with(use_cache=True)

            # Call with cache disabled
            await get_metric_names(use_cache=False)
            mock_fn.assert_called_with(use_cache=False)

    @pytest.mark.asyncio
    async def test_get_metric_names_empty_db(self):
        """Test get_metric_names handles empty database gracefully."""
        from raglite.retrieval.search import get_metric_names

        with patch(
            "raglite.forecasting.metrics.list_available_metrics",
            new_callable=AsyncMock,
            return_value=[],
        ):
            names = await get_metric_names()

        assert names == []


class TestEntityResolver:
    """Test Phase 5.2: Semantic entity resolution."""

    def test_entity_normalizer_exists(self):
        """Test entity normalizer module exists (from Phase 2)."""
        from raglite.ingestion.entity_normalizer import normalize_entity

        # Should be able to import the function
        assert callable(normalize_entity)

    def test_entity_normalizer_normalize(self):
        """Test entity normalization for common patterns."""
        from raglite.ingestion.entity_normalizer import normalize_entity

        # Test canonical normalization (from Phase 2)
        assert normalize_entity("PORTUGAL") == "Portugal"
        assert normalize_entity("GROUP") == "Group"

    def test_entity_normalizer_handles_unknown(self):
        """Test entity normalizer returns original for unknown entities."""
        from raglite.ingestion.entity_normalizer import normalize_entity

        # Unknown entities should pass through
        result = normalize_entity("Unknown Corp XYZ")
        # Should not crash, may return original or cleaned version
        assert isinstance(result, str)


class TestSemanticEntityResolver:
    """Test Phase 5.2: Semantic entity resolution using Fin-E5 embeddings."""

    def test_entity_resolver_module_exists(self):
        """Test entity_resolver.py module exists and can be imported."""
        from raglite.retrieval.entity_resolver import resolve_entity_semantic

        assert callable(resolve_entity_semantic)

    def test_resolve_entities_in_query_exists(self):
        """Test resolve_entities_in_query function exists."""
        from raglite.retrieval.entity_resolver import resolve_entities_in_query

        assert callable(resolve_entities_in_query)

    def test_cosine_similarity_function(self):
        """Test internal cosine similarity function."""
        from raglite.retrieval.entity_resolver import _cosine_similarity

        # Identical vectors should have similarity 1.0
        vec = np.array([1.0, 0.0, 0.0])
        assert abs(_cosine_similarity(vec, vec) - 1.0) < 0.001

        # Orthogonal vectors should have similarity 0.0
        vec1 = np.array([1.0, 0.0, 0.0])
        vec2 = np.array([0.0, 1.0, 0.0])
        assert abs(_cosine_similarity(vec1, vec2)) < 0.001

        # Opposite vectors should have similarity -1.0
        vec1 = np.array([1.0, 0.0, 0.0])
        vec2 = np.array([-1.0, 0.0, 0.0])
        assert abs(_cosine_similarity(vec1, vec2) + 1.0) < 0.001

    def test_resolve_entity_semantic_empty_input(self):
        """Test resolve_entity_semantic handles empty input."""
        from raglite.retrieval.entity_resolver import resolve_entity_semantic

        assert resolve_entity_semantic("") is None
        assert resolve_entity_semantic("   ") is None
        assert resolve_entity_semantic(None) is None

    def test_resolve_entity_semantic_with_mocked_embeddings(self):
        """Test semantic resolution with mocked embedding model."""
        from raglite.retrieval.entity_resolver import resolve_entity_semantic

        # Create mock embedding model
        mock_model = MagicMock()

        # Mock embeddings: Portugal and Group as canonical entities
        # Query "Portuguese Cement" should be closer to "Portugal"
        def mock_encode(texts, **kwargs):
            embeddings = []
            for text in texts:
                if "Portugal" in text:
                    embeddings.append(np.array([1.0, 0.0, 0.0]))
                elif "Group" in text:
                    embeddings.append(np.array([0.0, 1.0, 0.0]))
                elif "Portuguese" in text or "Cement" in text:
                    # Similar to Portugal
                    embeddings.append(np.array([0.9, 0.1, 0.0]))
                else:
                    embeddings.append(np.array([0.3, 0.3, 0.3]))
            return np.array(embeddings)

        mock_model.encode = mock_encode

        with patch(
            "raglite.retrieval.entity_resolver.get_embedding_model",
            return_value=mock_model,
        ):
            with patch(
                "raglite.retrieval.entity_resolver.get_all_canonical_entities",
                return_value=["Portugal", "Group"],
            ):
                # Clear the LRU cache to force recalculation
                from raglite.retrieval.entity_resolver import _get_canonical_entity_embeddings

                _get_canonical_entity_embeddings.cache_clear()

                # Test: "Portuguese Cement" should resolve to "Portugal"
                result = resolve_entity_semantic("Portuguese Cement")
                assert result == "Portugal"

    def test_similarity_threshold(self):
        """Test that similarity threshold is applied correctly."""
        from raglite.retrieval.entity_resolver import SIMILARITY_THRESHOLD

        # Threshold should be 0.7 as specified in story
        assert SIMILARITY_THRESHOLD == 0.7


class TestQueryReformulation:
    """Test Phase 5.3: Query reformulation fallback chain."""

    def test_metric_synonym_expansion_exists(self):
        """Test expand_metric_synonyms function exists."""
        from raglite.retrieval.query_classifier import expand_metric_synonyms

        assert callable(expand_metric_synonyms)

    def test_metric_synonym_expansion_petcoke(self):
        """Test petcoke synonym expansion (critical for Story 5.0.7)."""
        from raglite.retrieval.query_classifier import expand_metric_synonyms

        result = expand_metric_synonyms("What is the petcoke consumption?")
        assert "Petcoke Consumption" in result or "Pet Coke" in result

    def test_metric_synonym_expansion_energy(self):
        """Test energy synonym expansion."""
        from raglite.retrieval.query_classifier import expand_metric_synonyms

        result = expand_metric_synonyms("Show energy metrics")
        assert "Electrical Energy" in result or "Thermal Energy" in result

    def test_metric_synonym_expansion_no_match(self):
        """Test synonym expansion returns empty for unknown metrics."""
        from raglite.retrieval.query_classifier import expand_metric_synonyms

        result = expand_metric_synonyms("Random words here")
        assert result == []


class TestQueryReformulationFallbackChain:
    """Test Phase 5.3: Query reformulation fallback chain implementation."""

    def test_reformulate_query_exists(self):
        """Test reformulate_query function exists."""
        from raglite.retrieval.search import reformulate_query

        assert callable(reformulate_query)

    def test_search_with_reformulation_exists(self):
        """Test search_with_reformulation function exists."""
        from raglite.retrieval.search import search_with_reformulation

        assert callable(search_with_reformulation)

    @pytest.mark.asyncio
    async def test_reformulate_query_fallback_1_metric_synonyms(self):
        """Test fallback 1: metric synonym expansion."""
        from raglite.retrieval.search import reformulate_query

        query = "What is petcoke consumption?"
        reformulated, fallback_type = await reformulate_query(query, fallback_level=1)

        # Should expand petcoke synonyms
        assert "Petcoke Consumption" in reformulated or "Pet Coke" in reformulated
        assert fallback_type == "metric_synonym_expansion"

    @pytest.mark.asyncio
    async def test_reformulate_query_fallback_2_entity_synonyms(self):
        """Test fallback 2: entity synonym expansion."""
        from raglite.retrieval.search import reformulate_query

        query = "What is revenue for portugal?"
        reformulated, fallback_type = await reformulate_query(query, fallback_level=2)

        # Should expand Portugal entity synonyms
        assert "Portugal" in reformulated or "PT" in reformulated
        assert fallback_type == "entity_synonym_expansion"

    @pytest.mark.asyncio
    async def test_reformulate_query_fallback_3_time_period_removal(self):
        """Test fallback 3: time period removal."""
        from raglite.retrieval.search import reformulate_query

        query = "What is EBITDA for Q3 2024?"
        reformulated, fallback_type = await reformulate_query(query, fallback_level=3)

        # Should remove time period
        assert "Q3 2024" not in reformulated
        assert "EBITDA" in reformulated
        assert fallback_type == "time_period_removal"

    @pytest.mark.asyncio
    async def test_reformulate_query_no_match(self):
        """Test reformulation when no synonyms match."""
        from raglite.retrieval.search import reformulate_query

        query = "Random unknown query xyz"
        reformulated, fallback_type = await reformulate_query(query, fallback_level=1)

        # Should return original query
        assert reformulated == query
        assert fallback_type == "no_metric_synonyms"


class TestTimePeriodRemoval:
    """Test time period removal patterns for fallback 3."""

    def test_remove_time_periods_year(self):
        """Test removal of year patterns."""
        from raglite.retrieval.search import _remove_time_periods

        assert "2024" not in _remove_time_periods("Revenue in 2024")
        assert "2024" not in _remove_time_periods("Revenue for 2024")

    def test_remove_time_periods_quarter(self):
        """Test removal of quarter patterns."""
        from raglite.retrieval.search import _remove_time_periods

        assert "Q3" not in _remove_time_periods("EBITDA for Q3")
        assert "Q1" not in _remove_time_periods("EBITDA in Q1")
        assert "Q3 2024" not in _remove_time_periods("Revenue Q3 2024")

    def test_remove_time_periods_month(self):
        """Test removal of month patterns."""
        from raglite.retrieval.search import _remove_time_periods

        result = _remove_time_periods("Revenue January 2024")
        assert "January" not in result
        assert "2024" not in result

    def test_remove_time_periods_relative(self):
        """Test removal of relative time patterns."""
        from raglite.retrieval.search import _remove_time_periods

        assert "last year" not in _remove_time_periods("Revenue last year")
        assert "this quarter" not in _remove_time_periods("EBITDA this quarter")

    def test_remove_time_periods_preserves_content(self):
        """Test that non-time content is preserved."""
        from raglite.retrieval.search import _remove_time_periods

        result = _remove_time_periods("What is EBITDA for Q3 2024?")
        assert "EBITDA" in result
        assert result.strip().endswith("?")

    def test_remove_time_periods_no_match(self):
        """Test query without time periods is unchanged."""
        from raglite.retrieval.search import _remove_time_periods

        query = "What is the revenue?"
        assert _remove_time_periods(query) == query


class TestEntitySynonymExpansion:
    """Test entity synonym expansion for query reformulation."""

    def test_entity_synonym_patterns(self):
        """Test entity synonym patterns exist in classification.py."""
        from raglite.ingestion.adaptive_table.classification import HeaderType, classify_header

        # Common entity patterns should be recognized
        assert classify_header("Portugal") == HeaderType.ENTITY
        assert classify_header("Group") == HeaderType.ENTITY
        assert classify_header("Tunisia") == HeaderType.ENTITY


class TestQueryIntelligenceIntegration:
    """Integration tests for query intelligence features."""

    @pytest.mark.asyncio
    async def test_metric_names_metric_synonym_chain(self):
        """Test that metric names and synonyms work together."""
        from raglite.retrieval.query_classifier import expand_metric_synonyms

        # Get synonyms for common query
        synonyms = expand_metric_synonyms("What is revenue?")

        # Should expand to database metric names
        assert "Revenue" in synonyms or len(synonyms) > 0

    def test_phase5_import_chain(self):
        """Test all Phase 5 components can be imported."""
        # These imports should not fail
        from raglite.ingestion.entity_normalizer import expand_entity_synonyms, normalize_entity
        from raglite.retrieval.entity_resolver import (
            resolve_entities_in_query,
            resolve_entity_semantic,
        )
        from raglite.retrieval.query_classifier import METRIC_SYNONYMS, expand_metric_synonyms
        from raglite.retrieval.search import (
            _remove_time_periods,
            get_metric_names,
            reformulate_query,
            search_with_reformulation,
        )

        assert callable(get_metric_names)
        assert callable(expand_metric_synonyms)
        assert callable(normalize_entity)
        assert callable(expand_entity_synonyms)
        assert callable(resolve_entity_semantic)
        assert callable(resolve_entities_in_query)
        assert callable(reformulate_query)
        assert callable(search_with_reformulation)
        assert callable(_remove_time_periods)
        assert isinstance(METRIC_SYNONYMS, dict)

    def test_phase5_fallback_chain_complete(self):
        """Test that all 3 fallback stages are implemented."""
        from raglite.retrieval.search import TIME_PERIOD_PATTERNS

        # Verify time period patterns exist for fallback 3
        assert len(TIME_PERIOD_PATTERNS) >= 10

        # Verify fallback functions exist
        from raglite.retrieval.search import reformulate_query

        assert callable(reformulate_query)
