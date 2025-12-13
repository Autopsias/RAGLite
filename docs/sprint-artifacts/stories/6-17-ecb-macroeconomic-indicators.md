# Story 6.17: Add ECB Macroeconomic Indicators

Status: done

## Story

As a **system**,
I want **to extend the ECB client with GDP growth rate and HICP inflation**,
so that **forecasting can use macro indicators that affect construction demand and pricing**.

## Epic Reference

- **Epic:** 6 - Advanced Forecasting with External Data
- **Sprint Change Proposal:** SCP-2025-12-12-001
- **Priority:** P1 (High)
- **Estimated Effort:** 4 hours

## Problem Statement

Current forecasting relies on energy prices (TTF gas, API2 coal, diesel) and interest rates (EURIBOR) for external regressors. While these are valuable, the cement industry is also significantly impacted by broader macroeconomic conditions:

**Missing Macro Indicators:**
1. **GDP Growth Rate**: Economic expansion/contraction directly correlates with construction activity and infrastructure investment
2. **HICP Inflation**: Consumer price inflation affects material costs, wages, and pricing strategies

**Impact:**
- Revenue and Sales Volume forecasting lacks demand-side economic context
- Average Selling Price forecasting missing inflation drivers
- Variable Cost forecasting needs broader economic indicators beyond energy

**Current ECB Client Capabilities (from ecb.py):**
- EURIBOR rates (3M, 6M, 12M) - implemented
- GDP growth and HICP - NOT YET IMPLEMENTED

## Acceptance Criteria

### AC1: GDP Growth Rate API

**Given** a request for Portugal GDP growth data
**When** `fetch_gdp_growth()` is called with date range 2020-2025
**Then** the function returns quarterly YoY growth rates for Portugal

**Verification:**
```python
client = ECBClient()
data = await client.fetch_gdp_growth(
    country="PT",
    start_date=date(2020, 1, 1),
    end_date=date(2025, 12, 31)
)
assert len(data) >= 16, "Need at least 4 years of quarterly data"
assert all(d.country == "PT" for d in data)
assert all(-20.0 <= d.growth_pct <= 20.0 for d in data)  # Reasonable YoY range
```

**API Reference:**
```
ECB Statistical Data Warehouse (SDW):
Dataset: MNA (National accounts)
Series: Quarterly GDP growth, YoY percentage change

Example request:
GET /data/MNA/Q.Y.PT.W2.S1.S1.B.B1GQ._Z._Z._Z.XDC_R_B1GQ_Y.V.N?format=csvdata

Dimension breakdown:
- Q = Quarterly frequency
- Y = Year-on-year growth rate
- PT = Portugal
- W2.S1.S1.B.B1GQ = GDP at market prices (B1GQ)
- XDC_R_B1GQ_Y = Growth rate of real GDP
```

### AC2: HICP Inflation API

**Given** a request for Portugal HICP inflation data
**When** `fetch_inflation()` is called with date range 2020-2025
**Then** the function returns monthly HICP index values for Portugal

**Verification:**
```python
client = ECBClient()
data = await client.fetch_inflation(
    country="PT",
    start_date=date(2020, 1, 1),
    end_date=date(2025, 12, 31)
)
assert len(data) >= 48, "Need at least 4 years of monthly data"
assert all(d.country == "PT" for d in data)
assert all(80.0 <= d.index_value <= 150.0 for d in data)  # Reasonable index range
```

**API Reference:**
```
ECB Statistical Data Warehouse (SDW):
Dataset: ICP (HICP - Harmonised Index of Consumer Prices)
Series: Monthly HICP index (2015=100)

Example request:
GET /data/ICP/M.PT.N.000000.4.INX?format=csvdata

Dimension breakdown:
- M = Monthly frequency
- PT = Portugal
- N = Neither seasonally nor working day adjusted
- 000000 = All items (overall HICP)
- 4 = Index
- INX = Index level
```

### AC3: Quarterly GDP Interpolation to Monthly

**Given** quarterly GDP growth data
**When** aligning with monthly forecasting regressors
**Then** quarterly values are interpolated to monthly frequency

**Verification:**
```python
# Quarterly data: Q1 2024 = 2.5%
# Monthly interpolation: Jan=2.5%, Feb=2.5%, Mar=2.5% (constant within quarter)
# OR linear interpolation between quarters

quarterly_data = [
    GDPGrowth(date=date(2024, 1, 1), growth_pct=2.5),
    GDPGrowth(date=date(2024, 4, 1), growth_pct=2.8),
]
monthly_data = interpolate_quarterly_to_monthly(quarterly_data)
assert len(monthly_data) == 6  # 6 months for 2 quarters
assert all(m.date.day == 1 for m in monthly_data)
```

