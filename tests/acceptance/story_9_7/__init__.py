"""ATDD tests for Story 9.7: Re-ingestion - Process Existing PDFs with New Pipeline.

TDD RED Phase: All tests MUST fail initially because the re-ingestion
scripts and validation tools do not exist yet:
- scripts/prepare-reingestion.py (cleanup and backup verification)
- scripts/validate-classification-coverage.py (100% coverage check)
- scripts/validate-classification-accuracy.py (ground truth comparison)
- tests/fixtures/classification_ground_truth.json (50+ verified examples)
- Updated scripts/reingest-all-documents.py with all 33 PDFs
"""
