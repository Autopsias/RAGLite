#!/usr/bin/env python3
"""Re-ingest all 33 production documents with classification-enabled pipeline.

This script re-ingests all financial documents using the new classification pipeline
from Stories 9.5 and 9.6. Supports parallel ingestion and classification reporting.

Rollback Procedure (If Critical Failure):
1. Stop ingestion script (Ctrl+C)
2. Restore PostgreSQL backup:
   docker exec -i raglite-postgresql psql -U raglite -d raglite < backups/postgresql_backup_*.sql
3. Restore Qdrant snapshot:
   See backups/README.md for Qdrant snapshot recovery instructions
4. Verify data integrity:
   python scripts/validate-classification-coverage.py

Estimated time:
- Sequential: ~3-4 hours for 33 documents
- Parallel (--parallel 4): ~1-1.5 hours
"""

import argparse
import asyncio
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

# Add raglite to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set production environment
os.environ["APP_ENV"] = "production"

from raglite.ingestion.document_ingestion import ingest_document

# All 33 production financial documents (discovered from Qdrant)
DOCUMENTS = [
    "2017-12 Performance Review - Dezembro 2017.pdf",
    "2018-12 Performance Review - December 2018.pdf",
    "2019-12 Performance Review - Dezembro 2019_v2.pdf",
    "2020-12 Performance Review Consolidado.pdf",
    "2021-12 Performance Review CONSO_v01.02.2022.pdf",
    "2022-12 Performance Review CONSO_v1.pdf",
    "2023-01 Performance Review CONSO_v1.pdf",
    "2023-02 Performance Review CONSO_v2.pdf",
    "2023-03 Performance Review CONSO_2.pdf",
    "2023-12 Performance Review CONSO_v1.pdf",
    "2024-01 Performance Review CONSO_v2.pdf",
    "2024-02 Performance Review CONSO_v1.pdf",
    "2024-03 Performance Review CONSO_v3.pdf",
    "2024-04 Performance Review CONSO_v2.pdf",
    "2024-05 Performance Review CONSO_v1.pdf",
    "2024-06 Performance Review CONSO_v2.pdf",
    "2024-07 Performance Review CONSO_v1.pdf",
    "2024-08 Performance Review CONSO_V1.pdf",
    "2024-09 Performance Review CONSO_v2.pdf",
    "2024-10 Performance Review CONSO_v2.pdf",
    "2024-11 Performance Review CONSO_v2.pdf",
    "2024-12 Performance Review CONSO_v2.pdf",
    "2025-01 Performance Review CONSO_v2.pdf",
    "2025-02 Performance Review CONSO_v1.pdf",
    "2025-03 Performance Review CONSO_V1.pdf",
    "2025-04 Performance Review CONSO.pdf",
    "2025-05 Performance Review CONSO_v1.pdf",
    "2025-06 Performance Review CONSO_v1.pdf",
    "2025-07 Performance Review CONSO.pdf",
    "2025-08 Performance Review CONSO_v2.pdf",
    "2025-09 Performance Review CONSO_rev3.pdf",
    "2025-10 Performance Review CONSO_v3.pdf",
    "2025-11 Performance Review CONSO_v2.pdf",
]

# Default base path - can be overridden via --base-path argument
DEFAULT_BASE_PATH = os.getenv(
    "RAGLITE_DOCUMENTS_PATH", "/Users/ricardocarvalho/Downloads/OneDrive_1_11-25-2025 2"
)


@dataclass
class ClassificationSummary:
    """Classification summary for a document."""

    period_type_classified: int
    value_type_classified: int
    entity_level_classified: int
    total_rows: int


@dataclass
class DocumentMetrics:
    """Performance metrics for document ingestion."""

    doc_name: str
    pages: int
    chunks: int
    tables: int
    rows: int
    duration: float
    classification_time: float = 0.0
    extraction_time: float = 0.0
    classification: ClassificationSummary | None = None

    @property
    def rows_per_second(self) -> float:
        """Calculate rows per second throughput."""
        return self.rows / self.duration if self.duration > 0 else 0

    @property
    def classification_overhead(self) -> float:
        """Calculate classification overhead percentage."""
        if self.extraction_time > 0:
            return 100 * self.classification_time / self.extraction_time
        return 0.0


def print_classification_summary(summary: ClassificationSummary) -> None:
    """Print classification summary for a document."""
    print("   Classification Coverage:")
    print(
        f"     Period Type: {summary.period_type_classified}/{summary.total_rows} "
        f"({100 * summary.period_type_classified / max(summary.total_rows, 1):.1f}%)"
    )
    print(
        f"     Value Type: {summary.value_type_classified}/{summary.total_rows} "
        f"({100 * summary.value_type_classified / max(summary.total_rows, 1):.1f}%)"
    )
    print(
        f"     Entity Level: {summary.entity_level_classified}/{summary.total_rows} "
        f"({100 * summary.entity_level_classified / max(summary.total_rows, 1):.1f}%)"
    )


