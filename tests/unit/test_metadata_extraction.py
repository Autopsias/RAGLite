"""Unit tests for Story 2.4 metadata extraction functionality.

Tests AC1 (Metadata Extraction), AC2 (Schema), AC4 (Caching).
"""

import json
from unittest.mock import AsyncMock, patch

import pytest
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice
from openai.types.completion_usage import CompletionUsage

from raglite.ingestion.pipeline import _metadata_cache, extract_document_metadata
from raglite.shared.models import ExtractedMetadata


@pytest.fixture(autouse=True)
def clear_metadata_cache():
    """Clear metadata cache before each test."""
    _metadata_cache.clear()
    yield
    _metadata_cache.clear()


@pytest.fixture
def mock_openai_response():
    """Create a mock OpenAI API response.

    AI8: Refactored to use Pydantic for schema validation and consistency.
    """

    def _create_response(
        fiscal_period: str | None = "Q3 2024",
        company_name: str | None = "ACME Corporation",
        department_name: str | None = "Finance",
    ):
        # AI8: Validate against ExtractedMetadata schema first
        metadata = ExtractedMetadata(
            fiscal_period=fiscal_period,
            company_name=company_name,
            department_name=department_name,
        )
        # Convert to dict with proper JSON serialization
        response_dict = metadata.model_dump(mode="json", exclude_none=False)

        return ChatCompletion(
            id="chatcmpl-test123",
            object="chat.completion",
            created=1234567890,
            model="gpt-5-nano",
            choices=[
                Choice(
                    index=0,
                    message=ChatCompletionMessage(
                        role="assistant", content=json.dumps(response_dict)
                    ),
                    finish_reason="stop",
                )
            ],
            usage=CompletionUsage(prompt_tokens=2100, completion_tokens=50, total_tokens=2150),
        )

    return _create_response


