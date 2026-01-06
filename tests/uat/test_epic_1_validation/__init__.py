"""UAT Validation Tests for Epic 1 - Facade for backward compatibility.

This package contains tests for Story 1.7: Email Episode Validation Workflow.
Tests are split into focused modules by functionality.

Story 1.7: Email Episode Validation Workflow
- AC1: Episode metadata extraction works for financial emails
- AC2: Document segmentation functions correctly
- AC3: Search and retrieval operates on ingested content
- AC4: Performance meets user expectations (<5s response time)

Created: 2025-12-15
Purpose: Fix authentication/authorization issues causing 401 errors in UAT validation

IMPORTANT: UAT tests should NEVER be run via VS Code Test Explorer.
Use the "Test: UAT (User Acceptance Tests)" task in VS Code instead.
This is because Test Explorer is designed for fast unit tests (<30s) and
will cause ghost failures with long-running UAT tests.
"""
