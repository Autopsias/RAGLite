"""
Health Check Tests for External Data Sources

This package contains health check tests that run against real external APIs
to detect changes, deprecations, or data format modifications early.

These tests are:
- Excluded from regular test runs (marked with @pytest.mark.health_check)
- Run daily via CI scheduled workflow
- Used to monitor API stability

Usage:
    pytest tests/health/ -v --tb=short

Story: 6.9 - External Data Source Client Fixes
Created: 2025-12-08
"""
