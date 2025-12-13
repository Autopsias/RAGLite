# Story 6.16: Add Eurostat Construction & Industrial Indicators

Status: ready-for-dev

## Story

As a **system**,
I want **to extend the Eurostat client with construction output index and industrial production index**,
so that **forecasting can use high-correlation leading indicators for cement demand**.

## Epic Reference

- **Epic:** 6 - Advanced Forecasting with External Data
- **Sprint Change Proposal:** SCP-2025-12-12-001
- **Priority:** P1 (High)
- **Estimated Effort:** 8 hours

## Problem Statement

Current forecasting uses generic macro-economic indicators (EURIBOR, diesel prices) that have limited correlation with cement demand. The cement industry is highly correlated with construction activity and industrial production, but these indicators are not yet available in the regressor ecosystem.

**Missing Regressors:**
1. **Construction Output Index (sts_copr_m)**: Measures actual construction sector output - direct driver of cement demand
2. **Industrial Production Index (sts_inpr_m)**: Measures manufacturing activity - correlates with infrastructure and industrial projects

**Impact:**
- Variable Cost MAPE at 41.43% (target <8%)
- Sales Volume forecasting lacks construction sector context
- Revenue forecasting missing demand-side indicators

## Acceptance Criteria

### AC1: Construction Output Index API

**Given** a request for Portugal construction output data
**When** `fetch_construction_output()` is called with date range 2020-2025
**Then** the function returns monthly index values for Portugal (geo=PT)

**Verification:**
```python
client = EurostatClient()
data = await client.fetch_construction_output(
    country="PT",
    start_date=date(2020, 1, 1),
    end_date=date(2025, 12, 31)
)
assert len(data) >= 48, "Need at least 4 years of monthly data"
assert all(d.country == "PT" for d in data)
assert all(d.index_value > 0 for d in data)  # Index values positive
assert data[0].date >= date(2020, 1, 1)
```

**API Reference:**
```
Eurostat SDMX API:
Dataset: sts_copr_m (Short-term business statistics: Production in construction)
URL: https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/sts_copr_m
Filters:
  - geo=PT (Portugal)
  - unit=I21 (Index 2021=100)
  - s_adj=SCA (Seasonally and calendar adjusted)
  - nace_r2=F (Construction sector NACE Rev. 2)
```

### AC2: Industrial Production Index API

**Given** a request for Portugal industrial production data
**When** `fetch_industrial_production()` is called with date range 2020-2025
**Then** the function returns monthly index values for Portugal (geo=PT)

**Verification:**
```python
client = EurostatClient()
data = await client.fetch_industrial_production(
    country="PT",
    start_date=date(2020, 1, 1),
    end_date=date(2025, 12, 31)
)
assert len(data) >= 48, "Need at least 4 years of monthly data"
assert all(d.country == "PT" for d in data)
assert all(d.index_value > 0 for d in data)  # Index values positive
```

**API Reference:**
```
Eurostat SDMX API:
Dataset: sts_inpr_m (Industrial production)
URL: https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/sts_inpr_m
Filters:
  - geo=PT (Portugal)
  - unit=I21 (Index 2021=100)
  - s_adj=SCA (Seasonally and calendar adjusted)
  - nace_r2=B-D (Mining, manufacturing, energy)
```

### AC3: Correlation with Sales Volume

**Given** the construction output and industrial production time series
**When** calculating Pearson correlation with sales_volume
**Then** both indicators show >0.3 correlation coefficient

**Verification:**
```python
import numpy as np
from scipy.stats import pearsonr

# Get construction output and sales volume aligned by date
construction = [d.index_value for d in construction_data]
sales = [d.value for d in sales_volume_data]

corr, p_value = pearsonr(construction, sales)
assert corr > 0.3, f"Correlation {corr:.2f} below 0.3 threshold"
assert p_value < 0.05, "Correlation not statistically significant"
```

### AC4: Data Quality - Missing Values

**Given** the fetched indicator data for 2020-2025 (60 months)
**When** analyzing data completeness
**Then** missing values are <10% of the analysis period

