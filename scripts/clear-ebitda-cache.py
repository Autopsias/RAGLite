#!/usr/bin/env python3
"""Clear stale EBITDA model selection cache to force fresh training.

EBITDA Forecast Fix (2026-02-03):
After implementing lagged correlation application, seasonal future regressor
strategy, and optimized Prophet configuration, the stale cache needs to be
cleared to train a fresh model with these improvements.

Usage:
    python scripts/clear-ebitda-cache.py [--all]

Options:
    --all   Clear all model selection cache entries (not just EBITDA)
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def main():
    """Clear EBITDA model selection cache."""
    from raglite.external_data.storage import (
        invalidate_all_model_selections,
        invalidate_model_selection,
    )
    from raglite.shared.logging import get_logger

    logger = get_logger(__name__)

    clear_all = "--all" in sys.argv

    if clear_all:
        print("Clearing ALL model selection cache entries...")
        count = invalidate_all_model_selections()
        print(f"Cleared {count} model selection cache entries.")
        logger.info("Cleared all model selection cache entries", extra={"count": count})
    else:
        # Clear EBITDA-related entries
        ebitda_variants = [
            "ebitda",
            "EBITDA",
            "ebitda ifrs",
            "EBITDA IFRS",
            "ebitda_margin",
        ]

        total_cleared = 0
        for variant in ebitda_variants:
            try:
                count = invalidate_model_selection(variant)
                if count > 0:
                    print(f"  Cleared cache for '{variant}': {count} entries")
                    total_cleared += count
            except ValueError:
                # Skip invalid names
                pass

        if total_cleared > 0:
            print(f"\nTotal: Cleared {total_cleared} EBITDA-related cache entries.")
            print("Next EBITDA forecast will train a fresh model with:")
            print("  - Lagged correlation application (1-3 month optimal lags)")
            print("  - Seasonal future regressor strategy (not constant)")
            print("  - Increased regressor prior scale (0.05 vs 0.01)")
            print("  - Multiplicative seasonality mode")
        else:
            print("No EBITDA cache entries found (may already be cleared or expired).")

        logger.info(
            "EBITDA model selection cache cleared",
            extra={"total_cleared": total_cleared, "variants_checked": ebitda_variants},
        )


if __name__ == "__main__":
    main()