**Interpolation Strategy:**
- **Constant within quarter**: Each month in quarter gets same value (simplest)
- **Linear interpolation**: Smooth transition between quarters (more accurate)
- **Implementation**: Use constant interpolation initially, can enhance later

### AC4: Unit Tests for ECB SDW Parsing

**Given** mock ECB API responses in CSV format
**When** running unit tests for GDP and HICP parsing
**Then** all tests pass with correct data extraction

**Verification:**
```bash
uv run pytest tests/unit/test_ecb_macroeconomic.py -v
# Expected: All tests pass
```

## Tasks / Subtasks

### Task 1: Create Data Models (AC: 1, 2)

- [ ] **1.1** Add `GDPGrowth` dataclass to `raglite/external_data/clients/ecb.py`:
  ```python
  @dataclass
  class GDPGrowth:
      """GDP growth rate data point."""
      date: date
      growth_pct: float  # YoY growth as percentage (e.g., 2.5 for 2.5%)
      country: str  # ISO 2-letter code (PT for Portugal)
      frequency: str = "Q"  # Q=Quarterly
  ```

- [ ] **1.2** Add `HICPInflation` dataclass to `raglite/external_data/clients/ecb.py`:
  ```python
  @dataclass
  class HICPInflation:
      """HICP inflation index data point."""
      date: date
      index_value: float  # HICP index (2015=100)
      yoy_change_pct: float | None  # YoY % change (calculated)
      country: str  # ISO 2-letter code
  ```

### Task 2: Implement GDP Growth Fetching (AC: 1)

- [ ] **2.1** Add GDP series key constant to `ECBClient`:
  ```python
  # ECB SDMX series key for GDP growth
  # Q.Y.PT.W2.S1.S1.B.B1GQ._Z._Z._Z.XDC_R_B1GQ_Y.V.N
  GDP_SERIES = "Q.Y.PT.W2.S1.S1.B.B1GQ._Z._Z._Z.XDC_R_B1GQ_Y.V.N"
  ```

- [ ] **2.2** Implement `fetch_gdp_growth()` method:
  ```python
  async def fetch_gdp_growth(
      self,
      country: str = "PT",
      start_date: date | None = None,
      end_date: date | None = None,
  ) -> list[GDPGrowth]:
      """Fetch quarterly GDP growth rate from ECB SDW.

      Story 6.17 AC1: GDP growth for Portugal

      Dataset: MNA (National accounts)
      Coverage: Quarterly, 1999-present

      Args:
          country: ISO 2-letter country code (default: PT)
          start_date: Start of date range
          end_date: End of date range

      Returns:
          List of GDP growth rate records (quarterly frequency)
      """
  ```

- [ ] **2.3** Implement `_parse_gdp_csv()` parsing method

### Task 3: Implement HICP Inflation Fetching (AC: 2)

- [ ] **3.1** Add HICP series key constant to `ECBClient`:
  ```python
  # ECB SDMX series key for HICP inflation
  # M.PT.N.000000.4.INX
  HICP_SERIES = "M.PT.N.000000.4.INX"
  ```

- [ ] **3.2** Implement `fetch_inflation()` method:
  ```python
  async def fetch_inflation(
      self,
      country: str = "PT",
      start_date: date | None = None,
      end_date: date | None = None,
  ) -> list[HICPInflation]:
      """Fetch monthly HICP inflation index from ECB SDW.

      Story 6.17 AC2: HICP inflation for Portugal

      Dataset: ICP (HICP - Harmonised Index of Consumer Prices)
      Coverage: Monthly, 1996-present

      Args:
          country: ISO 2-letter country code (default: PT)
          start_date: Start of date range
          end_date: End of date range

      Returns:
          List of HICP inflation index records (monthly frequency)
      """
  ```

- [ ] **3.3** Implement `_parse_hicp_csv()` parsing method with YoY calculation

### Task 4: Implement Quarterly to Monthly Interpolation (AC: 3)

- [ ] **4.1** Add interpolation function to `ECBClient`:
  ```python
  def interpolate_quarterly_to_monthly(
      self,
      quarterly_data: list[GDPGrowth],
      method: str = "constant",  # "constant" or "linear"
  ) -> list[GDPGrowth]:
      """Interpolate quarterly GDP data to monthly frequency.

      Story 6.17 AC3: Quarterly to monthly alignment

      Args:
          quarterly_data: List of quarterly GDP records
          method: Interpolation method
              - "constant": Each month gets quarter's value
              - "linear": Linear interpolation between quarters

      Returns:
          List of monthly GDP records
      """
  ```

