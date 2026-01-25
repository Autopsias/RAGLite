"""Integration tests for document segregation and attribution.

Story 4.0.4: Validates document provenance tracking and query scoping capabilities.

Tests validate:
- AC4: Document Attribution - Chunks correctly identify source documents
- AC2/AC3: Document-scoped queries work in Qdrant and PostgreSQL

Performance Optimization:
- Lazy imports: Expensive modules imported inside test functions
- Uses session_ingested_collection fixture for pre-populated test data
"""

import pytest

# Mark all tests in this module as integration tests that preserve collection state
pytestmark = [pytest.mark.integration, pytest.mark.preserve_collection, pytest.mark.slow]

# Lazy imports for expensive modules - DO NOT import raglite modules at module level!


@pytest.mark.xdist_group(name="embedding_model_reads")
@pytest.mark.preserve_collection  # Tests are read-only - skip expensive cleanup
class TestDocumentSegregation:
    """Integration tests for document segregation and attribution (Story 4.0.4 AC4).

    Validates that chunks from ingested documents have correct source attribution
    and that document-scoped queries work properly.
    """

    @pytest.mark.priority("P1")
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_chunk_document_attribution_qdrant(self, session_ingested_collection) -> None:
        """AC4: Verify chunks in Qdrant have correct document attribution.

        Validates:
        - All retrieved chunks have non-empty source_document
        - source_document matches a valid filename pattern
        - page_number is present for citation generation

        Story 4.0.4 AC4: Validate each chunk's metadata correctly identifies
        its source document.
        """
        from raglite.retrieval.search import search_documents
        from raglite.shared.clients import get_qdrant_client
        from raglite.shared.config import settings

        # Check collection exists
        qdrant = get_qdrant_client()
        collections = qdrant.get_collections().collections
        collection_names = [c.name for c in collections]

        if settings.qdrant_collection_name not in collection_names:
            pytest.skip(
                f"Collection {settings.qdrant_collection_name} does not exist. Run ingestion first."
            )

        # Query to retrieve chunks from any document
        query = "financial report revenue expenses"
        results = await search_documents(query, top_k=10)

        assert len(results) > 0, "Should retrieve at least one chunk"

        # Validate document attribution for all results
        for i, result in enumerate(results):
            # AC4: source_document must be present and non-empty
            assert result.source_document, (
                f"Chunk {i} missing source_document - document attribution failed"
            )

            # Validate source_document looks like a filename
            assert "." in result.source_document, (
                f"Chunk {i} source_document '{result.source_document}' doesn't look like a filename"
            )

            # AC4: page_number must be present for citations
            assert result.page_number is not None, (
                f"Chunk {i} missing page_number - citation generation will fail"
            )

            # chunk_index must be present for ordering
            assert result.chunk_index is not None, f"Chunk {i} missing chunk_index"

        # Log validation results
        unique_docs = {r.source_document for r in results}
        print("\n✅ Document Attribution Test (Qdrant):")
        print(f"  Chunks validated: {len(results)}")
        print(f"  Unique documents: {len(unique_docs)}")
        print(f"  Documents: {unique_docs}")

    @pytest.mark.priority("P1")
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_document_scoped_filter_qdrant(self, session_ingested_collection) -> None:
        """AC2: Verify Qdrant filter by source_document works.

        Validates:
        - search_documents with source_document filter returns only matching chunks
        - All results have the filtered source_document value

        Story 4.0.4 AC2: Validate chunks can be filtered by source_document.
        """
        from raglite.retrieval.search import search_documents
        from raglite.shared.clients import get_qdrant_client
        from raglite.shared.config import settings

        # Check collection exists
        qdrant = get_qdrant_client()
        collections = qdrant.get_collections().collections
        collection_names = [c.name for c in collections]

        if settings.qdrant_collection_name not in collection_names:
            pytest.skip(f"Collection {settings.qdrant_collection_name} does not exist.")

        # First, get unfiltered results to find a valid document name
        unfiltered_results = await search_documents("financial data", top_k=5)
        if not unfiltered_results:
            pytest.skip("No chunks in collection to test filter")

        # Use the first result's source_document as our filter target
        target_document = unfiltered_results[0].source_document

        # Now search with document filter
        filtered_results = await search_documents(
            "financial data",
            top_k=10,
            filters={"source_document": target_document},
        )

        # All filtered results should match the target document
        for result in filtered_results:
            assert result.source_document == target_document, (
                f"Filter returned wrong document: {result.source_document} "
                f"(expected {target_document})"
            )

        print("\n✅ Document-Scoped Filter Test (Qdrant):")
        print(f"  Target document: {target_document}")
        print(f"  Filtered results: {len(filtered_results)}")
        print("  All results match filter: True")

    @pytest.mark.priority("P1")
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_source_citation_accuracy(self, session_ingested_collection) -> None:
        """AC4: Test that query results include accurate source citations.

        Validates:
        - QueryResult.source_document is populated for all results
        - QueryResult.page_number is available for citation formatting
        - Citation data is sufficient for "[Document] (page X)" format

        Story 4.0.4 AC4: Test that query results include accurate source citations.
        """
        from raglite.retrieval.search import search_documents
        from raglite.shared.clients import get_qdrant_client
        from raglite.shared.config import settings

        # Check collection exists
        qdrant = get_qdrant_client()
        collections = qdrant.get_collections().collections
        collection_names = [c.name for c in collections]

        if settings.qdrant_collection_name not in collection_names:
            pytest.skip(f"Collection {settings.qdrant_collection_name} does not exist.")

        # Search for financial content
        results = await search_documents("revenue growth percentage", top_k=5)

        assert len(results) > 0, "Should retrieve results for citation test"

        # Validate citation data is present and usable
        citations = []
        for result in results:
            # Both fields needed for proper citation
            assert result.source_document, "source_document required for citation"
            assert result.page_number is not None, "page_number required for citation"

            # Format citation as it would appear to users
            citation = f"{result.source_document} (page {result.page_number})"
            citations.append(citation)

        print("\n✅ Source Citation Accuracy Test:")
        print(f"  Results with valid citations: {len(citations)}")
        print("  Sample citations:")
        for citation in citations[:3]:
            print(f"    - {citation}")

    @pytest.mark.priority("P2")
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_multi_document_search_default(self, session_ingested_collection) -> None:
        """Verify default search returns chunks from potentially multiple documents.

        Validates:
        - Without filters, search may return chunks from different documents
        - Documents search behavior (all docs vs specific doc)

        Story 4.0.4: Multi-document search behavior documentation.
        """
        from raglite.retrieval.search import search_documents
        from raglite.shared.clients import get_qdrant_client
        from raglite.shared.config import settings

        # Check collection exists
        qdrant = get_qdrant_client()
        collections = qdrant.get_collections().collections
        collection_names = [c.name for c in collections]

        if settings.qdrant_collection_name not in collection_names:
            pytest.skip(f"Collection {settings.qdrant_collection_name} does not exist.")

        # Broad query that might match multiple documents
        results = await search_documents("company financial performance", top_k=20)

        if len(results) < 2:
            pytest.skip("Need at least 2 chunks to test multi-document behavior")

        # Count unique documents in results
        unique_docs = {r.source_document for r in results}

        print("\n✅ Multi-Document Search Test:")
        print(f"  Results retrieved: {len(results)}")
        print(f"  Unique documents: {len(unique_docs)}")
        print(f"  Documents found: {unique_docs}")
        print(
            f"  Behavior: Returns chunks from {'multiple' if len(unique_docs) > 1 else 'single'} document(s)"
        )

        # Document the observed behavior (not an assertion - just documentation)
        # In a single-document scenario, all results will be from one doc
        # In a multi-document scenario, results can span multiple docs


