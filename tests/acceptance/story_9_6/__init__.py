"""ATDD tests for Story 9.6 - Storage Extension: Store Classification Fields.

This package contains acceptance tests that verify PostgreSQL storage
correctly persists classification fields (period_type, value_type, entity_level)
from enriched rows.

TDD RED Phase: All tests MUST fail initially because the storage module
has not been updated to include classification fields in INSERT statements.
"""
