#!/usr/bin/env python3
"""Debug script to check for duplicate dates in Revenue extraction."""

import asyncio

import pandas as pd

from raglite.forecasting.timeseries_extract import extract_metric_from_qdrant_chunks


async def test():
    try:
        # Extract Revenue data
        ts_data = await extract_metric_from_qdrant_chunks(
            "Turnover+VAT", min_points=6, entity="portugal"
        )
        if not ts_data:
            print("No data")
            return

        print(f"Extracted {len(ts_data.points)} points")

        # Convert to pandas Series
        dates = [p.date for p in ts_data.points]
        values = [p.value for p in ts_data.points]

        print(f"Unique dates: {len(set(dates))} / {len(dates)}")
        if len(dates) != len(set(dates)):
            print("DUPLICATES IN EXTRACTION!")
            from collections import Counter

            date_counts = Counter(dates)
            for date, count in date_counts.items():
                if count > 1:
                    print(f"  {date}: {count}x")

        # Create pandas Series
        series = pd.Series(values, index=dates)
        print(f"Series index duplicated: {series.index.duplicated().any()}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test())