**Verification:**
```python
expected_months = 60  # 5 years * 12 months
actual_count = len(data)
missing_pct = (expected_months - actual_count) / expected_months * 100
assert missing_pct < 10, f"Missing {missing_pct:.1f}% exceeds 10% threshold"
```

### AC5: Unit Tests for Parsing and Data Quality

**Given** mock Eurostat API responses
**When** running unit tests for construction/industrial parsing
**Then** all tests pass with correct data extraction

**Verification:**
```bash
uv run pytest tests/unit/test_eurostat_construction.py -v
# Expected: All tests pass
```

## Tasks / Subtasks

### Task 1: Create Data Models (AC: 1, 2)

- [ ] **1.1** Add `EurostatConstructionOutput` model to `raglite/external_data/models.py`:
  ```python
  @dataclass
  class EurostatConstructionOutput:
      date: date
      index_value: float  # Index 2021=100
      country: str  # ISO 2-letter code
      nace_sector: str  # NACE Rev. 2 sector code
      seasonal_adjustment: str  # SCA, NSA, etc.
  ```

- [ ] **1.2** Add `EurostatIndustrialProduction` model to `raglite/external_data/models.py`:
  ```python
  @dataclass
  class EurostatIndustrialProduction:
      date: date
      index_value: float  # Index 2021=100
      country: str  # ISO 2-letter code
      nace_sector: str  # NACE Rev. 2 sector code
      seasonal_adjustment: str  # SCA, NSA, etc.
  ```

- [ ] **1.3** Export new models in `__init__.py`

### Task 2: Implement Construction Output Fetching (AC: 1)

- [ ] **2.1** Add dataset constant to `EurostatClient`:
  ```python
  CONSTRUCTION_DATASET = "sts_copr_m"  # Construction production index
  ```

- [ ] **2.2** Implement `fetch_construction_output()` method:
  ```python
  async def fetch_construction_output(
      self,
      country: str = "PT",
      start_date: date | None = None,
      end_date: date | None = None,
      nace_sector: str = "F",  # Construction sector
      seasonal_adjustment: str = "SCA",
  ) -> list[EurostatConstructionOutput]:
      """Fetch monthly construction output index from Eurostat.

      Story 6.16 AC1: Construction production index

      Dataset: sts_copr_m (Short-term statistics: Production in construction)
      Coverage: Monthly, 2000-present

      Args:
          country: ISO 2-letter country code (default: PT)
          start_date: Start of date range
          end_date: End of date range
          nace_sector: NACE Rev. 2 sector (default: F = Construction)
          seasonal_adjustment: Adjustment type (SCA, NSA, WDA)

      Returns:
          List of construction output index records
      """
  ```

- [ ] **2.3** Implement `_parse_construction_data()` parsing method

### Task 3: Implement Industrial Production Fetching (AC: 2)

- [ ] **3.1** Add dataset constant to `EurostatClient`:
  ```python
  INDUSTRIAL_PRODUCTION_DATASET = "sts_inpr_m"  # Industrial production index
  ```

- [ ] **3.2** Implement `fetch_industrial_production()` method:
  ```python
  async def fetch_industrial_production(
      self,
      country: str = "PT",
      start_date: date | None = None,
      end_date: date | None = None,
      nace_sector: str = "B-D",  # Mining, manufacturing, energy
      seasonal_adjustment: str = "SCA",
  ) -> list[EurostatIndustrialProduction]:
      """Fetch monthly industrial production index from Eurostat.

      Story 6.16 AC2: Industrial production index

      Dataset: sts_inpr_m (Industrial production)
      Coverage: Monthly, 2000-present

      Args:
          country: ISO 2-letter country code (default: PT)
          start_date: Start of date range
          end_date: End of date range
          nace_sector: NACE Rev. 2 sector (default: B-D)
          seasonal_adjustment: Adjustment type (SCA, NSA, WDA)

      Returns:
          List of industrial production index records
      """
  ```

