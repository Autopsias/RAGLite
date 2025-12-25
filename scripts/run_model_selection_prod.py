#!/usr/bin/env python3
"""Run model selection with production database settings.

This script runs the batch model selection job with explicit production
database configuration.
"""

import asyncio
import os
import sys

# Set production environment BEFORE any raglite imports
os.environ["APP_ENV"] = "production"
os.environ["POSTGRES_PORT"] = "5432"
os.environ["POSTGRES_DB"] = "raglite"
os.environ["POSTGRES_USER"] = "raglite"
os.environ["POSTGRES_PASSWORD"] = "raglite"

# Add project root to path
sys.path.insert(0, str(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from raglite.forecasting.model_selection_job import run_batch_model_selection
from raglite.shared.config import settings


async def main():
    """Run batch model selection with production database."""
    # Verify settings
    print(f"APP_ENV: {settings.app_env}")
    print(f"POSTGRES_PORT: {settings.postgres_port}")
    print(f"POSTGRES_DB: {settings.postgres_db}")
    print(f"POSTGRES_USER: {settings.postgres_user}")
    print()

    print("Starting model selection with production database...")
    print("=" * 60)

    results = await run_batch_model_selection(workers=4)

    print("=" * 60)
    print(f"\nModel selection complete. Processed {len(results)} variables.")

    # Print summary
    print("\nSummary:")
    for var_name, result in results.items():
        if hasattr(result, "best_model"):
            regressors = (
                ", ".join(result.best_regressor_set) if result.best_regressor_set else "None"
            )
            print(
                f"  {var_name}: {result.best_model} (MAPE: {result.best_mape:.2f}%, regressors: {regressors})"
            )
        else:
            print(f"  {var_name}: ERROR")

    return results


if __name__ == "__main__":
    asyncio.run(main())
