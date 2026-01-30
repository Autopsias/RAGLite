# Code Fix Recommendations - Data Quality Issues

**Date:** 2026-01-27
**Related:** `docs/analysis/data-quality-audit-report.md`
**Priority:** P0 fixes should be implemented before any forecasting is trusted

---

## Fix 1: Align Unit Conversion Thresholds (P0 - CRITICAL)

### Problem

The SQL query and Python post-processing use **different thresholds** for kEUR→EUR conversion, causing either:
- Double conversion (value divided by 1,000,000 instead of 1,000)
- No conversion (value left in wrong unit)

### Current Code

**File: `raglite/forecasting/timeseries/sql_extraction_query.py` (lines 119-124)**
```python
# FIX: Normalize values - if > 1000 assume kEUR, convert to EUR M
CASE
    WHEN value > 1000 THEN value / 1000.0
    ELSE value
END as value,
```

**File: `raglite/forecasting/timeseries/sql_extraction_normalization_utils/_normalization.py` (line 26)**
```python
EBITDA_KEUR_THRESHOLD = 10000  # Values > 10000 are in kEUR
```

### Recommended Fix: Remove SQL Inline Conversion

**Rationale:** Let Python handle all normalization with a single source of truth.

**Change in `sql_extraction_query.py` (lines 119-124):**

```python
# BEFORE:
CASE
    WHEN value > 1000 THEN value / 1000.0
    ELSE value
END as value,

# AFTER:
value,  -- Raw value, normalization handled in Python post-processing
```

**Full function update for `_build_periods_with_year_cte()`:**

```python
def _build_periods_with_year_cte(
    period_extract: str,
    is_ytd_flag: str,
    entity_priority_expr: str,
    metric_condition: str,
    period_match: str,
    entity_filter: str,
) -> str:
    """Build the periods_with_year CTE."""
    return f"""periods_with_year AS (
            SELECT
                {period_extract} as clean_period,
                {is_ytd_flag} as is_ytd,
                2000 + CAST(SUBSTRING(period FROM '[0-9]{{2}}$') AS INTEGER) as inferred_fiscal_year,
                document_id,
                value,  -- Raw value, normalization handled in Python
                entity,
                metric,
                {entity_priority_expr} as entity_priority
            FROM financial_tables
            WHERE {metric_condition}
              AND period IS NOT NULL
              {period_match}
              AND value IS NOT NULL
              {entity_filter}
        )"""
```

### Verification

After applying fix, run:
```bash
uv run python -c "
import asyncio
from raglite.forecasting.timeseries import extract_timeseries_from_sql

async def test():
    data = await extract_timeseries_from_sql('ebitda', min_points=6)
    values = [p.value for p in data.points if p.value > 0]
    if values:
        swing = max(values) / min(values)
        print(f'EBITDA swing ratio: {swing:.1f}x (target: <5x)')

asyncio.run(test())
"
```

---

## Fix 2: Add Variable Cost to Cost Metrics (P0)

### Problem

Variable Cost is already in `get_cost_metrics()` but may need explicit handling for the 88.9% negative values.

### Current Code

**File: `raglite/forecasting/timeseries/sql_extraction_config.py` (lines 161-176)**

```python
def get_cost_metrics() -> set[str]:
    """Get metrics that represent costs (need absolute value conversion)."""
    return {
        "electrical energy",
        "electricity",
        "electricity_cost",
        "thermal energy",
        "thermal",
        "thermal_cost",
        "fuel_cost",
        "variable cost",  # Already included
        "variable_cost",  # Already included
    }
```

### Status: ALREADY HANDLED

The current implementation correctly handles Variable Cost via:
1. `get_cost_metrics()` includes "variable cost" and "variable_cost"
2. `normalize_timeseries_data()` Step 6 calls `convert_cost_to_absolute()`
3. `convert_cost_to_absolute()` in `_postprocessing.py` converts to absolute values

### Verification

```python
# Confirm Variable Cost is handled
from raglite.forecasting.timeseries.sql_extraction_config import get_cost_metrics
assert "variable cost" in get_cost_metrics()
assert "variable_cost" in get_cost_metrics()
print("Variable Cost handling: CONFIRMED")
```

---

## Fix 3: Create Unit Normalization Module (P1)

### Problem

12,010 unique unit variants exist in the database with no standardization.

### Recommended Implementation

**New file: `raglite/ingestion/unit_normalizer.py`**

