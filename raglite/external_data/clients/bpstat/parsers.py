"""BPstat data parsers for API responses.

Story 6.9.3 AC3: Updated parser for new API structure
"""

from __future__ import annotations

from datetime import date

from raglite.external_data.clients.bpstat.config import BPstatSeries
from raglite.external_data.models import BPstatBankAppraisal, BPstatMortgageLoans
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


def parse_interest_rate_data(
    response_data: dict,
    series_ids: list[str],
) -> list[BPstatMortgageLoans]:
    """Parse interest rate data from new API response.

    Story 6.9.3 AC3: Updated parser for new API structure

    Args:
        response_data: JSON response from BPstat API
        series_ids: List of series IDs that were requested

    Returns:
        List of mortgage interest rate records
    """
    results = []

    # Build lookup for observations by period and series
    observations_by_period: dict[str, dict[str, float]] = {}

    # Story 6.9.4: BPstat API returns data in "data" array (not "observations")
    # Each item has "reference_date" (YYYY-MM-DD format) instead of "period"
    raw_observations = response_data.get("data", response_data.get("observations", []))

    for obs in raw_observations:
        try:
            # Handle both old ("period": "2024-01") and new ("reference_date": "2024-01-31") formats
            period = obs.get("period", obs.get("refPeriod"))
            if not period:
                ref_date = obs.get("reference_date")
                if ref_date:
                    # Convert "2024-01-31" to "2024-01"
                    period = ref_date[:7]

            series_id = str(obs.get("series_id", obs.get("seriesId", "")))
            value = obs.get("value")

            if not period or value is None:
                continue

            if period not in observations_by_period:
                observations_by_period[period] = {}

            observations_by_period[period][series_id] = float(value)

        except (ValueError, TypeError) as e:
            logger.warning(
                "Failed to parse BPstat observation",
                extra={"obs": obs, "error": str(e)},
            )
            continue

    # Create records for each period where we have data
    for period, series_values in sorted(observations_by_period.items()):
        try:
            # Parse period (format: YYYY-MM)
            year, month = map(int, period.split("-"))
            record_date = date(year, month, 1)

            # Get median rate (primary series) - required
            median_rate = series_values.get(BPstatSeries.MORTGAGE_RATE_MEDIAN)
            if median_rate is None:
                # Try old alias for backward compatibility
                median_rate = series_values.get(BPstatSeries.MORTGAGE_LOANS_SERIES)

            if median_rate is None:
                logger.warning(
                    "Missing median rate for period",
                    extra={"period": period},
                )
                continue

            results.append(
                BPstatMortgageLoans(
                    date=record_date,
                    # Story 6.9.3: Now returns interest rates, not loan amounts
                    # total_loans_eur is kept for backward compatibility but
                    # will be 0 since we no longer fetch loan amount series
                    total_loans_eur=0.0,
                    new_loans_eur=None,
                    avg_interest_rate_pct=median_rate,
                )
            )

        except (ValueError, KeyError) as e:
            logger.warning(
                "Failed to create BPstat record",
                extra={"period": period, "error": str(e)},
            )
            continue

    logger.info(
        "Parsed BPstat mortgage interest rates",
        extra={"record_count": len(results)},
    )
    return results


def parse_bank_appraisal_data(
    response_data: dict,
) -> list[BPstatBankAppraisal]:
    """Parse bank appraisal data from API response.

    Args:
        response_data: JSON response from BPstat API

    Returns:
        List of bank appraisal records
    """
    results = []

    # Same API structure as interest rates
    raw_observations = response_data.get("data", response_data.get("observations", []))

    for obs in raw_observations:
        try:
            # Handle both old and new date formats
            period = obs.get("period", obs.get("refPeriod"))
            if not period:
                ref_date = obs.get("reference_date")
                if ref_date:
                    period = ref_date[:7]

            value = obs.get("value")

            if not period or value is None:
                continue

            # Parse period (format: YYYY-MM)
            year, month = map(int, period.split("-"))
            record_date = date(year, month, 1)

            results.append(
                BPstatBankAppraisal(
                    date=record_date,
                    avg_appraisal_eur_m2=float(value),
                    region="Portugal",
                )
            )

        except (ValueError, TypeError, KeyError) as e:
            logger.warning(
                "Failed to parse BPstat appraisal observation",
                extra={"obs": obs, "error": str(e)},
            )
            continue

    logger.info(
        "Parsed BPstat bank appraisals",
        extra={"record_count": len(results)},
    )
    return results