- [ ] **3.3** Implement `_parse_industrial_data()` parsing method

### Task 4: Register as Available Regressors (AC: 3)

- [ ] **4.1** Add new regressors to `raglite/forecasting/regressor_config.py`:
  ```python
  AVAILABLE_REGRESSORS = {
      # ... existing regressors ...
      "construction_output": {
          "source": "eurostat",
          "fetch_method": "fetch_construction_output",
          "description": "Construction production index (NACE F)",
          "frequency": "monthly",
          "unit": "index_2021_100",
      },
      "industrial_production": {
          "source": "eurostat",
          "fetch_method": "fetch_industrial_production",
          "description": "Industrial production index (NACE B-D)",
          "frequency": "monthly",
          "unit": "index_2021_100",
      },
  }
  ```

- [ ] **4.2** Add fetch functions to `raglite/forecasting/regressor_fetch.py`

### Task 5: Create Unit Tests (AC: 5)

- [ ] **5.1** Create `tests/unit/test_eurostat_construction.py`:
  ```python
  import pytest
  from datetime import date
  from raglite.external_data.clients.eurostat import EurostatClient

  class TestEurostatConstructionOutput:
      """Unit tests for Eurostat construction output index."""

      def test_parse_construction_period_monthly(self):
          """Parse monthly period format."""
          client = EurostatClient()
          result = client._parse_eurostat_period("2024-01")
          assert result == date(2024, 1, 1)

      def test_parse_construction_data_valid(self):
          """Parse valid construction response."""
          mock_response = {
              "value": {"0": 105.2, "1": 106.8, "2": 104.5},
              "dimension": {
                  "time": {
                      "category": {
                          "index": {"2024-01": 0, "2024-02": 1, "2024-03": 2}
                      }
                  }
              }
          }
          client = EurostatClient()
          result = client._parse_construction_data(
              mock_response, "PT", "F", "SCA", None, None
          )
          assert len(result) == 3
          assert result[0].index_value == 105.2

      def test_construction_date_filtering(self):
          """Date filters are applied correctly."""
          # Test with start_date and end_date filters
          pass
  ```

- [ ] **5.2** Add industrial production unit tests

### Task 6: Create Integration Tests (AC: 3, 4)

- [ ] **6.1** Create `tests/integration/test_eurostat_construction_integration.py`:
  ```python
  import pytest
  from datetime import date
  from scipy.stats import pearsonr
  from raglite.external_data.clients.eurostat import EurostatClient

  @pytest.mark.integration
  class TestEurostatConstructionIntegration:
      """Integration tests for Eurostat construction indicators."""

      @pytest.mark.asyncio
      async def test_fetch_construction_output_portugal(self):
          """AC1: Fetch construction output for Portugal."""
          client = EurostatClient()
          data = await client.fetch_construction_output(
              country="PT",
              start_date=date(2020, 1, 1),
              end_date=date(2024, 12, 31)
          )
          assert len(data) >= 48
          assert all(d.country == "PT" for d in data)

      @pytest.mark.asyncio
      async def test_data_completeness_under_10_percent_missing(self):
          """AC4: Data has <10% missing values."""
          client = EurostatClient()
          data = await client.fetch_construction_output(
              country="PT",
              start_date=date(2020, 1, 1),
              end_date=date(2024, 12, 31)
          )
          expected_months = 60
          missing_pct = (expected_months - len(data)) / expected_months * 100
          assert missing_pct < 10
  ```

- [ ] **6.2** Add correlation test with sales_volume data

### Task 7: Documentation and Validation (AC: 1-5)

- [ ] **7.1** Update EurostatClient docstrings with new methods
- [ ] **7.2** Add API reference comments for dataset codes
- [ ] **7.3** Run full validation and document results

## Dev Notes

### Architecture Reference

**Source:** `docs/architecture/6-external-data-pipeline-epic-6.md#New Data Sources`