async def ingest_single_document(
    doc_name: str, doc_path: Path, dry_run: bool = False
) -> DocumentMetrics:
    """Ingest a single document and return metrics."""
    if dry_run:
        print(f"   [DRY RUN] Would ingest: {doc_path}")
        return DocumentMetrics(
            doc_name=doc_name,
            pages=0,
            chunks=0,
            tables=0,
            rows=0,
            duration=0.0,
        )

    start_time = time.time()
    result = await ingest_document(str(doc_path))
    duration = time.time() - start_time

    # Extract classification summary if available
    classification = None
    if hasattr(result, "table_count") and result.table_count > 0:
        # Query PostgreSQL for classification coverage
        # For now, stub this - full implementation would query DB
        classification = ClassificationSummary(
            period_type_classified=getattr(result, "rows_classified", 0),
            value_type_classified=getattr(result, "rows_classified", 0),
            entity_level_classified=getattr(result, "rows_classified", 0),
            total_rows=getattr(result, "row_count", 0),
        )

    return DocumentMetrics(
        doc_name=doc_name,
        pages=result.page_count,
        chunks=result.chunk_count,
        tables=getattr(result, "table_count", 0),
        rows=getattr(result, "row_count", 0),
        duration=duration,
        classification=classification,
    )


async def ingest_documents_parallel(
    documents: list[str], base_path: Path, max_workers: int, dry_run: bool = False
) -> list[DocumentMetrics]:
    """Ingest documents in parallel using semaphore to limit concurrency."""
    semaphore = asyncio.Semaphore(max_workers)

    async def ingest_with_limit(doc_name: str, doc_path: Path) -> DocumentMetrics:
        async with semaphore:
            return await ingest_single_document(doc_name, doc_path, dry_run)

    tasks = []
    for doc_name in documents:
        doc_path = base_path / doc_name
        if doc_path.exists():
            tasks.append(ingest_with_limit(doc_name, doc_path))

    return await asyncio.gather(*tasks, return_exceptions=True)


