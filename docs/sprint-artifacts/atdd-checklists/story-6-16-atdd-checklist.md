# ATDD Checklist - Story 6.16: Eurostat Construction & Industrial Indicators

## Story Reference

- **Story ID:** 6.16
- **Story File:** `docs/sprint-artifacts/stories/6-16-eurostat-construction-industrial-indicators.md`
- **Epic:** 6 - Advanced Forecasting with External Data
- **Status:** RED PHASE (Tests Created, Implementation Pending)

## Test Files Created

| File | Type | Test Count | Status |
|------|------|------------|--------|
| `tests/unit/test_eurostat_indicators.py` | Unit | 27 | RED (Failing) |
| `tests/integration/test_eurostat_api.py` | Integration | 18 | RED (Failing) |

**Total Tests:** 45

## Acceptance Criteria Coverage

### AC1: Construction Output Index API

| Test ID | Test Method | Status | Notes |
|---------|-------------|--------|-------|
| `test_ac1_parse_construction_data_valid` | Unit | RED | `_parse_construction_data` not implemented |
| `test_ac1_parse_construction_data_returns_model_type` | Unit | RED | `EurostatConstructionOutput` not defined |
| `test_ac1_parse_construction_data_date_parsing` | Unit | RED | Method not implemented |
| `test_ac1_parse_construction_missing_values_skipped` | Unit | RED | Method not implemented |
| `test_ac1_parse_construction_date_filter_start` | Unit | RED | Method not implemented |
| `test_ac1_parse_construction_date_filter_end` | Unit | RED | Method not implemented |
| `test_ac1_parse_construction_sorted_by_date` | Unit | RED | Method not implemented |
| `test_ac1_fetch_construction_output_builds_correct_url` | Unit (Async) | RED | `fetch_construction_output` not implemented |
| `test_ac1_fetch_construction_output_returns_data` | Unit (Async) | RED | Method not implemented |
| `test_ac1_fetch_construction_output_handles_api_error` | Unit (Async) | RED | Method not implemented |
| `test_ac1_construction_output_monthly_portugal` | Integration | RED | Method not implemented |
| `test_ac1_construction_output_country_portugal` | Integration | RED | Method not implemented |
| `test_ac1_construction_output_index_values_positive` | Integration | RED | Method not implemented |
| `test_ac1_construction_output_date_range_respected` | Integration | RED | Method not implemented |
| `test_ac1_construction_output_returns_correct_model_type` | Integration | RED | Model not defined |
| `test_ac1_construction_output_nace_sector_construction` | Integration | RED | Method not implemented |
| `test_ac1_construction_dataset_constant` | Unit | RED | `CONSTRUCTION_DATASET` constant not defined |

### AC2: Industrial Production Index API

| Test ID | Test Method | Status | Notes |
|---------|-------------|--------|-------|
| `test_ac2_parse_industrial_data_valid` | Unit | RED | `_parse_industrial_data` not implemented |
| `test_ac2_parse_industrial_data_returns_model_type` | Unit | RED | `EurostatIndustrialProduction` not defined |
| `test_ac2_parse_industrial_data_date_parsing` | Unit | RED | Method not implemented |
| `test_ac2_parse_industrial_missing_values_skipped` | Unit | RED | Method not implemented |
| `test_ac2_parse_industrial_date_filter_start` | Unit | RED | Method not implemented |
| `test_ac2_parse_industrial_sorted_by_date` | Unit | RED | Method not implemented |
| `test_ac2_fetch_industrial_production_builds_correct_url` | Unit (Async) | RED | `fetch_industrial_production` not implemented |
| `test_ac2_fetch_industrial_production_returns_data` | Unit (Async) | RED | Method not implemented |
| `test_ac2_fetch_industrial_production_handles_api_error` | Unit (Async) | RED | Method not implemented |
| `test_ac2_industrial_production_monthly_portugal` | Integration | RED | Method not implemented |
| `test_ac2_industrial_production_country_portugal` | Integration | RED | Method not implemented |
| `test_ac2_industrial_production_index_values_positive` | Integration | RED | Method not implemented |
| `test_ac2_industrial_production_date_range_respected` | Integration | RED | Method not implemented |
| `test_ac2_industrial_production_returns_correct_model_type` | Integration | RED | Model not defined |
| `test_ac2_industrial_production_nace_sector_industry` | Integration | RED | Method not implemented |
| `test_ac2_industrial_production_dataset_constant` | Unit | RED | `INDUSTRIAL_PRODUCTION_DATASET` constant not defined |

### AC3: Correlation with Sales Volume