- [ ] **4.2** Implement constant interpolation (primary)
- [ ] **4.3** Implement linear interpolation (optional enhancement)

### Task 5: Register as Available Regressors (AC: 1, 2)

- [ ] **5.1** Add new regressors to `raglite/forecasting/regressor_config.py`:
  ```python
  AVAILABLE_REGRESSORS = {
      # ... existing regressors ...
      "gdp_growth": {
          "source": "ecb",
          "fetch_method": "fetch_gdp_growth",
          "description": "GDP growth rate YoY (quarterly → monthly)",
          "frequency": "monthly",  # After interpolation
          "unit": "percent",
      },
      "inflation": {
          "source": "ecb",
          "fetch_method": "fetch_inflation",
          "description": "HICP inflation index (2015=100)",
          "frequency": "monthly",
          "unit": "index",
      },
  }
  ```

- [ ] **5.2** Add fetch functions to `raglite/forecasting/regressor_fetch.py`

### Task 6: Create Unit Tests (AC: 4)

- [ ] **6.1** Create `tests/unit/test_ecb_macroeconomic.py`:
  ```python
  import pytest
  from datetime import date
  from raglite.external_data.clients.ecb import ECBClient, GDPGrowth, HICPInflation

  class TestECBGDPGrowth:
      """Unit tests for ECB GDP growth parsing."""

      def test_parse_gdp_period_quarterly(self):
          """Parse quarterly period format (YYYY-Q1/Q2/Q3/Q4)."""
          client = ECBClient()
          assert client._parse_ecb_period("2024-Q1") == date(2024, 1, 1)
          assert client._parse_ecb_period("2024-Q2") == date(2024, 4, 1)
          assert client._parse_ecb_period("2024-Q3") == date(2024, 7, 1)
          assert client._parse_ecb_period("2024-Q4") == date(2024, 10, 1)

      def test_parse_gdp_csv_valid(self):
          """Parse valid GDP growth CSV response."""
          mock_csv = '''KEY,TIME_PERIOD,OBS_VALUE
MNA.Q.Y.PT...,2024-Q1,2.5
MNA.Q.Y.PT...,2024-Q2,2.8
MNA.Q.Y.PT...,2024-Q3,2.1'''
          client = ECBClient()
          result = client._parse_gdp_csv(mock_csv, "PT", None, None)
          assert len(result) == 3
          assert result[0].growth_pct == 2.5
          assert result[0].country == "PT"

      def test_interpolate_quarterly_to_monthly_constant(self):
          """Constant interpolation assigns quarter value to all months."""
          client = ECBClient()
          quarterly = [
              GDPGrowth(date=date(2024, 1, 1), growth_pct=2.5, country="PT"),
              GDPGrowth(date=date(2024, 4, 1), growth_pct=2.8, country="PT"),
          ]
          monthly = client.interpolate_quarterly_to_monthly(quarterly, method="constant")
          assert len(monthly) == 6
          # Q1 months all get 2.5%
          assert monthly[0].growth_pct == 2.5  # Jan
          assert monthly[2].growth_pct == 2.5  # Mar
          # Q2 months all get 2.8%
          assert monthly[3].growth_pct == 2.8  # Apr

  class TestECBInflation:
      """Unit tests for ECB HICP inflation parsing."""

      def test_parse_hicp_csv_valid(self):
          """Parse valid HICP CSV response."""
          mock_csv = '''KEY,TIME_PERIOD,OBS_VALUE
ICP.M.PT...,2024-01,120.5
ICP.M.PT...,2024-02,121.2
ICP.M.PT...,2024-03,121.8'''
          client = ECBClient()
          result = client._parse_hicp_csv(mock_csv, "PT", None, None)
          assert len(result) == 3
          assert result[0].index_value == 120.5
          assert result[0].country == "PT"

      def test_hicp_yoy_calculation(self):
          """YoY change calculated when 12 months of data available."""
          # Test with 13 months of data to verify YoY calculation
          pass
  ```

### Task 7: Create Integration Tests (AC: 1, 2)

