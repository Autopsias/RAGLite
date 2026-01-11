"""Story 8.2 ATDD Tests: External Data Client Refactoring.

This package contains acceptance tests for Story 8.2 which splits large
external data files (storage.py, basegov.py, ecb.py, eurostat.py) into
modules under 500 LOC each with a shared base class.

Tests are designed in TDD RED state - they FAIL before refactoring and
PASS after refactoring is complete.
"""
