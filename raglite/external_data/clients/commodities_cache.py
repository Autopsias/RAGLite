"""Cache management for commodities price data.

Story 6.1: Tier 1 External Data Source Integration
Extracted from commodities.py for better modularity.
"""

from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path

from raglite.external_data.exceptions import ExternalDataFetchError
from raglite.external_data.models import CO2EUAPrice, CoalPrice, CommodityPrice, PetcokePrice
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


def load_from_cache(
    cache_dir: Path,
    commodity: str,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[CommodityPrice]:
    """Load commodity prices from local cache.

    Args:
        cache_dir: Cache directory path
        commodity: Commodity type (coal, petcoke, co2_eua)
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

    results: list[CommodityPrice] = []
    for record in data:
        try:
            record_date = date.fromisoformat(record["date"])

            if start_date and record_date < start_date:
                continue
            if end_date and record_date > end_date:
                continue

            # Create appropriate model based on commodity type
            price_obj: CommodityPrice
            if commodity == "coal":
                price_obj = CoalPrice(
                    date=record_date,
                    price=float(record["price"]),
                    currency=record.get("currency", "EUR"),
                    grade=record.get("grade"),
                )
            elif commodity == "petcoke":
                price_obj = PetcokePrice(
                    date=record_date,
                    price=float(record["price"]),
                    currency=record.get("currency", "EUR"),
                    sulfur_content_pct=record.get("sulfur_content_pct"),
                )
            elif commodity == "co2_eua":
                price_obj = CO2EUAPrice(
                    date=record_date,
                    price=float(record["price"]),
                    currency=record.get("currency", "EUR"),
                )
            else:
                price_obj = CommodityPrice(
                    date=record_date,
                    commodity=commodity,
                    price=float(record["price"]),
                    currency=record.get("currency", "EUR"),
                    unit=record.get("unit", "EUR/tonne"),
                )
            results.append(price_obj)
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
    prices: list[CommodityPrice] | list[CO2EUAPrice] | list[CoalPrice] | list[PetcokePrice],
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

        # Add commodity-specific fields
        if isinstance(price, CoalPrice):
            record["grade"] = price.grade
        elif isinstance(price, PetcokePrice):
            record["sulfur_content_pct"] = price.sulfur_content_pct
        elif isinstance(price, CO2EUAPrice):
            record["market"] = price.market

        existing_by_date[price.date.isoformat()] = record

    # Sort by date and save
    sorted_data = sorted(existing_by_date.values(), key=lambda x: x["date"])

    with open(cache_file, "w") as f:
        json.dump(sorted_data, f, indent=2)

    logger.info(
        f"Saved {len(prices)} {commodity} prices to cache",
        extra={"cache_file": str(cache_file), "total_records": len(sorted_data)},
    )


def import_from_csv(
    cache_dir: Path,
    commodity: str,
    csv_path: str | Path,
) -> list[CommodityPrice]:
    """Import commodity prices from CSV file.

    Expected CSV format:
    date,price,currency,unit,[commodity-specific columns]

    Args:
        cache_dir: Cache directory path
        commodity: Commodity type
        csv_path: Path to CSV file

    Returns:
        List of imported price records
    """
    path = Path(csv_path)
    if not path.exists():
        raise ExternalDataFetchError(
            source="Commodities",
            message=f"CSV file not found: {csv_path}",
        )

    results: list[CommodityPrice] = []

    with open(path) as f:
        reader = csv.DictReader(f)

        for row in reader:
            try:
                record_date = date.fromisoformat(row["date"])
                price_val = float(row["price"])
                currency = row.get("currency", "EUR")
                unit = row.get("unit", "EUR/tonne")

                price_obj: CommodityPrice
                if commodity == "coal":
                    price_obj = CoalPrice(
                        date=record_date,
                        price=price_val,
                        currency=currency,
                        grade=row.get("grade"),
                    )
                elif commodity == "petcoke":
                    price_obj = PetcokePrice(
                        date=record_date,
                        price=price_val,
                        currency=currency,
                        sulfur_content_pct=(
                            float(row["sulfur_content_pct"])
                            if row.get("sulfur_content_pct")
                            else None
                        ),
                    )
                elif commodity == "co2_eua":
                    price_obj = CO2EUAPrice(
                        date=record_date,
                        price=price_val,
                        currency=currency,
                    )
                else:
                    price_obj = CommodityPrice(
                        date=record_date,
                        commodity=commodity,
                        price=price_val,
                        currency=currency,
                        unit=unit,
                    )
                results.append(price_obj)
            except (ValueError, KeyError) as e:
                logger.warning(
                    f"Failed to parse CSV row for {commodity}",
                    extra={"error": str(e)},
                )
                continue

    # Save to cache
    save_to_cache(cache_dir, commodity, results)

    logger.info(
        f"Imported {len(results)} {commodity} prices from CSV",
        extra={"csv_path": str(csv_path)},
    )

    return results