- [ ] **7.1** Create `tests/integration/test_ecb_macroeconomic_integration.py`:
  ```python
  import pytest
  from datetime import date
  from raglite.external_data.clients.ecb import ECBClient

  @pytest.mark.integration
  @pytest.mark.slow
  class TestECBMacroeconomicIntegration:
      """Integration tests for ECB macroeconomic indicators."""

      @pytest.mark.asyncio
      async def test_fetch_gdp_growth_portugal(self):
          """AC1: Fetch GDP growth for Portugal."""
          client = ECBClient()
          data = await client.fetch_gdp_growth(
              country="PT",
              start_date=date(2020, 1, 1),
              end_date=date(2024, 12, 31)
          )
          assert len(data) >= 16, f"Expected 16+ quarters, got {len(data)}"
          assert all(d.country == "PT" for d in data)

      @pytest.mark.asyncio
      async def test_fetch_inflation_portugal(self):
          """AC2: Fetch HICP inflation for Portugal."""
          client = ECBClient()
          data = await client.fetch_inflation(
              country="PT",
              start_date=date(2020, 1, 1),
              end_date=date(2024, 12, 31)
          )
          assert len(data) >= 48, f"Expected 48+ months, got {len(data)}"
          assert all(d.country == "PT" for d in data)

      @pytest.mark.asyncio
      async def test_gdp_interpolation_produces_monthly(self):
          """AC3: Quarterly GDP interpolated to monthly."""
          client = ECBClient()
          quarterly = await client.fetch_gdp_growth(
              country="PT",
              start_date=date(2022, 1, 1),
              end_date=date(2023, 12, 31)
          )
          monthly = client.interpolate_quarterly_to_monthly(quarterly)
          assert len(monthly) >= 24  # 2 years of monthly data
  ```

## Dev Notes

### Architecture Reference

**Source:** `docs/architecture/6-external-data-pipeline-epic-6.md`

```
+------------------------+     +------------------------+
| ECB SDW API            |     | External Data Points   |
| - MNA (GDP growth)     |---->| PostgreSQL Table       |
| - ICP (HICP inflation) |     +------------------------+
+------------------------+              |
        |                               v
        v                      +------------------------+
+------------------------+     | Prophet Multi-Variate  |
| ECBClient (extended)   |     | - add_regressor()      |
| - fetch_gdp_growth()   |---->| External regressors    |
| - fetch_inflation()    |     +------------------------+
+------------------------+
```

### ECB SDW API Reference

**Base URL:** `https://data-api.ecb.europa.eu/service/data`

**Format:** CSV (csvdata) - consistent with existing EURIBOR implementation

**Datasets:**
| Code | Name | Frequency | Coverage |
|------|------|-----------|----------|
| `MNA` | National accounts (GDP) | Quarterly | 1999-present |
| `ICP` | HICP inflation | Monthly | 1996-present |

**GDP Series Key Breakdown:**
```
Q.Y.PT.W2.S1.S1.B.B1GQ._Z._Z._Z.XDC_R_B1GQ_Y.V.N
|  |  |   |          |              |
|  |  |   |          |              +-- XDC_R_B1GQ_Y = Growth rate
|  |  |   |          +-- B1GQ = GDP at market prices
|  |  |   +-- W2.S1.S1.B = Sector classification
|  |  +-- PT = Portugal
|  +-- Y = Year-on-year
+-- Q = Quarterly
```

**HICP Series Key Breakdown:**
```
M.PT.N.000000.4.INX
|  |  |   |    |  |
|  |  |   |    |  +-- INX = Index level
|  |  |   |    +-- 4 = Index type
|  |  |   +-- 000000 = All items (overall HICP)
|  |  +-- N = Not seasonally adjusted
|  +-- PT = Portugal
+-- M = Monthly
```

### Files to Modify

| File | Changes |
|------|---------|
| `raglite/external_data/clients/ecb.py` | Add `fetch_gdp_growth()`, `fetch_inflation()`, interpolation |
| `raglite/forecasting/regressor_config.py` | Add gdp_growth, inflation regressors |
| `raglite/forecasting/regressor_fetch.py` | Add fetch functions for new regressors |

### Files to Create

| File | Purpose |
|------|---------|
| `tests/unit/test_ecb_macroeconomic.py` | Unit tests for GDP/HICP parsing |
| `tests/integration/test_ecb_macroeconomic_integration.py` | Integration tests |

### Existing Code Patterns (from ecb.py)

The current `ECBClient` (lines 1-283) already implements:
- `_fetch_series()` - Generic SDMX API fetch with retry logic
- `_parse_euribor_csv()` - CSV parsing for EURIBOR data
- File-based caching via `ExternalDataCache`
- Proper error handling with `ExternalDataFetchError`
- Structured logging with `get_logger()`