class TestExtractDocumentMetadata:
    """Test suite for extract_document_metadata function (AC1)."""

    @pytest.mark.asyncio
    async def test_metadata_extraction_success(self, mock_openai_response):
        """Test successful metadata extraction with all fields populated."""
        test_text = """
        Financial Report Q3 2024
        ACME Corporation
        Finance Department

        This report covers the third quarter of fiscal year 2024...
        """

        with patch("raglite.ingestion.pipeline.settings") as mock_settings:
            mock_settings.openai_api_key = "test-key-123"
            mock_settings.openai_metadata_model = "gpt-5-nano"  # AI7: Mock new config field
            mock_settings.gpt5_nano_input_price_per_mtok = 0.10  # AI4: Mock pricing
            mock_settings.gpt5_nano_output_price_per_mtok = 0.40  # AI4: Mock pricing

            with patch("openai.AsyncOpenAI") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.chat.completions.create = AsyncMock(return_value=mock_openai_response())
                mock_client_class.return_value = mock_client

                result = await extract_document_metadata(test_text, "test_report.pdf")

                assert isinstance(result, ExtractedMetadata)
                assert result.fiscal_period == "Q3 2024"
                assert result.company_name == "ACME Corporation"
                assert result.department_name == "Finance"

                # Verify API was called with correct parameters
                mock_client.chat.completions.create.assert_called_once()
                call_kwargs = mock_client.chat.completions.create.call_args.kwargs
                assert call_kwargs["model"] == "gpt-5-nano"
                assert call_kwargs["temperature"] == 0.0
                assert call_kwargs["response_format"] == {"type": "json_object"}

    @pytest.mark.asyncio
    async def test_metadata_extraction_partial_fields(self, mock_openai_response):
        """Test extraction with some fields missing (null values)."""
        with patch("raglite.ingestion.pipeline.settings") as mock_settings:
            mock_settings.openai_api_key = "test-key-123"
            mock_settings.openai_metadata_model = "gpt-5-nano"  # AI7: Mock new config field
            mock_settings.gpt5_nano_input_price_per_mtok = 0.10  # AI4: Mock pricing
            mock_settings.gpt5_nano_output_price_per_mtok = 0.40  # AI4: Mock pricing

            with patch("openai.AsyncOpenAI") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.chat.completions.create = AsyncMock(
                    return_value=mock_openai_response(
                        fiscal_period="FY 2023",
                        company_name="TechCorp",
                        department_name=None,  # Missing department
                    )
                )
                mock_client_class.return_value = mock_client

                result = await extract_document_metadata(
                    "Some text without department info", "test.pdf"
                )

                assert result.fiscal_period == "FY 2023"
                assert result.company_name == "TechCorp"
                assert result.department_name is None  # Optional field

    @pytest.mark.asyncio
    async def test_metadata_extraction_no_api_key(self):
        """Test that extraction fails gracefully when API key not configured."""
        with patch("raglite.ingestion.pipeline.settings") as mock_settings:
            mock_settings.openai_api_key = None

            with pytest.raises(RuntimeError, match="OpenAI API key not configured"):
                await extract_document_metadata("Test text", "test.pdf")

    @pytest.mark.asyncio
    async def test_metadata_extraction_api_failure(self):
        """Test handling of OpenAI API failures."""
        with patch("raglite.ingestion.pipeline.settings") as mock_settings:
            mock_settings.openai_api_key = "test-key-123"
            mock_settings.openai_metadata_model = "gpt-5-nano"  # AI7: Mock new config field
            mock_settings.gpt5_nano_input_price_per_mtok = 0.10  # AI4: Mock pricing
            mock_settings.gpt5_nano_output_price_per_mtok = 0.40  # AI4: Mock pricing

            with patch("openai.AsyncOpenAI") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.chat.completions.create = AsyncMock(
                    side_effect=Exception("API connection failed")
                )
                mock_client_class.return_value = mock_client

                with pytest.raises(RuntimeError, match="Metadata extraction failed"):
                    await extract_document_metadata("Test text", "test.pdf")

    @pytest.mark.asyncio
    async def test_metadata_caching_enabled(self, mock_openai_response):
        """Test AC4: Metadata caching works correctly (cache hit)."""
        with patch("raglite.ingestion.pipeline.settings") as mock_settings:
            mock_settings.openai_api_key = "test-key-123"
            mock_settings.openai_metadata_model = "gpt-5-nano"  # AI7: Mock new config field
            mock_settings.gpt5_nano_input_price_per_mtok = 0.10  # AI4: Mock pricing
            mock_settings.gpt5_nano_output_price_per_mtok = 0.40  # AI4: Mock pricing

            with patch("openai.AsyncOpenAI") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.chat.completions.create = AsyncMock(return_value=mock_openai_response())
                mock_client_class.return_value = mock_client

                # First call - cache miss
                result1 = await extract_document_metadata(
                    "Test text", "test_report.pdf", use_cache=True
                )
                assert result1.fiscal_period == "Q3 2024"

                # Second call - cache hit (should NOT call API again)
                result2 = await extract_document_metadata(
                    "Different text same file", "test_report.pdf", use_cache=True
                )

                # Should return cached result
                assert result2.fiscal_period == "Q3 2024"
                assert result1 is result2  # Same object reference

                # API should only be called once (cache hit on second call)
                assert mock_client.chat.completions.create.call_count == 1

    @pytest.mark.asyncio
    async def test_metadata_caching_disabled(self, mock_openai_response):
        """Test AC4: Caching can be disabled when needed."""
        with patch("raglite.ingestion.pipeline.settings") as mock_settings:
            mock_settings.openai_api_key = "test-key-123"
            mock_settings.openai_metadata_model = "gpt-5-nano"  # AI7: Mock new config field
            mock_settings.gpt5_nano_input_price_per_mtok = 0.10  # AI4: Mock pricing
            mock_settings.gpt5_nano_output_price_per_mtok = 0.40  # AI4: Mock pricing

            with patch("openai.AsyncOpenAI") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.chat.completions.create = AsyncMock(return_value=mock_openai_response())
                mock_client_class.return_value = mock_client

                # First call with caching disabled
                await extract_document_metadata("Test text", "test_report.pdf", use_cache=False)

                # Second call with caching disabled
                await extract_document_metadata("Test text", "test_report.pdf", use_cache=False)

                # API should be called twice (no caching)
                assert mock_client.chat.completions.create.call_count == 2

    @pytest.mark.asyncio
    async def test_text_truncation(self, mock_openai_response):
        """Test that long documents are truncated to 2000 tokens."""
        # Create a very long text (>2000 tokens)
        long_text = "Sample text. " * 500  # Approximately 1000 tokens

        with patch("raglite.ingestion.pipeline.settings") as mock_settings:
            mock_settings.openai_api_key = "test-key-123"
            mock_settings.openai_metadata_model = "gpt-5-nano"  # AI7: Mock new config field
            mock_settings.gpt5_nano_input_price_per_mtok = 0.10  # AI4: Mock pricing
            mock_settings.gpt5_nano_output_price_per_mtok = 0.40  # AI4: Mock pricing

            with patch("openai.AsyncOpenAI") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.chat.completions.create = AsyncMock(return_value=mock_openai_response())
                mock_client_class.return_value = mock_client

                # Mock encoding to simulate truncation
                with patch("raglite.ingestion.pipeline.encoding") as mock_encoding:
                    mock_encoding.encode.return_value = list(range(3000))  # 3000 tokens
                    mock_encoding.decode.return_value = "Truncated text..."

                    await extract_document_metadata(long_text, "large_doc.pdf")

                    # Verify encoding.decode was called with first 2000 tokens
                    mock_encoding.decode.assert_called_once()
                    decoded_tokens = mock_encoding.decode.call_args[0][0]
                    assert len(decoded_tokens) == 2000


class TestExtractedMetadataModel:
    """Test AC2: ExtractedMetadata Pydantic model validation."""

    def test_extracted_metadata_all_fields(self):
        """Test model with all fields populated."""
        metadata = ExtractedMetadata(
            fiscal_period="Q3 2024", company_name="ACME Corp", department_name="Finance"
        )

        assert metadata.fiscal_period == "Q3 2024"
        assert metadata.company_name == "ACME Corp"
        assert metadata.department_name == "Finance"

    def test_extracted_metadata_optional_fields(self):
        """Test model with optional fields as None."""
        metadata = ExtractedMetadata(fiscal_period=None, company_name=None, department_name=None)

        assert metadata.fiscal_period is None
        assert metadata.company_name is None
        assert metadata.department_name is None

    def test_extracted_metadata_defaults(self):
        """Test model default values (all None)."""
        metadata = ExtractedMetadata()

        assert metadata.fiscal_period is None
        assert metadata.company_name is None
        assert metadata.department_name is None