```python
"""Unit normalization for financial data.

Centralizes all unit variant handling to ensure consistent value scaling.
"""

from dataclasses import dataclass
from typing import Optional
import re


@dataclass
class UnitMapping:
    """Normalized unit with conversion multiplier."""
    normalized_unit: str
    multiplier: float
    notes: str = ""


# Master unit normalization map
UNIT_NORMALIZATION_MAP: dict[str, UnitMapping] = {
    # Standard EUR variants
    "EUR": UnitMapping("EUR", 1.0, "Base currency"),
    "€": UnitMapping("EUR", 1.0, "Symbol variant"),
    "Euro": UnitMapping("EUR", 1.0, "Text variant"),

    # Thousands (kEUR)
    "K EUR": UnitMapping("EUR", 1000.0, "Thousands"),
    "KEUR": UnitMapping("EUR", 1000.0, "Thousands compact"),
    "kEUR": UnitMapping("EUR", 1000.0, "Thousands lowercase"),
    "1000 EUR": UnitMapping("EUR", 1000.0, "Explicit thousands"),

    # Millions (MEUR)
    "M EUR": UnitMapping("EUR", 1_000_000.0, "Millions"),
    "MEUR": UnitMapping("EUR", 1_000_000.0, "Millions compact"),
    "Meur": UnitMapping("EUR", 1_000_000.0, "Millions mixed case"),
    "M€": UnitMapping("EUR", 1_000_000.0, "Millions symbol"),

    # Other currencies - thousands
    "1000 BRL": UnitMapping("BRL", 1000.0, "Brazilian Real thousands"),
    "1000 AOA": UnitMapping("AOA", 1000.0, "Angolan Kwanza thousands"),
    "1000 TND": UnitMapping("TND", 1000.0, "Tunisian Dinar thousands"),
    "1000 LBP": UnitMapping("LBP", 1000.0, "Lebanese Pound thousands"),
    "1000 USD": UnitMapping("USD", 1000.0, "US Dollar thousands"),
    "1000 AKZ": UnitMapping("AKZ", 1000.0, "Angolan Kwanza alt"),

    # Percentages (no conversion)
    "%": UnitMapping("PCT", 1.0, "Percentage"),
    "pp": UnitMapping("PP", 1.0, "Percentage points"),
    "% LY": UnitMapping("PCT_LY", 1.0, "Percent vs last year"),
    "% B": UnitMapping("PCT_B", 1.0, "Percent vs budget"),

    # Volume units
    "kton": UnitMapping("KTON", 1.0, "Kilotons"),
    "km3": UnitMapping("KM3", 1.0, "Cubic kilometers"),

    # Price units (no conversion needed)
    "Eur/ton": UnitMapping("EUR_TON", 1.0, "Euro per ton"),
    "EUR/ton": UnitMapping("EUR_TON", 1.0, "Euro per ton"),
    "Eur/m3": UnitMapping("EUR_M3", 1.0, "Euro per cubic meter"),
    "EUR/m3": UnitMapping("EUR_M3", 1.0, "Euro per cubic meter"),
    "BRL/ton": UnitMapping("BRL_TON", 1.0, "Real per ton"),
    "USD/ton": UnitMapping("USD_TON", 1.0, "Dollar per ton"),
    "LCU/ton": UnitMapping("LCU_TON", 1.0, "Local currency per ton"),
}

# Patterns for detecting malformed units
MALFORMED_PATTERNS = [
    r"[#@!()]",           # Symbol corruption
    r"^-?[0-9]+\.?[0-9]*$",  # Pure numeric
    r"^[A-Z][a-z]{2}-[0-9]{2}$",  # Period code (e.g., "Aug-25")
]


def is_malformed_unit(unit: str | None) -> bool:
    """Check if unit value is malformed/corrupted."""
    if unit is None or unit.strip() == "":
        return False

    for pattern in MALFORMED_PATTERNS:
        if re.match(pattern, unit.strip()):
            return True
    return False


def normalize_unit(raw_unit: str | None) -> tuple[str | None, float]:
    """Normalize unit to standard format and return multiplier.

    Args:
        raw_unit: Raw unit string from database

    Returns:
        Tuple of (normalized_unit, multiplier)
        Returns (None, 1.0) for malformed or unknown units
    """
    if raw_unit is None or raw_unit.strip() == "":
        return None, 1.0

    unit = raw_unit.strip()

    # Check for malformed
    if is_malformed_unit(unit):
        return None, 1.0

    # Look up in map
    mapping = UNIT_NORMALIZATION_MAP.get(unit)
    if mapping:
        return mapping.normalized_unit, mapping.multiplier

    # Unknown unit - return as-is with no conversion
    return unit, 1.0


def normalize_value_with_unit(
    value: float | None,
    unit: str | None,
    target_unit: str = "EUR"
) -> float | None:
    """Normalize a value based on its unit.

    Args:
        value: Raw value
        unit: Unit string
        target_unit: Target unit for normalization (default: EUR)

    Returns:
        Normalized value, or None if value is None
    """
    if value is None:
        return None

    _, multiplier = normalize_unit(unit)

    # Convert to base unit (EUR for financial values)
    return value * multiplier
```

### Usage Example