**CRITICAL: Follow the existing EURIBOR implementation pattern exactly!**

Key patterns to replicate:
1. Use `_fetch_series()` for API calls (handles retries and errors)
2. Parse CSV response with `csv.DictReader`
3. Cache results with `self._cache.set()`
4. Log parsing results with structured logging

### Period Parsing Enhancement

The existing `_parse_euribor_csv` only handles monthly periods (YYYY-MM). For GDP data, we need to handle quarterly periods (YYYY-Qn):

```python
def _parse_ecb_period(self, period: str) -> date:
    """Parse ECB period string to date.

    Handles:
    - Monthly: "2024-01" -> date(2024, 1, 1)
    - Quarterly: "2024-Q1" -> date(2024, 1, 1)
    """
    if "-Q" in period:
        year = int(period[:4])
        quarter = int(period[-1])
        month = (quarter - 1) * 3 + 1  # Q1=1, Q2=4, Q3=7, Q4=10
        return date(year, month, 1)
    else:
        year, month = int(period[:4]), int(period[5:7])
        return date(year, month, 1)
```

### Interpolation Strategy

**Constant Interpolation (Recommended for MVP):**
- Simple: Each month in quarter gets the quarter's value
- Accurate enough for forecasting (changes are gradual)
- Implementation: 3 months per quarter, same value each

**Linear Interpolation (Future Enhancement):**
- Smoother transitions between quarters
- More complex: requires handling edge cases
- Consider for future if validation shows issues

### Cement Industry Relevance

**GDP Growth Rate:**
- Leading indicator of construction demand
- Economic expansion -> more infrastructure projects
- High correlation expected with Sales Volume, Revenue

**HICP Inflation:**
- Affects material costs (cement raw materials)
- Impacts pricing decisions (Average Selling Price)
- Wage inflation affects labor costs (Variable Cost)

### Testing Considerations

**Unit Tests:**
- Mock ECB CSV responses (don't hit real API)
- Test period parsing for both monthly and quarterly formats
- Test interpolation logic with known inputs
- Test edge cases: empty data, missing values, malformed CSV

**Integration Tests:**
- Use `@pytest.mark.slow` for API-dependent tests
- Use `@pytest.mark.integration` marker
- Test actual API responses (verify data quality)
- Test caching behavior

### Performance Considerations

- ECB API typically responds in 1-3 seconds
- Use existing retry logic (3 attempts, exponential backoff)
- Cache results for 24 hours (same as EURIBOR)
- GDP data is quarterly, so less frequent updates needed

### Error Handling

Follow existing patterns:
- Raise `ExternalDataFetchError` on permanent failures
- Log warnings for parsing errors
- Skip invalid records rather than fail entire fetch
- Return empty list if no data (don't raise for empty results)

## Project Structure Notes

### Alignment with Repository Structure

- Extend existing `ecb.py` client (not create new file)
- No new data models file needed (add to ecb.py)
- Tests follow `tests/unit/` and `tests/integration/` patterns
- No new dependencies required (uses existing httpx)

### Detected Conflicts

None - this story extends existing ECB client following established patterns.

## Prerequisites

**Dependencies:** None - this story can be implemented independently

**Required Knowledge:**
- ECB SDW API structure (different series keys than EURIBOR)
- Existing ECBClient patterns in codebase (EURIBOR implementation)
- Quarterly to monthly data alignment concepts

## References

- [Source: docs/prd/epic-6-advanced-forecasting-external-data.md#Story 6.17]
- [Source: docs/sprint-change-proposals/2025-12-12-epic-6-forecasting-accuracy-extension.md]
- [Source: raglite/external_data/clients/ecb.py - existing EURIBOR implementation]
- [ECB SDW API: https://data.ecb.europa.eu/help/api/overview]
- [ECB GDP Data: https://data.ecb.europa.eu/data/datasets/MNA]
- [ECB HICP Data: https://data.ecb.europa.eu/data/datasets/ICP]

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

### File List

- `raglite/external_data/clients/ecb.py` - Modified (add GDP, HICP methods)
- `raglite/forecasting/regressor_config.py` - Modified (register regressors)
- `raglite/forecasting/regressor_fetch.py` - Modified (add fetch functions)
- `tests/unit/test_ecb_macroeconomic.py` - New (unit tests)
- `tests/integration/test_ecb_macroeconomic_integration.py` - New (integration tests)
