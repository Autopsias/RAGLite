"""BPstat API configuration and constants.

Story 6.9.3 AC2: Updated API endpoint and series IDs (2025-12-08)
"""

# BPstat API Configuration
# Story 6.9.3 AC2: Updated from /data/v1 (404) to /api (working)
BPSTAT_API_BASE = "https://bpstat.bportugal.pt/api"


# IMPORTANT: Old series IDs (12532089, 12532090, 12532091) were WRONG
# They returned FX rates (Egyptian Pound, etc.), NOT mortgage data!
# See: https://bpstat.bportugal.pt/api/series/12532089 (returns "Egypt, Pounds (EGP)")


class BPstatSeries:
    """BPstat series IDs for mortgage interest rates.

    Story 6.9.3 AC1/AC6: Correct series IDs (verified 2025-12-08)
    Source: https://bpstat.bportugal.pt/api/series/{id}

    IMPORTANT: Old series IDs (12532089, 12532090, 12532091) were WRONG
    They returned FX rates (Egyptian Pound, etc.), NOT mortgage data!

    Interest rate distribution for new housing loans (variable rate):
    """

    # Primary series (50th percentile / median)
    MORTGAGE_RATE_MEDIAN = "12710733"
    MORTGAGE_RATE_10TH_PERCENTILE = "12710735"
    MORTGAGE_RATE_25TH_PERCENTILE = "12710781"
    MORTGAGE_RATE_75TH_PERCENTILE = "12710734"
    MORTGAGE_RATE_90TH_PERCENTILE = "12710736"

    # Backward compatibility aliases (deprecated - use new names)
    MORTGAGE_LOANS_SERIES = MORTGAGE_RATE_MEDIAN
    MORTGAGE_RATE_SERIES = MORTGAGE_RATE_MEDIAN

    # Story 6.8 AC2.2: Bank appraisal values for housing
    BANK_APPRAISAL_SERIES = "12559916"
