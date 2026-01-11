"""BPstat (Banco de Portugal Statistics) API client.

Facade for backward compatibility. Re-exports all public API.

Story 6.1: Tier 1 External Data Source Integration
Story 6.9.3: BPstat Banco de Portugal Fix
"""

from .client import BPSTAT_API_BASE, BPstatClient  # noqa: F401

__all__ = ["BPstatClient", "BPSTAT_API_BASE"]
