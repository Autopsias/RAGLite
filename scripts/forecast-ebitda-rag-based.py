#!/usr/bin/env python3
"""RAG-based EBITDA forecasting using document context (not just SQL tables).

Replicates the methodology that produced the €207M 2025 baseline by:
1. Using vector search to find consolidated EBITDA mentions
2. Extracting values from narrative/executive summary sections
3. Building time series from RAG-extracted data
4. Forecasting 2026 with Prophet + LLM hybrid approach
"""

import asyncio
import os
import re
from collections import defaultdict
from datetime import datetime

os.environ["APP_ENV"] = "production"

from raglite.forecasting.hybrid import generate_forecast
from raglite.retrieval.search import hybrid_search
from raglite.shared.logging import get_logger
from raglite.shared.models import TimeSeriesData, TimeSeriesPoint

logger = get_logger(__name__)


async def extract_ebitda_from_rag(query: str, top_k: int = 50) -> dict:
    """Extract EBITDA values from document narratives using RAG.

    Args:
        query: Search query for EBITDA data
        top_k: Number of chunks to retrieve

    Returns:
        Dictionary mapping periods to EBITDA values extracted from text
    """
    logger.info(f"Searching for EBITDA data via RAG: {query}")

    # Disable SQL routing to search document text only
    results = await hybrid_search(
        query=query,
        top_k=top_k,
        enable_hybrid=True,
        auto_classify=False,
        enable_sql_tables=False,  # Force vector-only search for narrative context
    )

    logger.info(f"Retrieved {len(results)} relevant chunks")

    # Extract EBITDA values from text chunks
    ebitda_data = defaultdict(list)

    # Patterns to match EBITDA values in text
    # Examples: "EBITDA of €23.5M", "EBITDA: 23,500K", "consolidated EBITDA totaled €207M"
    patterns = [
        r"EBITDA[:\s]+(?:of\s+)?€?(\d+(?:,\d{3})*(?:\.\d+)?)\s*([KMB]?)",
        r"€(\d+(?:,\d{3})*(?:\.\d+)?)\s*([KMB]?)\s+EBITDA",
        r"consolidated.*?EBITDA.*?€?(\d+(?:,\d{3})*(?:\.\d+)?)\s*([KMB]?)",
        r"total.*?EBITDA.*?€?(\d+(?:,\d{3})*(?:\.\d+)?)\s*([KMB]?)",
    ]

    # Period patterns (e.g., "2025", "Q3 2025", "October 2025")
    period_patterns = [
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s-]+(20\d{2})",
        r"(20\d{2})",
        r"(Q[1-4])\s+(20\d{2})",
    ]

    for result in results:
        chunk_text = result.text
        doc_id = result.source_document

        # Extract EBITDA values
        for pattern in patterns:
            matches = re.finditer(pattern, chunk_text, re.IGNORECASE)
            for match in matches:
                value_str = match.group(1).replace(",", "")
                unit = match.group(2) if len(match.groups()) > 1 else ""

                try:
                    value = float(value_str)

                    # Convert to thousands (K)
                    if unit.upper() == "M":
                        value *= 1000  # Millions to thousands
                    elif unit.upper() == "B":
                        value *= 1000000  # Billions to thousands
                    # Default is K (thousands)

                    # Extract period from surrounding context
                    context_window = chunk_text[
                        max(0, match.start() - 200) : min(len(chunk_text), match.end() + 200)
                    ]

                    for period_pattern in period_patterns:
                        period_match = re.search(period_pattern, context_window)
                        if period_match:
                            period_str = " ".join(period_match.groups())
                            ebitda_data[period_str].append(
                                {
                                    "value": value,
                                    "doc_id": doc_id,
                                    "context": context_window[:150],
                                }
                            )
                            break

                except (ValueError, IndexError) as e:
                    logger.debug(f"Failed to parse EBITDA value: {e}")
                    continue

    return dict(ebitda_data)


