"""UAT Validation Tests for Epic 1 - Main test file.

This module re-exports test classes from split modules for backward compatibility.

Story 1.7: Email Episode Validation Workflow
- AC1: Episode metadata extraction works for financial emails
- AC2: Document segmentation functions correctly
- AC3: Search and retrieval operates on ingested content
- AC4: Performance meets user expectations (<5s response time)
"""

# Import all test classes for backward compatibility
from .test_auth_config import setup_uat_authentication
from .test_metadata import TestEpic1MetadataExtraction
from .test_performance import TestEpic1QueryPerformance
from .test_search_retrieval import TestEpic1SearchRetrieval
from .test_segmentation import TestEpic1DocumentSegmentation

# Legacy class name - alias for compatibility
TestEpic1EmailEpisodeValidation = type(
    "TestEpic1EmailEpisodeValidation",
    (
        TestEpic1MetadataExtraction,
        TestEpic1DocumentSegmentation,
        TestEpic1SearchRetrieval,
        TestEpic1QueryPerformance,
    ),
    {},  # Empty dict for namespace
)

__all__ = [
    "TestEpic1EmailEpisodeValidation",
    "TestEpic1MetadataExtraction",
    "TestEpic1DocumentSegmentation",
    "TestEpic1SearchRetrieval",
    "TestEpic1QueryPerformance",
    "setup_uat_authentication",
]
