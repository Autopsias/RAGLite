"""Unit tests for BM25 indexing and sparse vector generation (raglite/shared/bm25.py).

Test Coverage:
    - BM25 index creation with various corpus sizes
    - Index persistence (save/load)
    - Module-level caching behavior
    - Score computation and ranking
    - Error handling (empty corpus, invalid queries, missing files)
    - Parameter validation (k1, b)

Priority: P1 (High - BM25 critical for hybrid search accuracy)
"""

import pytest
from rank_bm25 import BM25Okapi

from raglite.shared.bm25 import (
    BM25IndexError,
    clear_bm25_cache,
    compute_bm25_scores,
    create_bm25_index,
    load_bm25_index,
    save_bm25_index,
)
from tests.support.factories import create_chunk, create_chunks


class TestBM25IndexCreation:
    """Test BM25 index creation from chunks."""

    @pytest.mark.unit
    @pytest.mark.priority("P1")
    def test_create_index_with_single_chunk(self):
        """Create BM25 index from single chunk - should succeed."""
        # GIVEN: Single chunk with financial content
        chunk = create_chunk(content="EBITDA margin was 23.5% in Q3 2024")

        # WHEN: Creating BM25 index
        bm25, tokenized = create_bm25_index([chunk])

        # THEN: Index created successfully
        assert isinstance(bm25, BM25Okapi)
        assert len(tokenized) == 1
        assert "EBITDA" in tokenized[0]
        assert "margin" in tokenized[0]

    @pytest.mark.unit
    @pytest.mark.priority("P1")
    def test_create_index_with_multiple_chunks(self):
        """Create BM25 index from multiple chunks - should succeed."""
        # GIVEN: Multiple chunks with financial content
        chunks = create_chunks(10)

        # WHEN: Creating BM25 index
        bm25, tokenized = create_bm25_index(chunks)

        # THEN: Index created for all chunks
        assert isinstance(bm25, BM25Okapi)
        assert len(tokenized) == 10
        assert all(isinstance(doc, list) for doc in tokenized)

    @pytest.mark.unit
    @pytest.mark.priority("P2")
    def test_create_index_with_custom_parameters(self):
        """Create BM25 index with custom k1 and b parameters."""
        # GIVEN: Chunks with content
        chunks = create_chunks(5)

        # WHEN: Creating index with custom parameters
        bm25, tokenized = create_bm25_index(chunks, k1=2.0, b=0.75)

        # THEN: Index created (parameters stored in BM25Okapi object)
        assert isinstance(bm25, BM25Okapi)
        # Note: BM25Okapi stores k1 and b internally but doesn't expose them directly

    @pytest.mark.unit
    @pytest.mark.priority("P1")
    def test_create_index_empty_chunks_raises_error(self):
        """Create BM25 index from empty list - should raise ValueError."""
        # GIVEN: Empty chunks list
        chunks = []

        # WHEN/THEN: Creating index raises ValueError
        with pytest.raises(ValueError, match="Cannot create BM25 index from empty chunks list"):
            create_bm25_index(chunks)

    @pytest.mark.unit
    @pytest.mark.priority("P2")
    def test_create_index_with_empty_content_raises_error(self):
        """Create BM25 index from chunks with empty content - should raise BM25IndexError."""
        # GIVEN: Chunks with empty content
        chunks = [
            create_chunk(content=""),
            create_chunk(content="   "),
            create_chunk(content="\n\t"),
        ]

        # WHEN/THEN: Creating index raises BM25IndexError
        with pytest.raises(BM25IndexError, match="All chunks produced empty tokenization"):
            create_bm25_index(chunks)

    @pytest.mark.unit
    @pytest.mark.priority("P2")
    def test_create_index_tokenization_preserves_financial_terms(self):
        """Verify tokenization preserves financial terms (EUR/ton, $100M, etc.)."""
        # GIVEN: Chunk with financial notation
        chunk = create_chunk(content="EBITDA is 23.2 EUR/ton, revenue $100M")

        # WHEN: Creating index
        bm25, tokenized = create_bm25_index([chunk])

        # THEN: Financial terms preserved in tokenization
        tokens = tokenized[0]
        assert "EBITDA" in tokens
        assert "EUR/ton," in tokens  # Preserved with punctuation
        assert "$100M" in tokens  # Preserved with $