async def build_timeseries_from_rag_data(ebitda_data: dict, min_points: int = 8) -> TimeSeriesData:
    """Build TimeSeriesData from RAG-extracted EBITDA values.

    Args:
        ebitda_data: Dictionary mapping periods to EBITDA values
        min_points: Minimum data points required

    Returns:
        TimeSeriesData object for forecasting
    """
    print("\n📊 Extracted EBITDA Data from Documents:")
    print("-" * 80)

    # Parse and aggregate by period
    period_values = {}

    for period_str, entries in sorted(ebitda_data.items()):
        if not entries:
            continue

        # Take median value if multiple mentions (more robust than mean)
        values = [e["value"] for e in entries]
        median_value = sorted(values)[len(values) // 2]

        # Parse period into datetime
        try:
            # Try different date formats
            if re.match(r"\d{4}$", period_str):  # Just year
                date = datetime(int(period_str), 12, 31)
                period_label = period_str
            elif re.match(r"Q[1-4]\s+\d{4}", period_str):  # Quarter
                match = re.match(r"Q(\d)\s+(\d{4})", period_str)
                quarter = int(match.group(1))
                year = int(match.group(2))
                month = quarter * 3  # Q1=Mar, Q2=Jun, Q3=Sep, Q4=Dec
                date = datetime(year, month, 1)
                period_label = f"Q{quarter} {year}"
            else:  # Month Year
                date = datetime.strptime(period_str, "%b %Y")
                period_label = period_str

            period_values[date] = (median_value, period_label, len(entries))

            print(f"{period_label:<15} | €{int(median_value):>12,}K ({len(entries)} mentions)")

        except (ValueError, AttributeError) as e:
            logger.debug(f"Failed to parse period '{period_str}': {e}")
            continue

    if len(period_values) < min_points:
        raise ValueError(
            f"Insufficient RAG-extracted data: {len(period_values)} periods found "
            f"(need {min_points}). Try broader search queries or check document coverage."
        )

    # Build TimeSeriesPoint objects
    points = []
    for date, (value, label, mentions) in sorted(period_values.items()):
        points.append(
            TimeSeriesPoint(date=date, value=float(value), label=f"{label} ({mentions} mentions)")
        )

    print(f"\n✅ Built time series: {len(points)} data points")
    print(f"   Range: {points[0].date.strftime('%b %Y')} to {points[-1].date.strftime('%b %Y')}")
    print(f"   Latest: €{int(points[-1].value):,}K")
    print()

    return TimeSeriesData(
        metric_name="Consolidated EBITDA (RAG-extracted)",
        points=points,
        interval="monthly",
        source_documents=[],
    )


async def forecast_ebitda_rag_based():
    """Main RAG-based EBITDA forecasting workflow."""
    print("\n" + "=" * 80)
    print("🏢 SECIL CONSOLIDATED EBITDA FORECAST (RAG-Based)")
    print("=" * 80)
    print()
    print("⚠️  Using PRODUCTION database (Qdrant:6333, PostgreSQL:5432)")
    print("📚 Method: Vector search + document context (NOT SQL tables)")
    print()

    # Step 1: Extract EBITDA data from document narratives
    print("=" * 80)
    print("STEP 1: Extract EBITDA from Document Narratives (Vector Search)")
    print("=" * 80)
    print()

    queries = [
        "consolidated EBITDA 2025 2024 total annual Secil Group all countries",
        "EBITDA performance full year results consolidated group",
        "total EBITDA millions euros 2025 2024 annual report",
    ]

    all_ebitda_data = {}

    for query in queries:
        print(f'🔍 Query: "{query}"')
        ebitda_data = await extract_ebitda_from_rag(query, top_k=30)

        # Merge results
        for period, entries in ebitda_data.items():
            if period not in all_ebitda_data:
                all_ebitda_data[period] = entries
            else:
                all_ebitda_data[period].extend(entries)

        print(f"   Found data for {len(ebitda_data)} periods")
        print()

    # Step 2: Build time series
    print("=" * 80)
    print("STEP 2: Build Time Series from Extracted Data")
    print("=" * 80)

    ts_data = await build_timeseries_from_rag_data(all_ebitda_data, min_points=6)

    # Step 3: Generate forecast
    print("=" * 80)
    print("STEP 3: Generate 2026 Forecast (Prophet + LLM Hybrid)")
    print("=" * 80)
    print()

    print("🔮 Generating 12-month forecast...")
    result = await generate_forecast(
        metric="Consolidated EBITDA", historical_data=ts_data, periods_ahead=12
    )

    print("✅ Forecast complete!")
    print()

    # Step 4: Display results
    print("=" * 80)
    print("2026 CONSOLIDATED EBITDA FORECAST")
    print("=" * 80)
    print()

    print(f"{'Period':<12} | {'Forecast (€K)':>15}")
    print("-" * 40)

    for pred in result.forecast[:12]:
        period = pred.date.strftime("%b %Y")
        forecast_val = int(pred.value)
        print(f"{period:<12} | €{forecast_val:>12,}K")

    print()

    # Summary
    forecast_values = [int(p.value) for p in result.forecast[:12]]
    total_2026 = sum(forecast_values)
    avg_2026 = total_2026 // 12

    print("📊 2026 Summary:")
    print(f"   Total EBITDA: €{total_2026:,}K (€{total_2026 // 1000}M)")
    print(f"   Monthly Average: €{avg_2026:,}K")
    print()

    # Compare to baseline
    historical_values = [int(p.value) for p in ts_data.points]
    latest_historical = historical_values[-1]
    historical_avg = sum(historical_values) // len(historical_values)

    print("📈 Year-over-Year Comparison:")
    print(f"   Latest Historical: €{latest_historical:,}K")
    print(f"   Historical Average: €{historical_avg:,}K")
    print(f"   2026 Forecast Avg: €{avg_2026:,}K")

    if historical_avg > 0:
        yoy_change = ((avg_2026 - historical_avg) / historical_avg) * 100
        print(f"   Change: {yoy_change:+.1f}%")
    print()

    # AI reasoning
    print("=" * 80)
    print("AI FORECAST REASONING")
    print("=" * 80)
    print()
    print(result.confidence_reasoning)
    print()

    print("=" * 80)
    print("✅ RAG-BASED FORECAST COMPLETE")
    print("=" * 80)
    print()


if __name__ == "__main__":
    asyncio.run(forecast_ebitda_rag_based())
