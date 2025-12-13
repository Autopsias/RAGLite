# ATDD Checklist: Story 6.17 - ECB Macroeconomic Indicators

**Story:** 6.17 Add ECB Macroeconomic Indicators
**Status:** RED Phase (Tests created, implementation pending)
**Generated:** 2025-12-13

## Overview

This checklist maps acceptance criteria to their corresponding tests. All tests are in the RED phase - they MUST fail until implementation is complete.

---

## Acceptance Criteria to Test Mapping

### AC1: GDP Growth Rate API

**Criterion:** `fetch_gdp_growth()` returns quarterly YoY growth for Portugal

| Test ID | Test Name | File | Status |
|---------|-----------|------|--------|
| AC1-U01 | `test_ac1_gdp_growth_dataclass_exists` | `test_ecb_macroeconomic.py` | RED |
| AC1-U02 | `test_ac1_gdp_growth_default_frequency` | `test_ecb_macroeconomic.py` | RED |
| AC1-U03 | `test_ac1_gdp_series_key_exists` | `test_ecb_macroeconomic.py` | RED |
| AC1-U04 | `test_ac1_fetch_gdp_growth_method_exists` | `test_ecb_macroeconomic.py` | RED |
| AC1-I01 | `test_ac1_fetch_gdp_growth_portugal_four_years` | `test_ecb_macroeconomic_integration.py` | RED |
| AC1-I02 | `test_ac1_fetch_gdp_growth_returns_quarterly_frequency` | `test_ecb_macroeconomic_integration.py` | RED |
| AC1-I03 | `test_ac1_fetch_gdp_growth_dates_are_quarter_starts` | `test_ecb_macroeconomic_integration.py` | RED |
| AC1-I04 | `test_ac1_fetch_gdp_growth_handles_covid_recession` | `test_ecb_macroeconomic_integration.py` | RED |
| AC1-I05 | `test_ac1_fetch_gdp_growth_uses_caching` | `test_ecb_macroeconomic_integration.py` | RED |

**Verification Query (from story):**
```python
client = ECBClient()
data = await client.fetch_gdp_growth(
    country="PT",
    start_date=date(2020, 1, 1),
    end_date=date(2025, 12, 31)
)
assert len(data) >= 16, "Need at least 4 years of quarterly data"
assert all(d.country == "PT" for d in data)
assert all(-20.0 <= d.growth_pct <= 20.0 for d in data)
```

---

### AC2: HICP Inflation API

**Criterion:** `fetch_inflation()` returns monthly HICP for Portugal

| Test ID | Test Name | File | Status |
|---------|-----------|------|--------|
| AC2-U01 | `test_ac2_inflation_dataclass_exists` | `test_ecb_macroeconomic.py` | RED |
| AC2-U02 | `test_ac2_inflation_yoy_optional` | `test_ecb_macroeconomic.py` | RED |
| AC2-U03 | `test_ac2_hicp_series_key_exists` | `test_ecb_macroeconomic.py` | RED |
| AC2-U04 | `test_ac2_fetch_inflation_method_exists` | `test_ecb_macroeconomic.py` | RED |
| AC2-I01 | `test_ac2_fetch_inflation_portugal_four_years` | `test_ecb_macroeconomic_integration.py` | RED |
| AC2-I02 | `test_ac2_fetch_inflation_index_in_reasonable_range` | `test_ecb_macroeconomic_integration.py` | RED |
| AC2-I03 | `test_ac2_fetch_inflation_monthly_frequency` | `test_ecb_macroeconomic_integration.py` | RED |
| AC2-I04 | `test_ac2_fetch_inflation_yoy_calculation` | `test_ecb_macroeconomic_integration.py` | RED |
| AC2-I05 | `test_ac2_fetch_inflation_2022_inflation_spike` | `test_ecb_macroeconomic_integration.py` | RED |