```python
from raglite.ingestion.unit_normalizer import normalize_value_with_unit

# Example: 5000 in K EUR → 5,000,000 in EUR
value = normalize_value_with_unit(5000, "K EUR")  # Returns 5,000,000.0

# Example: Malformed unit → returns raw value
value = normalize_value_with_unit(100, "Aug-25")  # Returns 100.0 (multiplier=1.0)
```

---

## Fix 4: Entity Contamination Filter (P1)

### Problem

489 rows have metrics (like "CF from Operations") stored in the entity column.

### Recommended Fix

Add entity exclusion list to `sql_extraction_execution.py`:

```python
# Add to sql_extraction_config.py

CONTAMINATED_ENTITIES = {
    "CF from Operations",
    "Net interest expenses",
    "De(in)crease Trade Working Capital",
    "CF from Operating Activities",
    "Other Working Capital Variances",
    "Trade Working Capital",
}

def get_entity_exclusion_clause() -> str:
    """Get SQL clause to exclude contaminated entities."""
    exclusions = ", ".join(f"'{e}'" for e in CONTAMINATED_ENTITIES)
    return f"AND entity_normalized NOT IN ({exclusions})"
```

### Integration Point

In `build_entity_filter_clause()`:

```python
def build_entity_filter_clause(
    metric_search: str,
    ENTITY_FILTERS: dict[str, tuple[str | None, bool]],
) -> tuple[str, bool]:
    """Build entity filter SQL clause."""
    entity_filter = ""
    prefer_ytd = False

    # Always exclude contaminated entities
    entity_filter += get_entity_exclusion_clause()

    # ... rest of existing logic
```

---

## Fix 5: Remove Invalid Fiscal Years (P2)

### Problem

11 rows have clearly invalid fiscal years (2030, 2045).

### Recommended SQL Fix

```sql
-- Run once to clean invalid data
DELETE FROM financial_tables
WHERE fiscal_year IN (2030, 2045);

-- Optionally flag 2026 as budget data
UPDATE financial_tables
SET notes = 'Budget/Forecast data'
WHERE fiscal_year = 2026;
```

### Verification

```sql
SELECT fiscal_year, COUNT(*)
FROM financial_tables
WHERE fiscal_year > 2025
GROUP BY fiscal_year;
-- Should return only 2026 (budget data)
```

---

## Implementation Priority

| Fix | Priority | Effort | Impact |
|-----|----------|--------|--------|
| Fix 1: Remove SQL inline conversion | P0 | Low | High |
| Fix 2: Variable Cost handling | P0 | None (already done) | N/A |
| Fix 3: Unit normalization module | P1 | Medium | High |
| Fix 4: Entity contamination filter | P1 | Low | Medium |
| Fix 5: Invalid fiscal years | P2 | Low | Low |

---

## Testing After Fixes

### Comprehensive Test Script

```python
"""Test script for data quality fixes."""

import asyncio
from raglite.forecasting.timeseries import extract_timeseries_from_sql

async def verify_fixes():
    """Run verification tests after applying fixes."""

    results = {}

    # Test 1: EBITDA swing ratio
    try:
        data = await extract_timeseries_from_sql('ebitda', min_points=6)
        values = [p.value for p in data.points if p.value > 0]
        if values:
            swing = max(values) / min(values)
            results['ebitda_swing'] = f"{swing:.1f}x"
            results['ebitda_pass'] = swing < 5.0
    except Exception as e:
        results['ebitda_error'] = str(e)

    # Test 2: Variable Cost (should be positive after conversion)
    try:
        data = await extract_timeseries_from_sql('variable_cost', min_points=6)
        negatives = sum(1 for p in data.points if p.value < 0)
        results['variable_cost_negatives'] = negatives
        results['variable_cost_pass'] = negatives == 0
    except Exception as e:
        results['variable_cost_error'] = str(e)

    # Test 3: Revenue extraction
    try:
        data = await extract_timeseries_from_sql('revenue', min_points=6)
        results['revenue_points'] = len(data.points)
        results['revenue_pass'] = len(data.points) >= 6
    except Exception as e:
        results['revenue_error'] = str(e)

    # Print results
    print("\n=== Data Quality Verification ===")
    for key, value in results.items():
        status = "✓" if "pass" in key and value else "✗" if "pass" in key else " "
        print(f"{status} {key}: {value}")

    return results

if __name__ == "__main__":
    asyncio.run(verify_fixes())
```

---

## Summary

The most critical fix is **Fix 1: Remove SQL inline conversion**. This single change will:
1. Eliminate double-conversion bugs
2. Reduce EBITDA swing ratio from 28.7x to target <5x
3. Establish Python as the single source of truth for normalization

The Variable Cost issue is already handled correctly in the existing code. Other fixes are enhancements that improve data quality but are not blocking forecasting accuracy.
