"""ECB utility functions.

Story 8.2 Task 5: ECB client refactoring
"""

from datetime import date

from raglite.external_data.clients.ecb.models import ECBGDPGrowth


def parse_ecb_period(period: str) -> date:
    """Parse ECB period string to date.

    Story 6.17 AC4: Period parsing for quarterly and monthly formats.

    Handles:
    - Monthly: "2024-01" -> date(2024, 1, 1)
    - Quarterly: "2024-Q1" -> date(2024, 1, 1)

    Args:
        period: ECB period string (e.g., "2024-Q1" or "2024-03")

    Returns:
        First day of the period as date
    """
    if "-Q" in period:
        # Quarterly format: "2024-Q1", "2024-Q2", etc.
        year = int(period[:4])
        quarter = int(period[-1])
        month = (quarter - 1) * 3 + 1  # Q1=1, Q2=4, Q3=7, Q4=10
        return date(year, month, 1)
    else:
        # Monthly format: "2024-03"
        year, month = int(period[:4]), int(period[5:7])
        return date(year, month, 1)


def interpolate_quarterly_to_monthly(
    quarterly_data: list[ECBGDPGrowth],
    method: str = "constant",
) -> list[ECBGDPGrowth]:
    """Interpolate quarterly GDP data to monthly frequency.

    Story 6.17 AC3: Quarterly to monthly alignment for regressors.

    Args:
        quarterly_data: List of quarterly GDP records
        method: Interpolation method (default: "constant")
            - "constant": Each month gets quarter's value (implemented)
            - Other values: Currently not supported, raises NotImplementedError

    Returns:
        List of monthly GDP records

    Raises:
        NotImplementedError: If method is not "constant"

    Example:
        >>> quarterly = [
        ...     ECBGDPGrowth(date=date(2024, 1, 1), growth_pct=2.5, country="PT"),
        ...     ECBGDPGrowth(date=date(2024, 4, 1), growth_pct=2.8, country="PT"),
        ... ]
        >>> monthly = interpolate_quarterly_to_monthly(quarterly)
        >>> len(monthly)
        6
    """
    # Story 6.17 Code Review #2: Validate method parameter
    if method != "constant":
        raise NotImplementedError(
            f"Interpolation method '{method}' not implemented. Use 'constant'."
        )

    if not quarterly_data:
        return []

    monthly_data: list[ECBGDPGrowth] = []

    for quarter in quarterly_data:
        # Get the quarter start month (1, 4, 7, or 10)
        quarter_start_month = quarter.date.month

        # Generate 3 months for this quarter
        for month_offset in range(3):
            month = quarter_start_month + month_offset
            monthly_date = date(quarter.date.year, month, 1)

            monthly_data.append(
                ECBGDPGrowth(
                    date=monthly_date,
                    growth_pct=quarter.growth_pct,  # Constant interpolation
                    country=quarter.country,
                    frequency="M",  # Now monthly
                )
            )

    return monthly_data
