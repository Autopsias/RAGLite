"""Eurostat utility functions.

Story 8.2 Task 6: Eurostat client refactoring
"""

from datetime import date


def parse_eurostat_period(period: str) -> date | None:
    """Parse Eurostat period string to date.

    Handles multiple formats:
    - "2024-01" (monthly)
    - "2024-S1" (first semester)
    - "2024-S2" (second semester)
    - "2024" (annual)

    Args:
        period: Period string from Eurostat

    Returns:
        date object or None if parsing fails
    """
    try:
        # Monthly format: YYYY-MM
        if "-" in period and len(period) == 7 and period[5:].isdigit():
            year = int(period[:4])
            month = int(period[5:7])
            if 1 <= month <= 12:
                return date(year, month, 1)
            return None

        # Semester format: YYYY-S1 or YYYY-S2
        if "-S" in period and len(period) == 7:
            year = int(period[:4])
            semester_str = period[-1]
            if semester_str.isdigit():
                semester = int(semester_str)
                if semester == 1:
                    return date(year, 1, 1)
                elif semester == 2:
                    return date(year, 7, 1)
                # Only S1 and S2 are valid semesters
                return None
            return None

        # Annual format: YYYY
        if len(period) == 4 and period.isdigit():
            return date(int(period), 1, 1)

    except ValueError:
        pass

    return None