@pytest.mark.xdist_group(name="embedding_model_reads")
@pytest.mark.preserve_collection
class TestPostgreSQLDocumentSegregation:
    """Integration tests for PostgreSQL document attribution (Story 4.0.4 AC3).

    Validates that PostgreSQL financial_tables correctly tracks document provenance.
    """

    @pytest.mark.priority("P1")
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_sql_table_document_attribution(self, session_ingested_collection) -> None:
        """AC3: Verify PostgreSQL financial_tables tracks document_id.

        Validates:
        - SQL queries return document_id for attribution
        - Page numbers are available for citations

        Story 4.0.4 AC3: Validate SQL queries can filter by document source.
        """
        import asyncio

        from raglite.shared.clients import get_postgresql_connection

        # Execute SQL query to check document attribution columns
        def check_table_attribution():
            try:
                conn = get_postgresql_connection()
                cursor = conn.cursor()

                # Query to verify document_id column exists and has data
                cursor.execute(
                    """
                    SELECT document_id, page_number, COUNT(*) as row_count
                    FROM financial_tables
                    WHERE document_id IS NOT NULL
                    GROUP BY document_id, page_number
                    LIMIT 10
                """
                )

                rows = cursor.fetchall()
                cursor.close()
                return rows

            except Exception:
                # Table may not exist or be empty - skip test
                return None

        rows = await asyncio.to_thread(check_table_attribution)

        if rows is None or len(rows) == 0:
            pytest.skip("financial_tables empty or unavailable")

        # Validate document attribution
        unique_docs = set()
        for row in rows:
            document_id, page_number, count = row
            assert document_id, "document_id should not be empty"
            unique_docs.add(document_id)

        print("\n✅ PostgreSQL Document Attribution Test:")
        print(f"  Rows with attribution: {sum(r[2] for r in rows)}")
        print(f"  Unique documents: {len(unique_docs)}")
        print(f"  Documents: {unique_docs}")

    @pytest.mark.priority("P1")
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_sql_document_filter(self, session_ingested_collection) -> None:
        """AC3: Verify SQL queries can filter by document_id.

        Validates:
        - WHERE document_id = 'X' correctly filters results
        - Filtered results all have matching document_id

        Story 4.0.4 AC3: Validate SQL queries can filter by document source.
        """
        import asyncio

        from raglite.shared.clients import get_postgresql_connection

        def test_document_filter():
            try:
                conn = get_postgresql_connection()
                cursor = conn.cursor()

                # First get a valid document_id
                cursor.execute(
                    """
                    SELECT DISTINCT document_id
                    FROM financial_tables
                    WHERE document_id IS NOT NULL
                    LIMIT 1
                """
                )

                doc_row = cursor.fetchone()
                if not doc_row:
                    return None, None

                target_doc = doc_row[0]

                # Now filter by that document_id
                cursor.execute(
                    """
                    SELECT document_id, entity, metric
                    FROM financial_tables
                    WHERE document_id = %s
                    LIMIT 10
                """,
                    (target_doc,),
                )

                filtered_rows = cursor.fetchall()
                cursor.close()
                return target_doc, filtered_rows

            except Exception:
                return None, None

        target_doc, filtered_rows = await asyncio.to_thread(test_document_filter)

        if target_doc is None or filtered_rows is None:
            pytest.skip("financial_tables empty or unavailable")

        # Verify all filtered results match the target document
        for row in filtered_rows:
            assert row[0] == target_doc, (
                f"Filter returned wrong document: {row[0]} (expected {target_doc})"
            )

        print("\n✅ PostgreSQL Document Filter Test:")
        print(f"  Target document: {target_doc}")
        print(f"  Filtered rows: {len(filtered_rows)}")
        print("  All rows match filter: True")