```
+------------------------+     +------------------------+
| Eurostat SDMX API      |     | External Data Points   |
| - sts_copr_m           |---->| PostgreSQL Table       |
| - sts_inpr_m           |     +------------------------+
+------------------------+              |
        |                               v
        v                      +------------------------+
+------------------------+     | Prophet Multi-Variate  |
| EurostatClient         |     | - add_regressor()      |
| - fetch_construction() |---->| External regressors    |
| - fetch_industrial()   |     +------------------------+
+------------------------+
```

### Eurostat SDMX API Reference

**Base URL:** `https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1`

**Datasets:**
| Code | Name | Frequency | Coverage |
|------|------|-----------|----------|
| `sts_copr_m` | Production in construction | Monthly | 2000-present |
| `sts_inpr_m` | Industrial production index | Monthly | 2000-present |

**Filter Parameters:**
| Parameter | Description | Values |
|-----------|-------------|--------|
| `geo` | Geographic area | PT (Portugal), EU27, etc. |
| `unit` | Unit of measure | I21 (Index 2021=100) |
| `s_adj` | Seasonal adjustment | SCA, NSA, WDA |
| `nace_r2` | NACE Rev. 2 sector | F (Construction), B-D (Industry) |

**Example Request:**
```
GET /data/sts_copr_m?geo=PT&unit=I21&s_adj=SCA&nace_r2=F&format=JSON
```

### Files to Modify

| File | Changes |
|------|---------|
| `raglite/external_data/clients/eurostat.py` | Add `fetch_construction_output()`, `fetch_industrial_production()` |
| `raglite/external_data/models.py` | Add `EurostatConstructionOutput`, `EurostatIndustrialProduction` |
| `raglite/forecasting/regressor_config.py` | Add new regressors |
| `raglite/forecasting/regressor_fetch.py` | Add fetch functions |

### Files to Create

| File | Purpose |
|------|---------|
| `tests/unit/test_eurostat_construction.py` | Unit tests for parsing |
| `tests/integration/test_eurostat_construction_integration.py` | Integration tests |

### Existing Code Patterns

The current `EurostatClient` (lines 31-325 of eurostat.py) already implements:
- `_fetch_with_retry()` - Retry logic with exponential backoff
- `_fetch_eurostat_data()` - Generic SDMX API fetch
- `_parse_eurostat_period()` - Period string parsing (YYYY-MM, YYYY-S1/S2)
- `fetch_electricity_prices()` - Example for similar indicator fetch

**Extend the existing client** following the electricity prices pattern.

### NACE Rev. 2 Sector Codes

| Code | Description | Relevance |
|------|-------------|-----------|
| **F** | Construction | Direct cement demand driver |
| **B-D** | Mining, Manufacturing, Energy | Industrial activity proxy |
| **C** | Manufacturing | Alternative for industrial |

### Seasonal Adjustment Types

| Code | Description | Recommended |
|------|-------------|-------------|
| **SCA** | Seasonally and calendar adjusted | Yes (default) |
| **NSA** | Not seasonally adjusted | No |
| **WDA** | Working day adjusted | Alternative |

### Performance Considerations

- Eurostat API has no rate limiting but may be slow (~2-5s response)
- Cache responses in PostgreSQL `external_data_points` table
- Refresh monthly (construction/industrial data updated monthly)
- Expected latency: <5s per fetch (well within NFR budget)

### Error Handling

Follow existing `EurostatClient` patterns:
- 3 retry attempts with exponential backoff (2s, 4s, 8s)
- Raise `ExternalDataFetchError` on permanent failure
- Log warnings for parsing errors
- Skip invalid records rather than fail entire fetch

## Project Structure Notes

### Alignment with Repository Structure

- Extend existing `eurostat.py` client (not create new file)
- Add models to existing `models.py`
- Tests follow `tests/unit/` and `tests/integration/` patterns
- No new dependencies required (uses existing httpx)

### Detected Conflicts

None - this story extends existing client without conflicting patterns.

## Testing Requirements

### Unit Tests (tests/unit/test_eurostat_construction.py)