| Test ID | Test Method | Status | Notes |
|---------|-------------|--------|-------|
| `test_ac3_construction_correlation_above_threshold` | Integration | RED | Depends on AC1 methods |
| `test_ac3_industrial_correlation_above_threshold` | Integration | RED | Depends on AC2 methods |
| `test_ac3_correlation_statistically_significant` | Integration | RED | Depends on AC1/AC2 methods |

### AC4: Data Quality - Missing Values

| Test ID | Test Method | Status | Notes |
|---------|-------------|--------|-------|
| `test_ac4_construction_data_completeness` | Integration | RED | Depends on AC1 methods |
| `test_ac4_industrial_data_completeness` | Integration | RED | Depends on AC2 methods |
| `test_ac4_construction_data_sorted_by_date` | Integration | RED | Depends on AC1 methods |
| `test_ac4_industrial_data_sorted_by_date` | Integration | RED | Depends on AC2 methods |

### AC5: Unit Tests for Parsing and Data Quality

| Test ID | Test Method | Status | Notes |
|---------|-------------|--------|-------|
| `test_ac5_construction_output_model_exists` | Unit | RED | Model not imported |
| `test_ac5_industrial_production_model_exists` | Unit | RED | Model not imported |
| `test_ac5_construction_output_model_fields` | Unit | RED | Model not defined |
| `test_ac5_industrial_production_model_fields` | Unit | RED | Model not defined |
| `test_ac5_construction_output_index_value_positive` | Unit | RED | Model not defined |
| `test_ac5_industrial_production_index_value_positive` | Unit | RED | Model not defined |

## Implementation Requirements

### Models to Create (`raglite/external_data/models.py`)

```python
class EurostatConstructionOutput(BaseModel):
    """Construction production index from Eurostat (sts_copr_m)."""
    date: date
    index_value: float = Field(gt=0, description="Index 2021=100")
    country: str = Field(description="ISO 2-letter code")
    nace_sector: str = Field(description="NACE Rev. 2 sector code")
    seasonal_adjustment: str = Field(description="SCA, NSA, etc.")

class EurostatIndustrialProduction(BaseModel):
    """Industrial production index from Eurostat (sts_inpr_m)."""
    date: date
    index_value: float = Field(gt=0, description="Index 2021=100")
    country: str = Field(description="ISO 2-letter code")
    nace_sector: str = Field(description="NACE Rev. 2 sector code")
    seasonal_adjustment: str = Field(description="SCA, NSA, etc.")
```

### Methods to Add (`raglite/external_data/clients/eurostat.py`)

1. **Constants:**
   - `CONSTRUCTION_DATASET = "sts_copr_m"`
   - `INDUSTRIAL_PRODUCTION_DATASET = "sts_inpr_m"`

2. **Fetch Methods:**
   - `fetch_construction_output(country, start_date, end_date, nace_sector, seasonal_adjustment)`
   - `fetch_industrial_production(country, start_date, end_date, nace_sector, seasonal_adjustment)`

3. **Parse Methods:**
   - `_parse_construction_data(data, country, nace_sector, seasonal_adjustment, start_date, end_date)`
   - `_parse_industrial_data(data, country, nace_sector, seasonal_adjustment, start_date, end_date)`

## Running the Tests

### Unit Tests (Fast - RED Phase)
```bash
uv run pytest tests/unit/test_eurostat_indicators.py -v
# Expected: All tests FAIL (AttributeError, ImportError)
```

### Integration Tests (Slow - RED Phase)
```bash
uv run pytest tests/integration/test_eurostat_api.py -v -m "integration and slow"
# Expected: All tests FAIL (AttributeError)
```

### All Story 6.16 Tests
```bash
uv run pytest tests/unit/test_eurostat_indicators.py tests/integration/test_eurostat_api.py -v
# Expected: 45 tests, all FAILING
```

## TDD Cycle Status

| Phase | Status | Date | Notes |
|-------|--------|------|-------|
| **RED** | COMPLETE | 2025-12-13 | 45 failing tests created |
| GREEN | PENDING | - | Implement models and methods |
| REFACTOR | PENDING | - | Clean up after GREEN |

## Dependencies

- **None** - This story can be implemented independently
- **Existing patterns:** Follow `fetch_electricity_prices()` pattern in `eurostat.py`

## Notes

- Tests use `pytest.mark.asyncio` for async methods
- Tests use `pytest.mark.integration` and `pytest.mark.slow` for real API calls
- Mock responses follow Eurostat SDMX-JSON format
- AC3 correlation tests use synthetic sales data (production would use real data)
- All tests follow Given-When-Then structure in docstrings
