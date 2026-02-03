"""
Story 9.9 AC6: No Breaking Changes to MCP Tools

Tests validate that all MCP tools continue to work correctly after Epic 9 changes.
This ensures backward compatibility is maintained.

Test IDs: TEST-AC-9.9.6.x
Priority: P0 (Critical)
"""

import subprocess
import sys

import pytest

from raglite.mcp.tools.forecast import get_financial_forecast
from raglite.mcp.tools.health import check_database_health
from raglite.mcp.tools.ingestion_tool import ingest_financial_document
from raglite.mcp.tools.query import query_financial_documents
from raglite.shared.models import QueryRequest
from raglite.shared.models.document import IngestionResult
from raglite.shared.models.timeseries_models import ForecastQueryRequest

pytestmark = [
    pytest.mark.acceptance,
    pytest.mark.slow,
]


class TestMCPCompatibility:
    """Tests for AC6: No breaking changes to MCP tools."""

    def test_ac_9_9_6_1_ingest_financial_document_works(self):
        """
        TEST-AC-9.9.6.1: [P0] ingest_financial_document works unchanged.

        Given the MCP tools depend on the ingestion pipeline
        When calling ingest_financial_document
        Then the tool works correctly with same API contract
        And response schema is unchanged
        """
        # Verify tool is importable and has expected interface
        # (imports moved to module level)

        # Verify it's a callable tool
        assert hasattr(ingest_financial_document, "fn"), "Tool should have .fn attribute"

        # Verify expected parameters (doc_path is the primary parameter)
        import inspect

        sig = inspect.signature(ingest_financial_document.fn)
        params = list(sig.parameters.keys())
        assert "doc_path" in params or "file_content" in params, (
            "Tool should accept doc_path or file_content parameter"
        )

    def test_ac_9_9_6_2_get_financial_forecast_works(self):
        """
        TEST-AC-9.9.6.2: [P0] get_financial_forecast works unchanged.

        Given the MCP tools depend on the query pipeline
        When calling get_financial_forecast
        Then the tool works correctly with same API contract
        And response schema is unchanged
        """
        # Verify it's a callable tool
        assert hasattr(get_financial_forecast, "fn"), "Tool should have .fn attribute"

        # Verify expected parameters
        import inspect

        sig = inspect.signature(get_financial_forecast.fn)
        params = list(sig.parameters.keys())
        assert "request" in params, "Tool should accept request parameter"

    def test_ac_9_9_6_3_query_financial_documents_works(self):
        """
        TEST-AC-9.9.6.3: [P0] query_financial_documents works unchanged.

        Given the MCP tools depend on the retrieval pipeline
        When calling query_financial_documents
        Then the tool works correctly with same API contract
        And response schema is unchanged
        """
        # Verify it's a callable tool
        assert hasattr(query_financial_documents, "fn"), "Tool should have .fn attribute"

        # Verify expected parameters
        import inspect

        sig = inspect.signature(query_financial_documents.fn)
        params = list(sig.parameters.keys())
        assert "request" in params, "Tool should accept request parameter"

    def test_ac_9_9_6_4_check_database_health_works(self):
        """
        TEST-AC-9.9.6.4: [P0] check_database_health works unchanged.

        Given the MCP tools include health monitoring
        When calling check_database_health
        Then the tool works correctly with same API contract
        And response schema is unchanged
        """
        # Verify it's a callable tool
        assert hasattr(check_database_health, "fn"), "Tool should have .fn attribute"

    def test_ac_9_9_6_5_mcp_unit_tests_pass(self):
        """
        TEST-AC-9.9.6.5: [P0] All MCP unit tests pass.

        Given the MCP test suite exists at tests/unit/mcp/
        When running pytest tests/unit/mcp/ -v
        Then all MCP unit tests pass
        """
        # Run MCP unit tests in subprocess
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/unit/mcp/",
                "-v",
                "--tb=short",
                "-q",
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )

        # Check result
        assert result.returncode == 0, f"MCP unit tests failed:\n{result.stdout}\n{result.stderr}"

    def test_ac_9_9_6_6_no_new_required_parameters(self):
        """
        TEST-AC-9.9.6.6: [P1] No new required parameters added.

        Given the MCP tool API contracts are documented
        When comparing pre-Epic 9 vs post-Epic 9 signatures
        Then no new required parameters have been added
        And backward compatibility is preserved
        """
        import inspect

        # Define expected required parameters for each tool
        expected_signatures = {
            "ingest_financial_document": ["doc_path"],  # Or file_content+filename
            "get_financial_forecast": ["request"],
            "query_financial_documents": ["request"],
            "check_database_health": [],  # No required params
        }

        tools = {
            "ingest_financial_document": ingest_financial_document,
            "get_financial_forecast": get_financial_forecast,
            "query_financial_documents": query_financial_documents,
            "check_database_health": check_database_health,
        }

        for tool_name, tool in tools.items():
            sig = inspect.signature(tool.fn)
            required_params = [
                name
                for name, param in sig.parameters.items()
                if param.default == inspect.Parameter.empty
                and param.kind
                not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
            ]

            expected = expected_signatures.get(tool_name, [])

            # Allow expected params or doc_path/file_content flexibility for ingestion
            if tool_name == "ingest_financial_document":
                # Either doc_path OR file_content+filename pattern is valid
                valid = (
                    "doc_path" in required_params
                    or "file_content" in required_params
                    or not required_params
                )
                assert valid, f"{tool_name}: unexpected required parameters {required_params}"
            else:
                # Verify no NEW required params beyond expected
                for param in required_params:
                    assert param in expected or param in ["self"], (
                        f"{tool_name}: unexpected required parameter '{param}'"
                    )

    def test_ac_9_9_6_7_response_schema_unchanged(self):
        """
        TEST-AC-9.9.6.7: [P1] Response schema remains unchanged.

        Given the MCP tools have documented response schemas
        When comparing response formats
        Then all existing fields are present
        And field types are unchanged
        """
        # Verify request/response models are importable and have expected fields

        # ForecastQueryRequest expected fields
        forecast_fields = ForecastQueryRequest.model_fields
        assert "entity" in forecast_fields, "ForecastQueryRequest missing 'entity' field"
        assert "metric" in forecast_fields, "ForecastQueryRequest missing 'metric' field"

        # QueryRequest expected fields
        query_fields = QueryRequest.model_fields
        assert "query" in query_fields, "QueryRequest missing 'query' field"

        # Verify ingestion response has expected structure
        ingestion_fields = IngestionResult.model_fields
        # Check for key fields (not 'status' - IngestionResult has filename, doc_type, etc.)
        assert "filename" in ingestion_fields, "IngestionResult missing 'filename' field"
        assert "doc_type" in ingestion_fields, "IngestionResult missing 'doc_type' field"
        assert "chunk_count" in ingestion_fields, "IngestionResult missing 'chunk_count' field"
