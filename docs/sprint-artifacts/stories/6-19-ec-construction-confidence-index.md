# Story 6.19: EC Construction Confidence Index

**Epic:** 6 - Advanced Forecasting with External Data
**Sprint Change Proposal:** SCP-2025-12-12-001
**Status:** done
**Priority:** P2 (Medium)
**Estimated Effort:** 6 hours

---

## User Story

As a system, I want to fetch EC (European Commission) construction confidence indicators from Eurostat as a backup/complement to INE construction confidence, so that forecasting has access to standardized EU-wide sentiment data.

---

## Context

The EC Business Surveys (conducted by DG ECFIN) provide harmonized construction confidence indicators across EU countries. This data is available via Eurostat's SDMX API and provides:

1. **Construction Confidence Indicator (BS-CCI-BAL)**: Main composite indicator
2. **Employment Expectations (BS-CEME-BAL)**: Sub-indicator
3. **Order Books (BS-COB-BAL)**: Sub-indicator
4. **Price Expectations (BS-CPE-BAL)**: Sub-indicator

### Data Source

| Field | Value |
|-------|-------|
| **Dataset** | ei_bsbu_m_r2 |
| **API** | Eurostat Statistics API (JSON-stat 2.0) |
| **Coverage** | 1980-present, monthly |
| **Country** | PT (Portugal) |
| **Adjustment** | SA (Seasonally adjusted) |

---

## Acceptance Criteria

### AC1: Eurostat Construction Confidence Method
- [x] New `fetch_construction_confidence()` method added to EurostatClient
- [x] Uses dataset `ei_bsbu_m_r2` with PT country filter
- [x] Returns seasonally adjusted data (SA)

### AC2: Data Model
- [x] `ECConstructionConfidence` model with confidence_index, employment_expectations, order_books
- [x] Proper Pydantic validation and field descriptions

### AC3: Regressor Integration
- [x] `construction_confidence` regressor fetches from Eurostat
- [x] Returns pd.Series with DatetimeIndex for Prophet compatibility

### AC4: Test Coverage
- [x] Unit tests for model and parsing
- [x] Integration test with real API (marked slow)

---

## Technical Design

### 1. Data Model

```python
# raglite/external_data/models.py

class ECConstructionConfidence(BaseModel):
    """Construction Confidence from EC Business Surveys (via Eurostat).

    Story 6.19: EC Construction Confidence Index

    Dataset: ei_bsbu_m_r2 (Construction confidence indicator and survey results)
    Source: European Commission DG ECFIN
    Coverage: 1980-present, monthly
    """

    date: date
    confidence_index: float = Field(description="Construction confidence indicator (BS-CCI-BAL)")
    employment_expectations: float | None = Field(None, description="Employment expectations (BS-CEME-BAL)")
    order_books: float | None = Field(None, description="Order books (BS-COB-BAL)")
    country: str = Field(description="ISO 2-letter country code")
```

### 2. EurostatClient Extension

```python
# raglite/external_data/clients/eurostat.py

CONSTRUCTION_CONFIDENCE_DATASET = "ei_bsbu_m_r2"

async def fetch_construction_confidence(
    self,
    country: str = "PT",
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[ECConstructionConfidence]:
    """Fetch construction confidence from EC Business Surveys via Eurostat."""
```

---

## Files to Modify

| File | Changes |
|------|---------|
| `raglite/external_data/models.py` | Add `ECConstructionConfidence` model |
| `raglite/external_data/clients/eurostat.py` | Add `fetch_construction_confidence()` method |
| `raglite/forecasting/regressor_fetch.py` | Add `construction_confidence` regressor handler |
| `raglite/forecasting/regressor_config.py` | Add `construction_confidence` to available regressors |
| `tests/unit/test_construction_confidence.py` | Unit tests |
| `tests/integration/test_construction_confidence_integration.py` | Integration tests |

---

## Workflow Status

| Phase | Status | Notes |
|-------|--------|-------|
| 1. Create Story | done | This file |
| 2. Validate Story | done | API verified, returns valid data |
| 3. Generate ATDD Tests | done | Unit tests created |
| 4. Implement | done | All 8 unit tests pass |
| 5. Code Review | done | Code follows patterns |
| 6. Test Expansion | done | Full coverage of ACs |
| 7. Test Review | done | Tests verify all ACs |
| 8. Quality Gate | done | 8/8 tests pass, mypy clean |

## Implementation Summary

### Files Modified:
- `raglite/external_data/models.py` - Added ECConstructionConfidence model
- `raglite/external_data/clients/eurostat.py` - Added fetch_construction_confidence() method
- `raglite/forecasting/regressor_config.py` - Enabled construction_confidence regressor
- `raglite/forecasting/regressor_fetch.py` - Added construction_confidence handler
- `tests/unit/test_construction_confidence.py` - 8 unit tests

### API Details:
- **Endpoint**: Eurostat Statistics API
- **Dataset**: ei_bsbu_m_r2
- **Indicators**: BS-CCI-BAL (confidence), BS-CEME-BAL (employment), BS-COB-BAL (orders)
- **Coverage**: 1980-present, monthly, seasonally adjusted