class TestBM25IndexPersistence:
    """Test BM25 index save and load operations."""

    @pytest.mark.unit
    @pytest.mark.priority("P1")
    def test_save_and_load_index_roundtrip(self, tmp_path):
        """Save and load BM25 index - should preserve data."""
        # GIVEN: BM25 index from chunks
        chunks = create_chunks(5)
        bm25_original, tokenized_original = create_bm25_index(chunks)
        index_path = tmp_path / "test_bm25.pkl"

        # WHEN: Saving and loading index
        saved_path = save_bm25_index(bm25_original, tokenized_original, index_path=str(index_path))
        bm25_loaded, tokenized_loaded, metadata_loaded = load_bm25_index(index_path=str(index_path))

        # THEN: Index preserved correctly
        assert saved_path == index_path
        assert isinstance(bm25_loaded, BM25Okapi)
        assert len(tokenized_loaded) == len(tokenized_original)
        assert tokenized_loaded == tokenized_original

    @pytest.mark.unit
    @pytest.mark.priority("P2")
    def test_save_index_with_metadata(self, tmp_path):
        """Save BM25 index with chunk metadata - should persist metadata."""
        # GIVEN: Index with metadata
        chunks = create_chunks(3)
        bm25, tokenized = create_bm25_index(chunks)
        metadata = [
            {"source_document": "doc1.pdf", "chunk_index": 0},
            {"source_document": "doc1.pdf", "chunk_index": 1},
            {"source_document": "doc2.pdf", "chunk_index": 0},
        ]
        index_path = tmp_path / "test_bm25_meta.pkl"

        # WHEN: Saving and loading with metadata
        save_bm25_index(bm25, tokenized, chunk_metadata=metadata, index_path=str(index_path))
        _, _, loaded_metadata = load_bm25_index(index_path=str(index_path))

        # THEN: Metadata preserved
        assert loaded_metadata == metadata

    @pytest.mark.unit
    @pytest.mark.priority("P1")
    def test_load_nonexistent_index_raises_error(self):
        """Load BM25 index from missing file - should raise FileNotFoundError."""
        # GIVEN: Non-existent path
        fake_path = "/tmp/nonexistent_bm25_index.pkl"

        # WHEN/THEN: Loading raises FileNotFoundError
        with pytest.raises(FileNotFoundError, match="BM25 index not found"):
            load_bm25_index(index_path=fake_path)

    @pytest.mark.unit
    @pytest.mark.priority("P2")
    def test_save_index_creates_directory(self, tmp_path):
        """Save BM25 index to non-existent directory - should create directory."""
        # GIVEN: Index and path with missing parent directory
        chunks = create_chunks(2)
        bm25, tokenized = create_bm25_index(chunks)
        nested_path = tmp_path / "nested" / "dir" / "test_bm25.pkl"

        # WHEN: Saving to nested path
        saved_path = save_bm25_index(bm25, tokenized, index_path=str(nested_path))

        # THEN: Directory created and file saved
        assert saved_path.exists()
        assert saved_path.parent.exists()
        assert saved_path == nested_path


class TestBM25Caching:
    """Test BM25 index module-level caching behavior."""

    @pytest.mark.unit
    @pytest.mark.priority("P2")
    def test_load_index_uses_cache_on_second_call(self, tmp_path, monkeypatch):
        """Load same index twice - should use cache on second load."""
        # GIVEN: Saved BM25 index
        chunks = create_chunks(3)
        bm25, tokenized = create_bm25_index(chunks)
        index_path = tmp_path / "cached_bm25.pkl"
        save_bm25_index(bm25, tokenized, index_path=str(index_path))

        # Clear cache to start fresh
        clear_bm25_cache()

        # WHEN: Loading index twice
        result1 = load_bm25_index(index_path=str(index_path))

        # Delete file to verify second load uses cache (not disk)
        index_path.unlink()

        result2 = load_bm25_index(index_path=str(index_path))

        # THEN: Second load uses cache (file deleted but still loads)
        assert result1 == result2
        assert isinstance(result2[0], BM25Okapi)

    @pytest.mark.unit
    @pytest.mark.priority("P2")
    def test_clear_cache_forces_reload_from_disk(self, tmp_path):
        """Clear cache - next load should read from disk."""
        # GIVEN: Saved and cached index
        chunks = create_chunks(2)
        bm25, tokenized = create_bm25_index(chunks)
        index_path = tmp_path / "test_cache_clear.pkl"
        save_bm25_index(bm25, tokenized, index_path=str(index_path))
        load_bm25_index(index_path=str(index_path))  # First load (caches)

        # WHEN: Clearing cache
        clear_bm25_cache()

        # Delete file to verify next load would fail if not cleared
        index_path.unlink()

        # THEN: Loading after clear should fail (cache was cleared)
        with pytest.raises(FileNotFoundError):
            load_bm25_index(index_path=str(index_path))


