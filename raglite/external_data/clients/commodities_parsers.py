"""Parsers for commodities data from various sources.

Story 6.1: Tier 1 External Data Source Integration
Extracted from commodities.py for better modularity.
"""

from __future__ import annotations

from datetime import date

from raglite.external_data.models import CO2EUAPrice
from raglite.shared.logging import get_logger

logger = get_logger(__name__)

# Minimum expected EU ETS price in EUR (sanity check)
# EU ETS prices have been 50-100 EUR/tCO2 since 2022
MIN_EXPECTED_CO2_PRICE_EUR = 40.0


def parse_co2_prices(
    data: dict,
    start_date: date,
    end_date: date,
) -> list[CO2EUAPrice]:
    """Parse CO2 EUA price data from API response.

    Args:
        data: API response
        start_date: Filter start date
        end_date: Filter end date

    Returns:
        List of CO2 EUA price records
    """
    results: list[CO2EUAPrice] = []

    for record in data.get("data", []):
        try:
            date_str = record.get("date")
            if not date_str:
                continue

            record_date = date.fromisoformat(date_str)
            if not (start_date <= record_date <= end_date):
                continue

            price = record.get("price", record.get("value"))
            if price is None:
                continue

            results.append(
                CO2EUAPrice(
                    date=record_date,
                    price=float(price),
                    currency="EUR",
                )
            )
        except (ValueError, KeyError) as e:
            logger.warning(
                "Failed to parse CO2 price record",
                extra={"error": str(e)},
            )
            continue

    return results


def validate_co2_prices(prices: list[CO2EUAPrice]) -> list[CO2EUAPrice]:
    """Validate CO2 prices are in expected EUR range.

    Story 6.29 P3: Added to detect KRBN contamination.
    EU ETS prices have been 50-100 EUR/tCO2 since 2022.
    KRBN ETF trades at ~$30/share - if we see prices this low, data is wrong.

    Args:
        prices: List of CO2 price records

    Returns:
        Validated prices (only those >= MIN_EXPECTED_CO2_PRICE_EUR)
    """
    if not prices:
        return []

    # Check for KRBN contamination (prices significantly below expected EU ETS levels)
    valid_prices = []
    invalid_count = 0

    for price in prices:
        # Convert USD to EUR if needed (approximate)
        price_eur = price.price
        if price.currency == "USD":
            price_eur = price.price * 0.92  # Approximate USD->EUR

        if price_eur >= MIN_EXPECTED_CO2_PRICE_EUR:
            valid_prices.append(price)
        else:
            invalid_count += 1

    if invalid_count > 0:
        logger.warning(
            "CO2 price validation: rejected low prices (likely KRBN contamination)",
            extra={
                "rejected": invalid_count,
                "accepted": len(valid_prices),
                "min_threshold_eur": MIN_EXPECTED_CO2_PRICE_EUR,
            },
        )

    return valid_prices