**Verification Query (from story):**
```python
client = ECBClient()
data = await client.fetch_inflation(
    country="PT",
    start_date=date(2020, 1, 1),
    end_date=date(2025, 12, 31)
)
assert len(data) >= 48, "Need at least 4 years of monthly data"
assert all(d.country == "PT" for d in data)
assert all(80.0 <= d.index_value <= 150.0 for d in data)
```

---

### AC3: Quarterly GDP Interpolation to Monthly

**Criterion:** Quarterly values interpolated to monthly frequency for regressor alignment

| Test ID | Test Name | File | Status |
|---------|-----------|------|--------|
| AC3-U01 | `test_ac3_interpolate_constant_method` | `test_ecb_macroeconomic.py` | RED |
| AC3-U02 | `test_ac3_interpolate_preserves_country` | `test_ecb_macroeconomic.py` | RED |
| AC3-U03 | `test_ac3_interpolate_changes_frequency` | `test_ecb_macroeconomic.py` | RED |
| AC3-U04 | `test_ac3_interpolate_empty_list` | `test_ecb_macroeconomic.py` | RED |
| AC3-U05 | `test_ac3_interpolate_single_quarter` | `test_ecb_macroeconomic.py` | RED |
| AC3-U06 | `test_ac3_interpolate_full_year` | `test_ecb_macroeconomic.py` | RED |
| AC3-U07 | `test_ac3_interpolate_default_method_is_constant` | `test_ecb_macroeconomic.py` | RED |
| AC3-U08 | `test_ac3_interpolate_method_exists` | `test_ecb_macroeconomic.py` | RED |
| AC3-I01 | `test_ac3_interpolation_produces_correct_monthly_count` | `test_ecb_macroeconomic_integration.py` | RED |
| AC3-I02 | `test_ac3_interpolation_all_months_present` | `test_ecb_macroeconomic_integration.py` | RED |
| AC3-I03 | `test_ac3_interpolation_ready_for_prophet` | `test_ecb_macroeconomic_integration.py` | RED |

**Verification Query (from story):**
```python
quarterly_data = [
    GDPGrowth(date=date(2024, 1, 1), growth_pct=2.5),
    GDPGrowth(date=date(2024, 4, 1), growth_pct=2.8),
]
monthly_data = interpolate_quarterly_to_monthly(quarterly_data)
assert len(monthly_data) == 6  # 6 months for 2 quarters
assert all(m.date.day == 1 for m in monthly_data)
```

---

### AC4: Unit Tests for ECB SDW Parsing

**Criterion:** Unit tests verify ECB SDW parsing

| Test ID | Test Name | File | Status |
|---------|-----------|------|--------|
| AC4-U01 | `test_ac4_parse_quarterly_period_q1` | `test_ecb_macroeconomic.py` | RED |
| AC4-U02 | `test_ac4_parse_quarterly_period_q2` | `test_ecb_macroeconomic.py` | RED |
| AC4-U03 | `test_ac4_parse_quarterly_period_q3` | `test_ecb_macroeconomic.py` | RED |
| AC4-U04 | `test_ac4_parse_quarterly_period_q4` | `test_ecb_macroeconomic.py` | RED |
| AC4-U05 | `test_ac4_parse_monthly_period` | `test_ecb_macroeconomic.py` | RED |
| AC4-U06 | `test_ac4_parse_gdp_csv_valid` | `test_ecb_macroeconomic.py` | RED |
| AC4-U07 | `test_ac4_parse_gdp_csv_empty_response` | `test_ecb_macroeconomic.py` | RED |
| AC4-U08 | `test_ac4_parse_gdp_csv_skip_invalid_rows` | `test_ecb_macroeconomic.py` | RED |
| AC4-U09 | `test_ac4_parse_gdp_csv_negative_growth` | `test_ecb_macroeconomic.py` | RED |
| AC4-U10 | `test_ac4_parse_hicp_csv_valid` | `test_ecb_macroeconomic.py` | RED |
| AC4-U11 | `test_ac4_parse_hicp_csv_with_yoy_calculation` | `test_ecb_macroeconomic.py` | RED |
| AC4-U12 | `test_ac4_parse_hicp_csv_empty` | `test_ecb_macroeconomic.py` | RED |

