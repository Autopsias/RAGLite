"""Scripts package for RAGLite utilities.

This package contains utility scripts for database inspection,
data ingestion, accuracy validation, and other operational tasks.

Making this a proper Python package (with __init__.py) ensures
compatibility with coverage.py import hooks during test execution.
"""

__all__ = [
    "inspect_database_for_epic_3",
    "init_qdrant",
    "init_postgresql",
    "accuracy_utils",
]