```python
import pytest
from datetime import date
from unittest.mock import AsyncMock, patch
from raglite.external_data.clients.eurostat import EurostatClient
from raglite.external_data.models import EurostatConstructionOutput

class TestEurostatConstructionOutput:
    """Unit tests for Eurostat construction output index."""

    def test_parse_eurostat_period_monthly(self):
        """Parse monthly period format (YYYY-MM)."""
        client = EurostatClient()
        result = client._parse_eurostat_period("2024-01")
        assert result == date(2024, 1, 1)

    def test_parse_eurostat_period_semester(self):
        """Parse semester period format (YYYY-S1/S2)."""
        client = EurostatClient()
        assert client._parse_eurostat_period("2024-S1") == date(2024, 1, 1)
        assert client._parse_eurostat_period("2024-S2") == date(2024, 7, 1)

    def test_parse_construction_data_valid(self):
        """Parse valid construction output response."""
        mock_response = {
            "value": {"0": 105.2, "1": 106.8, "2": 104.5},
            "dimension": {
                "time": {
                    "category": {
                        "index": {"2024-01": 0, "2024-02": 1, "2024-03": 2}
                    }
                }
            }
        }
        client = EurostatClient()
        result = client._parse_construction_data(
            mock_response, "PT", "F", "SCA", None, None
        )
        assert len(result) == 3
        assert result[0].index_value == 105.2
        assert result[0].country == "PT"
        assert result[0].nace_sector == "F"

    def test_parse_construction_data_missing_values(self):
        """Handle missing values in response."""
        mock_response = {
            "value": {"0": 105.2, "2": 104.5},  # Missing index 1
            "dimension": {
                "time": {
                    "category": {
                        "index": {"2024-01": 0, "2024-02": 1, "2024-03": 2}
                    }
                }
            }
        }
        client = EurostatClient()
        result = client._parse_construction_data(
            mock_response, "PT", "F", "SCA", None, None
        )
        assert len(result) == 2  # Only 2 valid records

    def test_construction_date_filtering_start(self):
        """Filter by start_date."""
        mock_response = {
            "value": {"0": 100.0, "1": 101.0, "2": 102.0},
            "dimension": {
                "time": {
                    "category": {
                        "index": {"2024-01": 0, "2024-02": 1, "2024-03": 2}
                    }
                }
            }
        }
        client = EurostatClient()
        result = client._parse_construction_data(
            mock_response, "PT", "F", "SCA",
            start_date=date(2024, 2, 1), end_date=None
        )
        assert len(result) == 2  # Feb and Mar only
        assert result[0].date == date(2024, 2, 1)

class TestEurostatIndustrialProduction:
    """Unit tests for Eurostat industrial production index."""

    def test_parse_industrial_data_valid(self):
        """Parse valid industrial production response."""
        mock_response = {
            "value": {"0": 98.5, "1": 99.2, "2": 100.1},
            "dimension": {
                "time": {
                    "category": {
                        "index": {"2024-01": 0, "2024-02": 1, "2024-03": 2}
                    }
                }
            }
        }
        client = EurostatClient()
        result = client._parse_industrial_data(
            mock_response, "PT", "B-D", "SCA", None, None
        )
        assert len(result) == 3
        assert result[0].index_value == 98.5
        assert result[0].nace_sector == "B-D"

    @pytest.mark.asyncio
    async def test_fetch_industrial_production_builds_correct_url(self):
        """Fetch constructs correct API URL."""
        client = EurostatClient()
        with patch.object(client, '_fetch_eurostat_data', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = {"value": {}, "dimension": {"time": {"category": {"index": {}}}}}
            await client.fetch_industrial_production(country="PT")
            mock_fetch.assert_called_once()
            call_args = mock_fetch.call_args
            assert call_args[0][0] == "sts_inpr_m"  # Dataset
            assert call_args[0][1]["geo"] == "PT"  # Filter
```

### Integration Tests (tests/integration/test_eurostat_construction_integration.py)