**Verification Command:**
```bash
uv run pytest tests/unit/test_ecb_macroeconomic.py -v
# Expected: All tests pass (after implementation)
```

---

## Test Files Summary

| File | Location | Test Count | Purpose |
|------|----------|------------|---------|
| `test_ecb_macroeconomic.py` | `tests/unit/` | 27 | Unit tests for models, parsing, interpolation |
| `test_ecb_macroeconomic_integration.py` | `tests/integration/` | 16 | Integration tests for API calls, pipelines |

**Total Tests Created:** 43

---

## Test Run Commands

```bash
# Run all tests for Story 6.17 (expected: ALL FAIL in RED phase)
uv run pytest tests/unit/test_ecb_macroeconomic.py tests/integration/test_ecb_macroeconomic_integration.py -v

# Run unit tests only
uv run pytest tests/unit/test_ecb_macroeconomic.py -v

# Run integration tests only (mocked)
uv run pytest tests/integration/test_ecb_macroeconomic_integration.py -v -m "not slow"

# Run real API tests (slow, requires network)
uv run pytest tests/integration/test_ecb_macroeconomic_integration.py -v -m "slow and external_api"
```

---

## Implementation Imports Required

The tests expect these imports from `raglite.external_data.clients.ecb`:

```python
from raglite.external_data.clients.ecb import (
    ECBClient,                          # Existing class (to be extended)
    ECBGDPGrowth,                       # New: GDP growth dataclass
    ECBInflation,                       # New: HICP inflation dataclass
    interpolate_quarterly_to_monthly,   # New: Interpolation function
)
```

---

## Expected Methods to Implement

### ECBClient Extensions

1. **`fetch_gdp_growth()`**
   - Parameters: `country: str = "PT"`, `start_date: date | None = None`, `end_date: date | None = None`
   - Returns: `list[ECBGDPGrowth]`

2. **`fetch_inflation()`**
   - Parameters: `country: str = "PT"`, `start_date: date | None = None`, `end_date: date | None = None`
   - Returns: `list[ECBInflation]`

3. **`_parse_ecb_period()`**
   - Parameters: `period: str`
   - Returns: `date`
   - Handles: Monthly ("2024-01") and Quarterly ("2024-Q1") formats

4. **`_parse_gdp_csv()`**
   - Parameters: `csv_data: str`, `country: str`
   - Returns: `list[ECBGDPGrowth]`

5. **`_parse_hicp_csv()`**
   - Parameters: `csv_data: str`, `country: str`
   - Returns: `list[ECBInflation]`

### Module-Level Function

6. **`interpolate_quarterly_to_monthly()`**
   - Parameters: `quarterly_data: list[ECBGDPGrowth]`, `method: str = "constant"`
   - Returns: `list[ECBGDPGrowth]`

---

## TDD Cycle Status

| Phase | Status | Notes |
|-------|--------|-------|
| RED | CURRENT | All 43 tests fail (import errors expected) |
| GREEN | PENDING | Implement to make tests pass |
| REFACTOR | PENDING | Clean up implementation |

---

## Next Steps

1. **Verify RED phase:** Run tests to confirm all fail with import errors
2. **Implement dataclasses:** `ECBGDPGrowth`, `ECBInflation`
3. **Implement parsing:** `_parse_ecb_period`, `_parse_gdp_csv`, `_parse_hicp_csv`
4. **Implement fetching:** `fetch_gdp_growth`, `fetch_inflation`
5. **Implement interpolation:** `interpolate_quarterly_to_monthly`
6. **Verify GREEN phase:** All tests pass
7. **REFACTOR:** Clean up, add documentation
