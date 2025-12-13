# Story 6.18: Fix INE Building Permits API

**Epic:** 6 - Advanced Forecasting with External Data
**Sprint Change Proposal:** SCP-2025-12-12-001
**Status:** done
**Priority:** P1 (High)
**Estimated Effort:** 4 hours

---

## User Story

As a system, I want to fix the INE Building Permits indicator ID (currently returning wrong data) and add Eurostat backup, so that forecasting has access to construction leading indicators.

---

## Context

The INE Building Permits API was previously disabled because the indicator returned wrong data. The current indicator `0012096` (Edifícios licenciados) now returns valid building permit data by region.

### Issues to Fix

1. **Regressor is disabled:** The `building_permits` regressor is currently disabled in `regressor_fetch.py`
2. **Regional aggregation needed:** INE returns data by region (e.g., "Alentejo Litoral: 12 permits"). Need to aggregate to national total.
3. **No backup source:** Add Eurostat as fallback when INE is unavailable

### Data Sources

| Source | Dataset | Description |
|--------|---------|-------------|
| INE | 0010099 or 0010094 | Licenciamento de obras (recommended) |
| INE | 0012096 | Edifícios licenciados (current) |
| Eurostat | sts_cobp_m | Building permits - number of dwellings (backup) |

---

## Acceptance Criteria

### AC1: INE Building Permits Aggregated to National Total
- [x] Aggregate regional data to national monthly totals
- [x] Filter for "Portugal" region or sum all regional values
- [x] Returns pd.Series with DatetimeIndex for Prophet compatibility

### AC2: Eurostat Building Permits Backup
- [x] New `fetch_building_permits()` method added to EurostatClient
- [x] Dataset `sts_cobp_m` used with PT country filter
- [x] Returns monthly building permits count for Portugal

### AC3: Fallback Logic
- [x] `fetch_building_permits()` in regressor_fetch.py tries INE first
- [x] If INE fails or returns no data, automatically uses Eurostat backup
- [x] Logging indicates which source was used

### AC4: Correlation Validation
- [x] Building permits shows >0.3 correlation with sales_volume
- [x] Data available for period 2020-2025

### AC5: No Regression
- [x] All existing INE client tests pass
- [x] All existing regressor tests pass

---

## Technical Design

### 1. Verify INE Indicator ID

```python
# raglite/external_data/clients/ine.py

# Current:
BUILDING_PERMITS_INDICATOR = "0012096"  # Edifícios licenciados (N.º)

# Potential fix (if current returns wrong data):
BUILDING_PERMITS_INDICATOR = "0010099"  # Licenciamento de obras
```

### 2. Add Eurostat Building Permits

```python
# raglite/external_data/clients/eurostat.py

class EurostatClient:
    BUILDING_PERMITS_DATASET = "sts_cobp_m"  # Building permits

    async def fetch_building_permits(
        self,
        country: str = "PT",
        start_date: date | None = None,
        end_date: date | None = None,
        building_type: str = "RES",  # Residential
    ) -> list[EurostatBuildingPermits]:
        """Fetch building permits from Eurostat (backup for INE).

        Dataset: sts_cobp_m (Building permits - number of dwellings)
        Coverage: Monthly, 2000-present
        """
```

### 3. Add Data Model

```python
# raglite/external_data/models.py

@dataclass
class EurostatBuildingPermits:
    date: date
    permits_count: int
    country: str
    building_type: str  # RES, NRES, TOTAL
```

### 4. Update Regressor Fetch

```python
# raglite/forecasting/regressor_fetch.py

elif reg_name == "building_permits":
    # Try INE first
    from raglite.external_data.clients.ine import INEClient
    client_ine = INEClient()
    permits_data = await client_ine.fetch_building_permits(start_date, end_date)

    # Fallback to Eurostat if INE fails or returns no data
    if not permits_data:
        from raglite.external_data.clients.eurostat import EurostatClient
        client_eurostat = EurostatClient()
        permits_data = await client_eurostat.fetch_building_permits(
            country="PT", start_date=start_date, end_date=end_date
        )
        logger.info("Using Eurostat building permits (INE fallback)")
```

---

## Test Plan

### Unit Tests

| Test | Description |
|------|-------------|
| test_ine_building_permits_returns_valid_data | Verify INE API returns construction data |
| test_ine_building_permits_date_filtering | Test date range filtering |
| test_eurostat_building_permits_fetch | Test Eurostat building permits endpoint |
| test_eurostat_building_permits_parsing | Test SDMX-JSON parsing |
| test_building_permits_fallback | Test INE → Eurostat fallback logic |

### Integration Tests

| Test | Description |
|------|-------------|
| test_building_permits_real_api | Test with real INE API (mark slow) |
| test_eurostat_building_permits_real_api | Test with real Eurostat API (mark slow) |
| test_building_permits_regressor | Test building_permits regressor fetch |

---

## Files to Modify

| File | Changes |
|------|---------|
| `raglite/external_data/clients/ine.py` | Verify/fix `BUILDING_PERMITS_INDICATOR` |
| `raglite/external_data/clients/eurostat.py` | Add `fetch_building_permits()` method |
| `raglite/external_data/models.py` | Add `EurostatBuildingPermits` dataclass |
| `raglite/forecasting/regressor_fetch.py` | Add fallback logic for building_permits |
| `raglite/forecasting/regressor_config.py` | Ensure building_permits registered |
| `tests/unit/test_ine_building_permits.py` | New unit tests |
| `tests/integration/test_building_permits.py` | New integration tests |

---

## Dependencies

- None (can start immediately)

---

## NFRs

- API response time: <5s p95
- Data freshness: <30 days (alert if stale)
- Fallback latency: <10s total (INE attempt + Eurostat fallback)

---

## Workflow Status

| Phase | Status | Notes |
|-------|--------|-------|
| 1. Create Story | done | This file |
| 2. Validate Story | done | Story requirements verified |
| 3. Generate ATDD Tests | done | Unit + integration tests created |
| 4. Implement | done | All 10 unit tests pass |
| 5. Code Review | done | Approved with recommendations (addressed) |
| 6. Test Expansion | done | Added national totals test |
| 7. Test Review | done | Tests cover all ACs |
| 8. Quality Gate | done | 10/10 tests pass, mypy clean |

## Code Review Summary (Phase 5)

**Status:** APPROVED ✅

### Issues Addressed:
1. **Double-counting prevention**: Added national total detection to avoid summing regional data when national totals exist
2. **Consistent aggregation**: Standardized to use `pd.Series.groupby().sum()` for both INE and Eurostat paths
3. **Structured logging**: Updated to use `extra={}` parameter for structured log context
4. **Test markers**: Added `@pytest.mark.slow` to integration tests hitting real APIs
5. **New test added**: `test_ine_building_permits_uses_national_totals_when_available`

### Implementation Files:
- `raglite/external_data/models.py` - Added EurostatBuildingPermits model
- `raglite/external_data/clients/eurostat.py` - Added fetch_building_permits()
- `raglite/forecasting/regressor_config.py` - Enabled building_permits regressor
- `raglite/forecasting/regressor_fetch.py` - INE with Eurostat fallback, national total handling
- `tests/unit/test_building_permits.py` - 10 unit tests
- `tests/integration/test_building_permits_integration.py` - 6 integration tests
