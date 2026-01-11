"""European electricity price client using Ember Energy data.

Story 6.29 P3: Phase 2 - Electricity Price Integration for Electricity Cost Regressor

Facade for backward compatibility. Re-exports all public API from internal modules.
"""

from .client import ENTSOEClient

__all__ = [
    "ENTSOEClient",
]
