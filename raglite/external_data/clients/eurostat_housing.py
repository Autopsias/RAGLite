"""Eurostat housing market data client.

Story 7b-7: Demand-Side Regressors for Cement Industry

Fetches housing market indicators from Eurostat:
- Housing transactions (prc_hpi_inx)

These are demand-side regressors for cement industry forecasting,
complementing the cost-side regressors (energy prices, interest rates).
"""

from __future__ import annotations

from datetime import date

from raglite.external_data.clients.eurostat import EurostatClient
from raglite.external_data.models import EurostatDwellingCompletions, EurostatHousingTransactions
from raglite.shared.logging import get_logger

logger = get_logger(__name__)


class EurostatHousingClient(EurostatClient):
    """Extended Eurostat client for housing market data.

    Story 7b-7: Adds housing transactions fetcher for demand-side regressors.

    Inherits from EurostatClient to reuse:
    - _fetch_with_retry() for API calls with exponential backoff
    - _parse_eurostat_period() for period string parsing
    - _fetch_eurostat_data() for SDMX API queries

    Example:
        >>> client = EurostatHousingClient()
        >>> transactions = await client.fetch_housing_transactions(
        ...     country="PT",
        ...     start_date=date(2020, 1, 1),
        ...     end_date=date(2024, 12, 31),
        ... )
    """

    # Dataset codes for housing market
    # prc_hpi_q: House Price Index quarterly (2015=100) - proxy for housing market activity
    # Note: prc_hpi_inx not available via dissemination API, use prc_hpi_q instead
    HOUSING_TRANSACTIONS_DATASET = "prc_hpi_q"
    # sts_cobp_m: Building permits - number of dwellings (monthly)
    DWELLING_COMPLETIONS_DATASET = "sts_cobp_m"

    async def fetch_housing_transactions(
        self,
        country: str = "PT",
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[EurostatHousingTransactions]:
        """Fetch quarterly housing transactions from Eurostat.

        Story 7b-7 AC1: Demand-side regressor for construction activity.

        Dataset: prc_hpi_inx (House Price Index - includes transaction counts)
        Coverage: Quarterly, 2019-present for Portugal
        Source: INE Portugal via Tax Authority (IMT property transfer tax)

        The number of transactions is a leading indicator for cement demand:
        - Housing purchases -> renovation/construction -> cement consumption
        - 6-12 month lag between transaction and cement demand

        Args:
            country: ISO 2-letter country code (default: PT for Portugal)
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of housing transaction records with quarterly counts
        """
        logger.info(
            "Fetching Eurostat housing transactions",
            extra={
                "country": country,
                "start": str(start_date) if start_date else "all",
                "end": str(end_date) if end_date else "all",
            },
        )

        # Use Statistics API (JSON-stat format) for prc_hpi_inx
        # This is similar to construction_confidence which uses the Statistics API
        base_url = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
        url = f"{base_url}/{self.HOUSING_TRANSACTIONS_DATASET}"

        # Build time period filter
        if start_date:
            since_period = f"{start_date.year}-Q{(start_date.month - 1) // 3 + 1}"
        else:
            since_period = "2019-Q1"  # Dataset starts ~2019 for transactions

        if end_date:
            until_period = f"{end_date.year}-Q{(end_date.month - 1) // 3 + 1}"
        else:
            until_period = None

        params = {
            "geo": country,
            "unit": "I15_Q",  # Quarterly index, 2015=100
            "purchase": "TOTAL",  # All purchases (new + existing dwellings)
            "format": "JSON",
            "lang": "en",
            "sinceTimePeriod": since_period,
        }
        if until_period:
            params["untilTimePeriod"] = until_period

        try:
            data = await self._fetch_with_retry(url, params)
        except (TimeoutError, ConnectionError, ValueError) as e:
            logger.error(
                "Failed to fetch housing transactions",
                extra={"error": str(e), "country": country},
            )
            return []

        return self._parse_housing_price_index_data(data, country, start_date, end_date)

    def _parse_housing_price_index_data(
        self,
        data: dict,
        country: str,
        start_date: date | None,
        end_date: date | None,
    ) -> list[EurostatHousingTransactions]:
        """Parse Eurostat house price index response (prc_hpi_q).

        The prc_hpi_q dataset returns quarterly house price index values.
        Index values are stored in transaction_count field for backward compatibility.

        Args:
            data: JSON-stat response from Eurostat Statistics API
            country: Country code
            start_date: Filter start date
            end_date: Filter end date

        Returns:
            List of housing transaction records (using index values)
        """
        results: list[EurostatHousingTransactions] = []

        # Get values and time dimension from JSON-stat format
        values = data.get("value", {})
        dimensions = data.get("dimension", {})
        time_dim = dimensions.get("time", {}).get("category", {})
        time_index = time_dim.get("index", {})

        if not time_index or not values:
            logger.warning("No time periods or values in house price index response")
            return results

        # Reverse the index mapping: position -> period
        period_by_index = {v: k for k, v in time_index.items()}

        for idx_str, index_value in values.items():
            try:
                idx = int(idx_str)
                period = period_by_index.get(idx)

                if not period or index_value is None:
                    continue

                # Parse quarterly period (2024-Q1, 2024-Q2, etc.)
                record_date = self._parse_quarterly_period(period)
                if record_date is None:
                    continue

                # Apply date filters
                if start_date and record_date < start_date.replace(day=1):
                    continue
                if end_date and record_date > end_date:
                    continue

                # Store index value as integer (e.g., 174.59 -> 175)
                results.append(
                    EurostatHousingTransactions(
                        date=record_date,
                        transaction_count=int(round(index_value)),
                        country=country,
                        period=period,
                    )
                )

            except (ValueError, KeyError) as e:
                logger.warning(
                    "Failed to parse house price index record",
                    extra={"index": idx_str, "error": str(e)},
                )
                continue

        results.sort(key=lambda x: x.date)
        logger.info(
            "Parsed Eurostat house price index",
            extra={"count": len(results), "country": country},
        )
        return results

    def _parse_housing_transactions_data(
        self,
        data: dict,
        country: str,
        start_date: date | None,
        end_date: date | None,
    ) -> list[EurostatHousingTransactions]:
        """Parse Eurostat housing transactions response (legacy).

        Note: This method is kept for backward compatibility with tests.
        The actual API now uses _parse_housing_price_index_data.

        Args:
            data: JSON-stat response from Eurostat Statistics API
            country: Country code
            start_date: Filter start date
            end_date: Filter end date

        Returns:
            List of housing transaction records
        """
        results: list[EurostatHousingTransactions] = []

        # Get values and time dimension from JSON-stat format
        values = data.get("value", {})
        dimensions = data.get("dimension", {})
        time_dim = dimensions.get("time", {}).get("category", {})
        time_index = time_dim.get("index", {})

        if not time_index or not values:
            logger.warning("No time periods or values in housing transactions response")
            return results

        # Reverse the index mapping: position -> period
        period_by_index = {v: k for k, v in time_index.items()}

        for idx_str, transaction_count in values.items():
            try:
                idx = int(idx_str)
                period = period_by_index.get(idx)

                if not period or transaction_count is None:
                    continue

                # Parse quarterly period (2024-Q1, 2024-Q2, etc.)
                record_date = self._parse_quarterly_period(period)
                if record_date is None:
                    continue

                # Apply date filters
                if start_date and record_date < start_date.replace(day=1):
                    continue
                if end_date and record_date > end_date:
                    continue

                results.append(
                    EurostatHousingTransactions(
                        date=record_date,
                        transaction_count=int(transaction_count),
                        country=country,
                        period=period,
                    )
                )

            except (ValueError, KeyError) as e:
                logger.warning(
                    "Failed to parse housing transactions record",
                    extra={"index": idx_str, "error": str(e)},
                )
                continue

        results.sort(key=lambda x: x.date)
        logger.info(
            "Parsed Eurostat housing transactions",
            extra={"count": len(results), "country": country},
        )
        return results

    def _parse_quarterly_period(self, period: str) -> date | None:
        """Parse quarterly period string to date.

        Handles format: YYYY-Q1, YYYY-Q2, YYYY-Q3, YYYY-Q4

        Args:
            period: Period string from Eurostat (e.g., "2024-Q3")

        Returns:
            date object (first day of quarter) or None if parsing fails
        """
        try:
            # Format: YYYY-Q1, YYYY-Q2, etc.
            if "-Q" in period and len(period) == 7:
                year = int(period[:4])
                quarter_str = period[-1]
                if quarter_str.isdigit():
                    quarter = int(quarter_str)
                    if 1 <= quarter <= 4:
                        # Map quarter to first month of quarter
                        month = (quarter - 1) * 3 + 1
                        return date(year, month, 1)
            return None
        except ValueError:
            return None

    async def fetch_dwelling_completions(
        self,
        country: str = "PT",
        start_date: date | None = None,
        end_date: date | None = None,
        dwelling_type: str = "TOTAL",
    ) -> list[EurostatDwellingCompletions]:
        """Fetch monthly building permit index from Eurostat.

        Story 7b-7 AC2: Lagging demand indicator for construction activity.

        Dataset: sts_cobp_m (Building permits - monthly data)
        Coverage: Monthly, 2000-present
        Source: INE Portugal via Eurostat

        Building permits are a leading indicator for cement demand:
        - Permits are granted before construction begins
        - Index values (2015=100) indicate activity level vs baseline

        Args:
            country: ISO 2-letter country code (default: PT for Portugal)
            start_date: Start of date range
            end_date: End of date range
            dwelling_type: Unused - kept for backward compatibility

        Returns:
            List of dwelling completion records with index values
        """
        logger.info(
            "Fetching Eurostat dwelling completions",
            extra={
                "country": country,
                "start": str(start_date) if start_date else "all",
                "end": str(end_date) if end_date else "all",
                "dwelling_type": dwelling_type,
            },
        )

        # Use Statistics API (JSON-stat format) for sts_cobp_m
        base_url = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
        url = f"{base_url}/{self.DWELLING_COMPLETIONS_DATASET}"

        # Note: sts_cobp_m doesn't support sinceTimePeriod/untilTimePeriod parameters
        # Fetch all data and filter client-side in _parse_dwelling_completions_data
        #
        # Correct dimension names for sts_cobp_m:
        # - indic_bt: BPRM_SQM (building permits - m2 of useful floor area)
        #   Note: Portugal doesn't have BPRM_DW (number of dwellings), only BPRM_SQM
        # - cpa2_1: CPA_F41001_41002 (total buildings - residential + non-residential)
        # - unit: I15 (index, 2015=100)
        # - s_adj: NSA (not seasonally adjusted)
        params = {
            "geo": country,
            "indic_bt": "BPRM_SQM",  # Building permits - m2 of useful floor area
            "cpa2_1": "CPA_F41001_41002",  # Total buildings
            "unit": "I15",  # Index 2015=100
            "s_adj": "NSA",  # Not seasonally adjusted (raw data)
            "format": "JSON",
            "lang": "en",
        }

        try:
            data = await self._fetch_with_retry(url, params)
        except (TimeoutError, ConnectionError, ValueError) as e:
            logger.error(
                "Failed to fetch dwelling completions",
                extra={"error": str(e), "country": country},
            )
            return []

        return self._parse_dwelling_completions_data(
            data, country, dwelling_type, start_date, end_date
        )

    def _parse_dwelling_completions_data(
        self,
        data: dict,
        country: str,
        dwelling_type: str,
        start_date: date | None,
        end_date: date | None,
    ) -> list[EurostatDwellingCompletions]:
        """Parse Eurostat dwelling completions response.

        Args:
            data: JSON-stat response from Eurostat Statistics API
            country: Country code
            dwelling_type: Dwelling type filter
            start_date: Filter start date
            end_date: Filter end date

        Returns:
            List of dwelling completion records
        """
        results: list[EurostatDwellingCompletions] = []

        # Get values and time dimension from JSON-stat format
        values = data.get("value", {})
        dimensions = data.get("dimension", {})
        time_dim = dimensions.get("time", {}).get("category", {})
        time_index = time_dim.get("index", {})

        if not time_index or not values:
            logger.warning("No time periods or values in dwelling completions response")
            return results

        # Reverse the index mapping: position -> period
        period_by_index = {v: k for k, v in time_index.items()}

        for idx_str, completion_count in values.items():
            try:
                idx = int(idx_str)
                period = period_by_index.get(idx)

                if not period or completion_count is None:
                    continue

                # Parse monthly period (2024M01, 2024M02, etc.)
                record_date = self._parse_monthly_period(period)
                if record_date is None:
                    continue

                # Apply date filters
                if start_date and record_date < start_date.replace(day=1):
                    continue
                if end_date and record_date > end_date:
                    continue

                results.append(
                    EurostatDwellingCompletions(
                        date=record_date,
                        completion_count=int(completion_count),
                        country=country,
                        dwelling_type=dwelling_type,
                    )
                )

            except (ValueError, KeyError) as e:
                logger.warning(
                    "Failed to parse dwelling completions record",
                    extra={"index": idx_str, "error": str(e)},
                )
                continue

        results.sort(key=lambda x: x.date)
        logger.info(
            "Parsed Eurostat dwelling completions",
            extra={"count": len(results), "country": country},
        )
        return results

    def _parse_monthly_period(self, period: str) -> date | None:
        """Parse monthly period string to date.

        Handles formats:
        - YYYYMNN (e.g., 2024M01, 2024M12)
        - YYYY-MM (e.g., 2024-01, 2024-12)

        Args:
            period: Period string from Eurostat

        Returns:
            date object (first day of month) or None if parsing fails
        """
        try:
            # Format 1: YYYYMNN (e.g., 2024M01)
            if "M" in period and len(period) == 7:
                year = int(period[:4])
                month = int(period[5:7])
                if 1 <= month <= 12:
                    return date(year, month, 1)

            # Format 2: YYYY-MM (e.g., 2024-01) - used by sts_cobp_m
            if "-" in period and len(period) == 7:
                parts = period.split("-")
                if len(parts) == 2:
                    year = int(parts[0])
                    month = int(parts[1])
                    if 1 <= month <= 12:
                        return date(year, month, 1)

            return None
        except ValueError:
            return None
