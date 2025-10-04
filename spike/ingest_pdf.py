"""PDF ingestion using Docling for Week 0 Integration Spike."""

import json
import time
from pathlib import Path
from typing import Any

from config import TEST_PDF_PATH
from docling.document_converter import DocumentConverter


def ingest_pdf(pdf_path: str = TEST_PDF_PATH) -> dict[str, Any]:
    """
    Ingest a financial PDF using Docling and extract text and tables.

    Args:
        pdf_path: Path to the PDF file to ingest

    Returns:
        Dictionary containing extracted content, metadata, and performance metrics

    Raises:
        FileNotFoundError: If PDF file doesn't exist
        Exception: If ingestion fails
    """
    pdf_file = Path(pdf_path)

    if not pdf_file.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    print(f"Starting PDF ingestion: {pdf_file.name}")
    print(f"File size: {pdf_file.stat().st_size / 1024 / 1024:.2f} MB")

    # Start timing
    start_time = time.time()

    try:
        # Initialize Docling converter
        converter = DocumentConverter()

        # Convert PDF
        print("Converting PDF with Docling...")
        result = converter.convert(str(pdf_file))

        # Extract document structure
        doc = result.document

        # Extract text content (full document)
        text_content = doc.export_to_markdown()

        # Extract page-level content with page numbers
        # WORKAROUND: Docling's page attribution is complex. For this spike,
        # we'll estimate page boundaries by dividing the full text proportionally.
        # This provides reasonable page context for the Week 0 validation.

        page_count = len(doc.pages) if hasattr(doc, "pages") else 160
        total_chars = len(text_content)
        avg_chars_per_page = total_chars // page_count if page_count > 0 else total_chars

        pages_with_content = []

        # Split text into estimated page chunks
        for page_num in range(1, page_count + 1):
            start_idx = (page_num - 1) * avg_chars_per_page
            end_idx = page_num * avg_chars_per_page if page_num < page_count else total_chars

            page_text = text_content[start_idx:end_idx]

            pages_with_content.append(
                {
                    "page_number": page_num,
                    "text": page_text,
                    "char_count": len(page_text),
                    "note": "Estimated page boundary (spike workaround)",
                }
            )

        # Extract tables if any
        tables = []
        for table in doc.tables:
            tables.append(
                {
                    "page": getattr(table, "page_no", None),
                    "rows": getattr(table, "num_rows", 0),
                    "cols": getattr(table, "num_cols", 0),
                    "content": str(table),
                }
            )

        # Calculate ingestion time
        ingestion_time = time.time() - start_time

        # Prepare result
        result_data = {
            "status": "success",
            "file_name": pdf_file.name,
            "file_size_mb": pdf_file.stat().st_size / 1024 / 1024,
            "page_count": page_count,
            "text_length": len(text_content),
            "table_count": len(tables),
            "tables": tables,
            "text_content": text_content,
            "pages": pages_with_content,  # NEW: Per-page content with page numbers
            "ingestion_time_seconds": round(ingestion_time, 2),
            "extracted_metadata": {
                "title": getattr(doc, "title", None),
                "author": getattr(doc, "author", None),
            },
        }

        # Print summary
        print(f"\n{'='*60}")
        print("INGESTION SUMMARY")
        print(f"{'='*60}")
        print("Status: SUCCESS")
        print(f"Pages: {page_count}")
        print(f"Text length: {len(text_content):,} characters")
        print(f"Tables found: {len(tables)}")
        print(f"Ingestion time: {ingestion_time:.2f} seconds")
        print(f"{'='*60}\n")

        # Display sample text
        print("SAMPLE EXTRACTED TEXT (first 500 chars):")
        print(f"{text_content[:500]}...\n")

        # Display table info
        if tables:
            print(f"TABLES FOUND: {len(tables)}")
            for i, table in enumerate(tables[:3]):  # Show first 3 tables
                print(
                    f"  Table {i+1}: {table['rows']} rows x {table['cols']} cols (Page {table['page']})"
                )

        return result_data

    except Exception as e:
        ingestion_time = time.time() - start_time
        print(f"\nERROR during ingestion: {str(e)}")
        print(f"Ingestion time before failure: {ingestion_time:.2f} seconds")

        return {
            "status": "failed",
            "file_name": pdf_file.name,
            "error": str(e),
            "ingestion_time_seconds": round(ingestion_time, 2),
        }


def save_ingestion_result(result: dict[str, Any], output_path: str = "spike_ingestion_result.json"):
    """Save ingestion result to JSON file for later analysis."""
    output_file = Path(output_path)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"Ingestion result saved to: {output_file}")


if __name__ == "__main__":
    # Run ingestion
    result = ingest_pdf()

    # Save result
    save_ingestion_result(result)

    # Exit with appropriate code
    exit(0 if result["status"] == "success" else 1)
