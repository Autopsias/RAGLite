"""Parsers for BPstat API responses.

Story 6.9.3: BPstat Banco de Portugal Fix
Story 6.8: Bank appraisal values for housing
"""

from __future__ import annotations

from datetime import date

from raglite.external_data.models import BPstatBankAppraisal, BPstatMortgageLoans
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


class BPstatParser:
    """Parser for BPstat API responses.

    Encapsulates parsing logic for mortgage interest rate data.
    """

    def __init__(self, mortgage_rate_median: str, mortgage_loans_series: str):
        """Initialize parser with series IDs.

        Args:
            mortgage_rate_median: Primary series ID for median mortgage rate
            mortgage_loans_series: Legacy series ID for backward compatibility
        """
        self.MORTGAGE_RATE_MEDIAN = mortgage_rate_median
        self.MORTGAGE_LOANS_SERIES = mortgage_loans_series

    def _extract_period_from_observation(self, obs: dict) -> str | None:
        """Extract period from observation dict.

        Handles both old ("period": "2024-01") and new ("reference_date": "2024-01-31") formats.

        Args:
            obs: Single observation from API response

        Returns:
            Period string (YYYY-MM) or None if not found
        """
        period: str | None = obs.get("period", obs.get("refPeriod"))
        if not period:
            ref_date = obs.get("reference_date")
            if ref_date:
                # Convert "2024-01-31" to "2024-01"
                period = ref_date[:7]
        return period

    def _build_observations_lookup(
        self, raw_observations: list[dict]
    ) -> dict[str, dict[str, float]]:
        """Build lookup dict for observations by period and series.

        Args:
            raw_observations: List of observation dicts from API

        Returns:
            Nested dict: {period: {series_id: value}}
        """
        observations_by_period: dict[str, dict[str, float]] = {}

        for obs in raw_observations:
            try:
                period = self._extract_period_from_observation(obs)
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

        return observations_by_period

    def _create_mortgage_records(
        self, observations_by_period: dict[str, dict[str, float]]
    ) -> list[BPstatMortgageLoans]:
        """Create mortgage loan records from observations lookup.

        Args:
            observations_by_period: Nested dict from _build_observations_lookup

        Returns:
            List of BPstatMortgageLoans records
        """
        results = []

        for period, series_values in sorted(observations_by_period.items()):
            try:
                # Parse period (format: YYYY-MM)
                year, month = map(int, period.split("-"))
                record_date = date(year, month, 1)

                # Get median rate (primary series) - required
                median_rate = series_values.get(self.MORTGAGE_RATE_MEDIAN)
                if median_rate is None:
                    # Try old alias for backward compatibility
                    median_rate = series_values.get(self.MORTGAGE_LOANS_SERIES)

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

        return results

    def parse_interest_rate_data(
        self,
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
        # New API response structure:
        # {
        #   "data": {
        #     "series_id": { ... series metadata ... },
        #     ...
        #   },
        #   "observations": [
        #     { "period": "2024-01", "value": 3.45, "series_id": "12710733" },
        #     ...
        #   ]
        # }

        # Story 6.9.4: BPstat API returns data in "data" array (not "observations")
        # Each item has "reference_date" (YYYY-MM-DD format) instead of "period"
        raw_observations = response_data.get("data", response_data.get("observations", []))

        # Build lookup and create records
        observations_by_period = self._build_observations_lookup(raw_observations)
        results = self._create_mortgage_records(observations_by_period)

        logger.info(
            "Parsed BPstat mortgage interest rates",
            extra={"record_count": len(results)},
        )
        return results

    def _merge_loan_data(
        self,
        total_loans: dict,
        new_loans: dict,
        rates: dict,
    ) -> list[BPstatMortgageLoans]:
        """Merge loan data from multiple series (DEPRECATED).

        Story 6.9.3: This method is deprecated. Use parse_interest_rate_data instead.
        Kept for backward compatibility only.

        Args:
            total_loans: Total outstanding loans data
            new_loans: New loans data
            rates: Interest rate data

        Returns:
            List of merged loan records
        """
        logger.warning(
            "Using deprecated _merge_loan_data method - "
            "update caller to use parse_interest_rate_data"
        )

        results = []

        # Index new loans and rates by period for quick lookup
        new_loans_by_period = {}
        for obs in new_loans.get("observations", []):
            period = obs.get("period", obs.get("refPeriod"))
            if period and obs.get("value") is not None:
                new_loans_by_period[period] = float(obs["value"])

        rates_by_period = {}
        for obs in rates.get("observations", []):
            period = obs.get("period", obs.get("refPeriod"))
            if period and obs.get("value") is not None:
                rates_by_period[period] = float(obs["value"])

        # Process total loans as the primary series
        for obs in total_loans.get("observations", []):
            try:
                period = obs.get("period", obs.get("refPeriod"))
                value = obs.get("value")

                if not period or value is None:
                    continue

                # Parse period (format: YYYY-MM)
                year, month = map(int, period.split("-"))
                record_date = date(year, month, 1)

                results.append(
                    BPstatMortgageLoans(
                        date=record_date,
                        total_loans_eur=float(value) * 1_000_000,  # BPstat reports in millions
                        new_loans_eur=(
                            new_loans_by_period.get(period, 0) * 1_000_000
                            if period in new_loans_by_period
                            else None
                        ),
                        avg_interest_rate_pct=rates_by_period.get(period),
                    )
                )
            except (ValueError, KeyError) as e:
                logger.warning(
                    "Failed to parse BPstat observation",
                    extra={"period": obs.get("period"), "error": str(e)},
                )
                continue

        logger.info(
            "Parsed BPstat mortgage loans",
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


def parse_interest_rate_data(
    response_data: dict,
    series_ids: list[str],
    mortgage_rate_median: str = "12710733",
    mortgage_loans_series: str = "12710733",
) -> list[BPstatMortgageLoans]:
    """Standalone function to parse interest rate data.

    Convenience function for backward compatibility.

    Args:
        response_data: JSON response from BPstat API
        series_ids: List of series IDs that were requested
        mortgage_rate_median: Primary series ID for median mortgage rate
        mortgage_loans_series: Legacy series ID for backward compatibility

    Returns:
        List of mortgage interest rate records
    """
    parser = BPstatParser(mortgage_rate_median, mortgage_loans_series)
    return parser.parse_interest_rate_data(response_data, series_ids)
