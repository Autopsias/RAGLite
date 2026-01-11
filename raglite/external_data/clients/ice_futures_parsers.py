"""Parsers for ICE Futures data responses.

Handles:
- Quandl API2 Coal data parsing
- Quandl TTF Natural Gas data parsing
- Cache data parsing
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from raglite.external_data.models import API2CoalPrice, CommodityPrice, TTFGasPrice
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


def parse_quandl_coal_data(
    data: dict,
    start_date: date,
    end_date: date,
) -> list[API2CoalPrice]:
    """Parse Quandl API2 Coal response.

    Args:
        data: JSON response from Quandl
        start_date: Filter start date
        end_date: Filter end date

    Returns:
        List of API2 Coal price records
    """
    results: list[API2CoalPrice] = []

    dataset = data.get("dataset", data)
    raw_data = dataset.get("data", [])

    for row in raw_data:
        try:
            if len(row) < 2:
                continue

            date_str = row[0]
            price = row[1]

            if not date_str or price is None:
                continue

            record_date = date.fromisoformat(date_str)

            if not (start_date <= record_date <= end_date):
                continue

            results.append(
                API2CoalPrice(
                    date=record_date,
                    price=float(price),
                    currency="USD",
                )
            )

        except (ValueError, IndexError) as e:
            logger.warning(
                "Failed to parse Quandl coal record",
                extra={"row": row, "error": str(e)},
            )
            continue

    logger.info(
        "Parsed API2 Coal prices",
        extra={"count": len(results)},
    )
    return results


def parse_quandl_gas_data(
    data: dict,
    start_date: date,
    end_date: date,
) -> list[TTFGasPrice]:
    """Parse Quandl TTF gas response.

    Args:
        data: JSON response from Quandl
        start_date: Filter start date
        end_date: Filter end date

    Returns:
        List of TTF gas price records
    """
    results: list[TTFGasPrice] = []

    dataset = data.get("dataset", data)
    raw_data = dataset.get("data", [])

    # TTF data columns: Date, Open, High, Low, Settle, Change, Volume, Open Interest
    # We use Settle (index 4) or Open (index 1) if Settle not available
    settle_idx = 4
    open_idx = 1

    for row in raw_data:
        try:
            if len(row) < 2:
                continue

            date_str = row[0]

            # Try settle price first, then open
            price = None
            if len(row) > settle_idx and row[settle_idx] is not None:
                price = row[settle_idx]
            elif len(row) > open_idx and row[open_idx] is not None:
                price = row[open_idx]
            else:
                price = row[1]  # Fallback to second column

            if not date_str or price is None:
                continue

            record_date = date.fromisoformat(date_str)

            if not (start_date <= record_date <= end_date):
                continue

            results.append(
                TTFGasPrice(
                    date=record_date,
                    price=float(price),
                    currency="EUR",
                )
            )

        except (ValueError, IndexError) as e:
            logger.warning(
                "Failed to parse Quandl TTF record",
                extra={"row": row, "error": str(e)},
            )
            continue

    logger.info(
        "Parsed TTF Gas prices",
        extra={"count": len(results)},
    )
    return results


def load_from_cache(
    cache_dir: Path,
    commodity: str,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[CommodityPrice | API2CoalPrice | TTFGasPrice]:
    """Load commodity prices from local cache.

    Args:
        cache_dir: Cache directory path
        commodity: Commodity type (api2_coal, ttf_gas)
        start_date: Optional filter start date
        end_date: Optional filter end date

    Returns:
        List of cached price records
    """
    cache_file = cache_dir / f"{commodity}_prices.json"

    if not cache_file.exists():
        logger.warning(
            f"No cached data for {commodity}",
            extra={"cache_file": str(cache_file)},
        )
        return []

    try:
        with open(cache_file) as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        logger.error(
            f"Failed to load {commodity} cache",
            extra={"error": str(e)},
        )
        return []

    results: list[CommodityPrice | API2CoalPrice | TTFGasPrice] = []
    for record in data:
        try:
            record_date = date.fromisoformat(record["date"])

            if start_date and record_date < start_date:
                continue
            if end_date and record_date > end_date:
                continue

            if commodity == "api2_coal":
                results.append(
                    API2CoalPrice(
                        date=record_date,
                        price=float(record["price"]),
                        currency=record.get("currency", "USD"),
                    )
                )
            elif commodity == "ttf_gas":
                results.append(
                    TTFGasPrice(
                        date=record_date,
                        price=float(record["price"]),
                        currency=record.get("currency", "EUR"),
                    )
                )

        except (ValueError, KeyError) as e:
            logger.warning(
                f"Failed to parse cached {commodity} record",
                extra={"error": str(e)},
            )
            continue

    return results


def save_to_cache(
    cache_dir: Path,
    commodity: str,
    prices: list[CommodityPrice] | list[API2CoalPrice] | list[TTFGasPrice],
) -> None:
    """Save commodity prices to local cache.

    Args:
        cache_dir: Cache directory path
        commodity: Commodity type
        prices: List of price records to cache
    """
    cache_file = cache_dir / f"{commodity}_prices.json"

    # Load existing data
    existing = []
    if cache_file.exists():
        try:
            with open(cache_file) as f:
                existing = json.load(f)
        except (OSError, json.JSONDecodeError):
            pass

    # Convert existing to dict keyed by date
    existing_by_date = {r["date"]: r for r in existing}

    # Add new prices (overwrite if date exists)
    for price in prices:
        record = {
            "date": price.date.isoformat(),
            "price": price.price,
            "currency": price.currency,
            "unit": price.unit,
        }
        existing_by_date[price.date.isoformat()] = record

    # Sort by date and save
    sorted_data = sorted(existing_by_date.values(), key=lambda x: x["date"])

    with open(cache_file, "w") as f:
        json.dump(sorted_data, f, indent=2)

    logger.info(
        f"Saved {len(prices)} {commodity} prices to cache",
        extra={"cache_file": str(cache_file), "total_records": len(sorted_data)},
    )
