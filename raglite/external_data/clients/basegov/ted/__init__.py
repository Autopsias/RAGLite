"""TED API client module - facade for backward compatibility.

Story 8.2 Task 4: Refactored ted_api into structured package.
This facade preserves the original API for backward compatibility.
"""

from .client import fetch_ted_notices
from .workflow import fetch_ted_contracts

__all__ = ["fetch_ted_notices", "fetch_ted_contracts"]