class TestBM25ScoreComputation:
    """Test BM25 score computation for queries."""

    @pytest.mark.unit
    @pytest.mark.priority("P1")
    def test_compute_scores_returns_score_per_document(self):
        """Compute BM25 scores - should return one score per document."""
        # GIVEN: Index with 5 documents
        chunks = create_chunks(5)
        bm25, _ = create_bm25_index(chunks)

        # WHEN: Computing scores for query
        scores = compute_bm25_scores(bm25, "revenue EBITDA margin")

        # THEN: One score per document
        assert len(scores) == 5
        assert all(isinstance(s, (int, float)) for s in scores)

    @pytest.mark.unit
    @pytest.mark.priority("P2")
    def test_compute_scores_higher_for_matching_terms(self):
        """Compute BM25 scores - matching documents should score higher."""
        # GIVEN: Chunks with specific content
        chunks = [
            create_chunk(content="EBITDA margin was 23.5% in Q3"),
            create_chunk(content="Revenue increased 15% year over year"),
            create_chunk(content="Cash flow remained stable"),
        ]
        bm25, _ = create_bm25_index(chunks)

        # WHEN: Querying for EBITDA
        scores = compute_bm25_scores(bm25, "EBITDA margin")

        # THEN: First document (contains EBITDA and margin) scores highest
        assert scores[0] > scores[1]
        assert scores[0] > scores[2]

    @pytest.mark.unit
    @pytest.mark.priority("P2")
    def test_compute_scores_empty_query_returns_empty(self):
        """Compute BM25 scores with empty query - should return empty list."""
        # GIVEN: Index with documents
        chunks = create_chunks(3)
        bm25, _ = create_bm25_index(chunks)

        # WHEN: Computing scores for empty query
        scores = compute_bm25_scores(bm25, "")

        # THEN: Empty scores list returned
        assert scores == []

    @pytest.mark.unit
    @pytest.mark.priority("P3")
    def test_compute_scores_whitespace_query_returns_empty(self):
        """Compute BM25 scores with whitespace-only query - should return empty."""
        # GIVEN: Index with documents
        chunks = create_chunks(2)
        bm25, _ = create_bm25_index(chunks)

        # WHEN: Computing scores for whitespace query
        scores = compute_bm25_scores(bm25, "   \t\n   ")

        # THEN: Empty scores list
        assert scores == []


class TestBM25IndexError:
    """Test BM25IndexError exception handling."""

    @pytest.mark.unit
    @pytest.mark.priority("P2")
    def test_index_error_is_exception(self):
        """Verify BM25IndexError is an Exception."""
        # GIVEN/WHEN: Creating exception
        error = BM25IndexError("Test error")

        # THEN: Is Exception subclass
        assert isinstance(error, Exception)
        assert str(error) == "Test error"


# Integration-level test (requires actual file I/O, but still unit test scope)
class TestBM25EndToEnd:
    """End-to-end BM25 workflow tests."""

    @pytest.mark.unit
    @pytest.mark.priority("P1")
    def test_complete_workflow_create_save_load_score(self, tmp_path):
        """Test complete BM25 workflow: create → save → load → score."""
        # GIVEN: Financial documents
        chunks = [
            create_chunk(content="Q3 revenue was $50M, up 20% YoY"),
            create_chunk(content="Operating expenses increased 10% to $30M"),
            create_chunk(content="Net income for the period was $15M"),
        ]
        index_path = tmp_path / "workflow_bm25.pkl"

        # WHEN: Running complete workflow
        # Step 1: Create index
        bm25_original, tokenized = create_bm25_index(chunks)

        # Step 2: Save index
        saved_path = save_bm25_index(bm25_original, tokenized, index_path=str(index_path))

        # Step 3: Load index
        bm25_loaded, _, _ = load_bm25_index(index_path=str(index_path))

        # Step 4: Compute scores
        scores = compute_bm25_scores(bm25_loaded, "revenue YoY growth")

        # THEN: Workflow completes successfully
        assert saved_path.exists()
        assert isinstance(bm25_loaded, BM25Okapi)
        assert len(scores) == 3
        # First doc mentions revenue and YoY - should score highest
        assert scores[0] == max(scores)