```python
import pytest
from datetime import date
from scipy.stats import pearsonr
from raglite.external_data.clients.eurostat import EurostatClient

@pytest.mark.integration
@pytest.mark.slow
class TestEurostatConstructionIntegration:
    """Integration tests for Eurostat construction indicators."""

    @pytest.mark.asyncio
    async def test_fetch_construction_output_portugal(self):
        """AC1: Fetch construction output for Portugal."""
        client = EurostatClient()
        data = await client.fetch_construction_output(
            country="PT",
            start_date=date(2020, 1, 1),
            end_date=date(2024, 12, 31)
        )
        assert len(data) >= 48, f"Expected 48+ months, got {len(data)}"
        assert all(d.country == "PT" for d in data)
        assert all(d.index_value > 0 for d in data)

    @pytest.mark.asyncio
    async def test_fetch_industrial_production_portugal(self):
        """AC2: Fetch industrial production for Portugal."""
        client = EurostatClient()
        data = await client.fetch_industrial_production(
            country="PT",
            start_date=date(2020, 1, 1),
            end_date=date(2024, 12, 31)
        )
        assert len(data) >= 48, f"Expected 48+ months, got {len(data)}"
        assert all(d.country == "PT" for d in data)
        assert all(d.index_value > 0 for d in data)

    @pytest.mark.asyncio
    async def test_construction_data_completeness(self):
        """AC4: Data has <10% missing values over 5 years."""
        client = EurostatClient()
        data = await client.fetch_construction_output(
            country="PT",
            start_date=date(2020, 1, 1),
            end_date=date(2024, 12, 31)
        )
        expected_months = 60  # 5 years
        actual_count = len(data)
        missing_pct = (expected_months - actual_count) / expected_months * 100
        assert missing_pct < 10, f"Missing {missing_pct:.1f}% exceeds 10% threshold"

    @pytest.mark.asyncio
    async def test_industrial_data_completeness(self):
        """AC4: Industrial data has <10% missing values."""
        client = EurostatClient()
        data = await client.fetch_industrial_production(
            country="PT",
            start_date=date(2020, 1, 1),
            end_date=date(2024, 12, 31)
        )
        expected_months = 60
        actual_count = len(data)
        missing_pct = (expected_months - actual_count) / expected_months * 100
        assert missing_pct < 10, f"Missing {missing_pct:.1f}% exceeds 10% threshold"

    @pytest.mark.asyncio
    async def test_data_sorted_by_date(self):
        """Data returned sorted by date ascending."""
        client = EurostatClient()
        data = await client.fetch_construction_output(
            country="PT",
            start_date=date(2022, 1, 1),
            end_date=date(2023, 12, 31)
        )
        dates = [d.date for d in data]
        assert dates == sorted(dates), "Data not sorted by date"
```

## Prerequisites

**Dependencies:** None - this story can be implemented independently

**Required Knowledge:**
- Eurostat SDMX API structure
- Existing EurostatClient patterns in codebase
- NACE Rev. 2 sector classification

## References

- [Source: docs/prd/epic-6-advanced-forecasting-external-data.md#Story 6.16]
- [Source: docs/sprint-change-proposals/2025-12-12-epic-6-forecasting-accuracy-extension.md]
- [Source: docs/architecture/6-external-data-pipeline-epic-6.md#New Data Sources]
- [Source: raglite/external_data/clients/eurostat.py - existing client]
- [Eurostat SDMX API: https://ec.europa.eu/eurostat/web/json-and-unicode-web-services]
- [NACE Rev. 2: https://ec.europa.eu/eurostat/web/nace-rev2]

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

### File List

- `raglite/external_data/clients/eurostat.py` - Modified (add fetch methods)
- `raglite/external_data/models.py` - Modified (add data models)
- `raglite/forecasting/regressor_config.py` - Modified (register regressors)
- `raglite/forecasting/regressor_fetch.py` - Modified (add fetch functions)
- `tests/unit/test_eurostat_construction.py` - New (unit tests)
- `tests/integration/test_eurostat_construction_integration.py` - New (integration tests)