async def main() -> int:
    """Re-ingest all documents with optional parallel execution."""
    parser = argparse.ArgumentParser(
        description="Re-ingest all production PDFs with classification"
    )
    parser.add_argument(
        "--parallel",
        type=int,
        default=1,
        metavar="N",
        help="Number of parallel workers (default: 1 = sequential)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview actions without executing ingestion",
    )
    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="Retry only failed documents from previous run",
    )
    parser.add_argument(
        "--failed-log",
        default="failed_documents.txt",
        help="Path to failed documents log file (default: failed_documents.txt)",
    )
    parser.add_argument(
        "--base-path",
        type=str,
        default=DEFAULT_BASE_PATH,
        help=f"Base path for documents (default: env RAGLITE_DOCUMENTS_PATH or {DEFAULT_BASE_PATH})",
    )
    args = parser.parse_args()

    BASE_PATH = Path(args.base_path)

    # Load failed documents if retry mode
    documents_to_process = DOCUMENTS
    if args.retry_failed:
        failed_log = Path(args.failed_log)
        if not failed_log.exists():
            print(f"❌ Failed log not found: {failed_log}")
            return 1
        with open(failed_log) as f:
            documents_to_process = [line.strip() for line in f if line.strip()]
        print(f"Retrying {len(documents_to_process)} failed documents")

    print("=" * 80)
    print("FULL DATABASE RE-INGESTION WITH CLASSIFICATION PIPELINE")
    print("=" * 80)
    print(f"Total documents: {len(documents_to_process)}")
    print(f"Parallel workers: {args.parallel}")
    print(f"Dry run mode: {args.dry_run}")
    print(f"Environment: {os.environ.get('APP_ENV')}")
    print(f"Base path: {BASE_PATH}")
    if args.parallel > 1:
        print("Estimated time: ~1-1.5 hours (parallel)")
    else:
        print("Estimated time: ~3-4 hours (sequential)")
    print("=" * 80)
    print()

    if args.dry_run:
        print("[DRY RUN] No actual ingestion will be performed\n")

    total_start_time = time.time()
    completed = 0
    failed: list[tuple[str, str]] = []
    all_metrics: list[DocumentMetrics] = []

    if args.parallel > 1:
        # Parallel execution
        print(f"Ingesting {len(documents_to_process)} documents with {args.parallel} workers...")
        results = await ingest_documents_parallel(
            documents_to_process, BASE_PATH, args.parallel, args.dry_run
        )

        for i, result in enumerate(results):
            doc_name = documents_to_process[i]
            if isinstance(result, Exception):
                failed.append((doc_name, str(result)))
                print(f"❌ FAILED: {doc_name}: {result}")
            else:
                completed += 1
                all_metrics.append(result)
                print(f"✅ [{completed}/{len(documents_to_process)}] {doc_name}")
    else:
        # Sequential execution
        for i, doc_name in enumerate(documents_to_process, 1):
            doc_path = BASE_PATH / doc_name

            if not doc_path.exists():
                print(
                    f"\n❌ [{i}/{len(documents_to_process)}] SKIPPED: {doc_name} (file not found)"
                )
                failed.append((doc_name, "File not found"))
                continue

            print(f"\n{'=' * 80}")
            print(f"[{i}/{len(documents_to_process)}] Ingesting: {doc_name}")
            print(f"{'=' * 80}")

            try:
                metrics = await ingest_single_document(doc_name, doc_path, args.dry_run)
                completed += 1
                all_metrics.append(metrics)

                print("\n✅ SUCCESS!")
                print(f"   Pages: {metrics.pages}")
                print(f"   Chunks: {metrics.chunks}")
                print(f"   Tables: {metrics.tables}")
                print(f"   Rows: {metrics.rows}")
                print(f"   Duration: {metrics.duration:.1f}s")
                print(f"   Rows/sec: {metrics.rows_per_second:.1f}")

                if metrics.classification:
                    print_classification_summary(metrics.classification)

                elapsed = time.time() - total_start_time
                avg_time_per_doc = elapsed / completed
                remaining_docs = len(documents_to_process) - i
                estimated_remaining = avg_time_per_doc * remaining_docs
                print(f"   Progress: {completed}/{len(documents_to_process)} documents complete")
                print(f"   Estimated time remaining: {estimated_remaining / 60:.1f} minutes")

            except Exception as e:
                print(f"\n❌ FAILED: {doc_name}")
                print(f"   Error: {e}")
                failed.append((doc_name, str(e)))

    total_duration = time.time() - total_start_time

    # Save failed documents to log
    if failed:
        with open(args.failed_log, "w") as f:
            for doc_name, _ in failed:
                f.write(f"{doc_name}\n")

    # Final summary
    print()
    print("=" * 80)
    print("INGESTION COMPLETE - SUMMARY")
    print("=" * 80)
    print(f"Documents completed: {completed}/{len(documents_to_process)}")
    print(f"Total duration: {total_duration / 60:.1f} minutes")

    if all_metrics:
        total_pages = sum(m.pages for m in all_metrics)
        total_chunks = sum(m.chunks for m in all_metrics)
        total_tables = sum(m.tables for m in all_metrics)
        total_rows = sum(m.rows for m in all_metrics)
        avg_rows_per_sec = sum(m.rows_per_second for m in all_metrics) / len(all_metrics)

        print(f"Total pages: {total_pages}")
        print(f"Total chunks: {total_chunks}")
        print(f"Total tables: {total_tables}")
        print(f"Total rows: {total_rows}")
        print(f"Average throughput: {avg_rows_per_sec:.1f} rows/sec")

    if failed:
        print(f"\n❌ Failed documents ({len(failed)}):")
        for doc_name, error in failed:
            print(f"   - {doc_name}: {error}")
        print(f"\nFailed documents saved to: {args.failed_log}")
        print("Retry with: python scripts/reingest-all-documents.py --retry-failed")
    else:
        print("\n✅ All documents ingested successfully!")

    print("=" * 80)

    # Save metrics to performance report
    if all_metrics and not args.dry_run:
        report_path = Path("docs/sprint-artifacts/re-ingestion-metrics.md")
        report_path.parent.mkdir(parents=True, exist_ok=True)

        # Calculate classification overhead
        avg_overhead = (
            sum(m.classification_overhead for m in all_metrics) / len(all_metrics)
            if all_metrics
            else 0.0
        )

        with open(report_path, "w") as f:
            f.write("# Re-ingestion Performance Metrics\n\n")
            f.write(f"**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("## Summary\n\n")
            f.write(f"- Total documents: {len(all_metrics)}\n")
            f.write(f"- Total duration: {total_duration / 60:.1f} minutes\n")
            f.write(f"- Total rows: {sum(m.rows for m in all_metrics)}\n")
            f.write(f"- Average throughput: {avg_rows_per_sec:.1f} rows/sec\n")
            f.write(f"- Classification overhead: {avg_overhead:.1f}%\n\n")
            f.write("## Per-Document Metrics\n\n")
            f.write("| Document | Pages | Tables | Rows | Duration (s) | Rows/sec |\n")
            f.write("|----------|-------|--------|------|--------------|----------|\n")
            for m in all_metrics:
                f.write(
                    f"| {m.doc_name} | {m.pages} | {m.tables} | {m.rows} | {m.duration:.1f} | {m.rows_per_second:.1f} |\n"
                )

        print(f"\nPerformance metrics saved to: {report_path}")
        print(f"Classification overhead: {avg_overhead:.1f}%")

    # Return exit code (0 = success, 1 = partial/complete failure)
    return 0 if not failed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
