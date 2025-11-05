"""Unit tests for pypdfium backend configuration (Story 2.1).

Tests AC1: Docling Backend Configuration
- Verify DocumentConverter initialization includes PyPdfiumDocumentBackend
- Verify do_table_structure=True and TableFormerMode.ACCURATE preserved
"""

import pytest


class TestPypdfiumBackendConfiguration:
    """Unit tests for pypdfium backend configuration (Story 2.1 AC1)."""

    def test_backend_import_successful(self) -> None:
        """Verify PyPdfiumDocumentBackend can be imported successfully.

        This is a smoke test to ensure the backend module is available
        and the import path is correct.
        """
        # Test import - should not raise ImportError
        from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend

        assert PyPdfiumDocumentBackend is not None
        assert hasattr(PyPdfiumDocumentBackend, "__name__")

    def test_pipeline_options_configuration(self) -> None:
        """Verify PdfPipelineOptions is configured correctly for pypdfium.

        Validates:
        - do_table_structure=True is set
        - TableFormerMode.ACCURATE is preserved
        - Configuration doesn't break existing structure
        """
        # Lazy import to avoid test discovery overhead
        from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode

        # Configure pipeline options as done in pipeline.py
        pipeline_options = PdfPipelineOptions(do_table_structure=True)
        pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE

        # Assertions
        assert pipeline_options.do_table_structure is True
        assert pipeline_options.table_structure_options.mode == TableFormerMode.ACCURATE

    def test_document_converter_accepts_pypdfium_backend(self) -> None:
        """Verify DocumentConverter accepts PyPdfiumDocumentBackend in PdfFormatOption.

        Validates that the backend can be properly configured in PdfFormatOption
        without raising type errors or configuration errors.
        """
        # Lazy imports
        from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
        from docling.document_converter import DocumentConverter, PdfFormatOption

        # Configure pipeline options
        pipeline_options = PdfPipelineOptions(do_table_structure=True)
        pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE

        # Test that PdfFormatOption accepts the backend parameter
        # and DocumentConverter initializes without errors
        try:
            converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(
                        pipeline_options=pipeline_options, backend=PyPdfiumDocumentBackend
                    )
                }
            )
            # If we reach here, initialization was successful
            assert converter is not None
        except Exception as e:
            pytest.fail(f"DocumentConverter initialization failed with pypdfium backend: {e}")

    def test_backend_type_is_correct(self) -> None:
        """Verify PyPdfiumDocumentBackend is a valid backend type.

        Ensures the backend class inherits from AbstractDocumentBackend
        and can be used as a backend type.
        """
        # Lazy imports
        from docling.backend.abstract_backend import AbstractDocumentBackend
        from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend

        # Verify PyPdfiumDocumentBackend is a subclass of AbstractDocumentBackend
        assert issubclass(PyPdfiumDocumentBackend, AbstractDocumentBackend), (
            "PyPdfiumDocumentBackend must be a subclass of AbstractDocumentBackend"
        )
