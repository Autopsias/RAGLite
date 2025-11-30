# Data Dictionary - Epic 3 Analytical Queries

**Generated:** 2025-11-06
**Source:** PostgreSQL financial_tables (1,547 rows)
**Purpose:** Validate test queries align with actual database content
**Story:** 3.0.2 - Create Epic 3 Data Dictionary

---

## Available Metrics

| Metric | Sample Value | Notes |
|--------|--------------|-------|
| EBITDA | 191.8 | Earnings before interest, taxes, depreciation, amortization |
| Revenue (M EUR) | 379.2 | Total revenue in millions EUR |
| Turnover | 245.6 | Revenue/turnover metrics |
| Frequency Ratio (1) | 3.68 | Safety/operational frequency ratio |
| Capital Employed (%) | 12.5 | Percentage of capital employed |
| Cash | 89.3 | Cash position in millions |
| Financial | varies | Financial indicators |
| Operational | varies | Operational metrics |
| Operational Profitability (%) | 8.2 | Operating margin percentage |

**Total Unique Metrics:** 28

**Full Metrics List:**
- (5)
- Angola AOA - Currency Exchange impact
- Angola USD - Currency Exchange impact
- Brazil BRL - Currency Exchange impact
- Capital Employed (%)
- Capital Employed profitability (M EUR, %) (5)
- Cash
- Closing Eur/ LCU
- Currency (1000 EUR)
- Currency Exchange impact Secil GROUP
- **EBITDA** ⭐
- Eur/Akz
- Eur/Brl
- Eur/Tnd
- Eur/Usd
- Financial
- Frequency Ratio (1)
- Indicator
- (M EUR, %)
- Operational
- Operational Profitability (%)
- Portugal EUR - Currency Exchange impact
- Results
- **Revenue (M EUR)** ⭐
- Tunisia TND - Currency Exchange impact
- **Turnover** ⭐
- USD - Currency Exchange impact Lebanon
- (null values present)

⭐ = Core metrics for analytical queries

---

## Available Periods

### Well-Formed Periods (Month-Year Format)

| Period | Type | Description |
|--------|------|-------------|
| Jan-25 | Monthly | January 2025 actual |
| Feb-25 | Monthly | February 2025 actual |
| Mar-25 | Monthly | March 2025 actual |
| Apr-25 | Monthly | April 2025 actual |
| May-25 | Monthly | May 2025 actual |
| Jun-25 | Monthly | June 2025 actual |
| Jul-25 | Monthly | July 2025 actual |
| Aug-24 | Monthly | August 2024 actual |
| Aug-25 | Monthly | August 2025 actual |
| Sep-25 | Monthly | September 2025 actual |
| Oct-25 | Monthly | October 2025 actual |
| Nov-25 | Monthly | November 2025 actual |
| Dec-25 | Monthly | December 2025 actual |
| Mar-24 | Monthly | March 2024 actual |

**Well-Formed Period Count:** 14 periods

### Period Mappings (from Story 2.15)

Quarter-to-month normalization for queries:

| Query Period | Maps To |
|--------------|---------|
| Q1 2025 | Jan-25, Feb-25, Mar-25 |
| Q2 2025 | Apr-25, May-25, Jun-25 |
| Q3 2025 | Jul-25, Aug-25, Sep-25 |
| Q4 2024 | Oct-24, Nov-24, Dec-24 (if available) |

**Note:** YTD (Year-To-Date) periods not found in current dataset.

**Total Unique Periods:** 152 (includes malformed entries - see Limitations)

---

## Available Entities

| Entity | Full Name | Country | Type |
|--------|-----------|---------|------|
| Group | Secil Group Consolidated | Global | Consolidated |
| Portugal | Portugal Cement Operations | Portugal | Cement |
| Angola | Angola Operations | Angola | Cement |
| Tunisia | Tunisia Cement Operations | Tunisia | Cement |
| Brazil | Brazil Operations | Brazil | Cement |
| Lebanon | Lebanon Operations | Lebanon | Cement |
| Others | Other Operations | Various | Mixed |
| Group Structure * | Group Structure Adjustments | Internal | Adjustments |
| Currency (1000 EUR) | Currency Amounts in Thousands EUR | N/A | Currency Reporting |

**Total Unique Entities:** 36 (includes entity-period combinations - see Limitations)

### Entity Aliases (from Story 2.14 AC1)

Fuzzy matching rules for query normalization:

| Query Term | Matches Entity | Fuzzy Match Threshold |
|------------|----------------|----------------------|
| "Group" | Group | Exact |
| "Secil" | Secil Group | Contains |
| "Portugal" | Portugal | Exact |
| "Angola" | Angola | Exact |
| "Secil Angola" | Angola | Alias |
| "Tunisia" | Tunisia | Exact |
| "Brazil" | Brazil | Exact |
| "Adrianopolis" | Brazil | Regional (Story 2.14) |
| "Pomerode" | Brazil | Regional (Story 2.14) |

**Fuzzy Match Algorithm:** 80% similarity threshold (Story 2.14 implementation)

---

## Available Units

### Standard Units

| Unit | Description | Example Value |
|------|-------------|---------------|
| % | Percentage | 12.5% |
| M EUR | Millions EUR | 191.8 |
| EUR | Euro currency | 1,234.56 |
| (null) | No unit specified | varies |

**Total Unique Units:** 38 (includes malformed entries)

### Currency Limitations

- ✅ **EUR (Euro)** - PRIMARY CURRENCY (most data)
- ❌ **AOA (Angolan Kwanza)** - Not as base unit (currency exchange metrics only)
- ❌ **BRL (Brazilian Real)** - Not as base unit (currency exchange metrics only)
- ❌ **TND (Tunisian Dinar)** - Not as base unit (currency exchange metrics only)
- ❌ **USD (US Dollar)** - Not as base unit (currency exchange metrics only)

**Note:** Database stores most values in EUR. Currency conversion NOT supported (Story 2.14 AC5).

---

## Data Limitations

### ⚠️ Critical Limitations

#### 1. Reduced Dataset Size
- **Actual Rows:** 1,547
- **Story Expected:** ~170,142
- **Impact:** Limited historical data; fewer time series for trend analysis
- **Cause:** Database appears partially populated or test data only

#### 2. Data Quality Issues - Metrics

**Noisy Metric Entries (7 currency-related):**
- "Angola AOA - Currency Exchange impact"
- "Angola USD - Currency Exchange impact"
- "Brazil BRL - Currency Exchange impact"
- "Portugal EUR - Currency Exchange impact"
- "Tunisia TND - Currency Exchange impact"
- "USD - Currency Exchange impact Lebanon"
- "Currency Exchange impact Secil GROUP"

**Recommendation:** Filter queries to core metrics (EBITDA, Revenue, Turnover, etc.)

#### 3. Data Quality Issues - Periods

**Malformed Period Entries (8 identified):**
- "147.068 Angola", "147.068 Brazil", "147.068 Group Structure *", etc.
- "Apr Angola", "Apr Brazil", "Apr Group Structure *", etc.

**Root Cause:** Table extraction errors from PDF (numeric data parsed as periods)

**Well-Formed Periods:** Only 14 out of 152 total (9% clean data rate)

**Recommendation:** Use period validation against well-formed list before query execution

#### 4. Data Quality Issues - Entities

**Entity-Period Combinations:**
Many entity entries are actually entity-period combinations:
- "147.068 Angola" (should be entity="Angola", period="147.068" separately)

**Recommendation:** Entity validation should accept base entity names only

#### 5. Missing Data Elements

**Metrics NOT Available:**
- ❌ Variable Cost (individual components)
- ❌ Fixed Cost (breakdown)
- ❌ G&A Expenses
- ❌ Headcount / FTE data
- ❌ Production Volume (tonnes)
- ❌ Cost per Unit (detailed)

**Period Variants NOT Available:**
- ❌ YTD (Year-To-Date) periods
- ❌ Budget periods (B Aug-25)
- ❌ Forecast periods

**Currency Conversions NOT Available:**
- ❌ Native currency amounts (AOA, BRL, TND)
- ❌ Currency conversion rates (stored only for reference)

---

## Test Query Validation Rules

**CRITICAL:** All Epic 3 test queries MUST pass these checks BEFORE validation execution.

### Validation Process (4 Steps)

#### Step 1: Metric Check
```
Question: Is metric in "Available Metrics" section?
Action:
  - YES → Proceed to Step 2
  - NO → Remove query OR use available metric

Example:
  ✅ "What is EBITDA for Portugal?" → EBITDA found
  ❌ "What is Variable Cost?" → NOT in metrics → Use "Operational" or skip
```

#### Step 2: Period Check
```
Question: Is period well-formed (in 14 good periods) OR mappable via Story 2.15?
Action:
  - YES → Proceed to Step 3
  - NO → Remove query OR use available period

Example:
  ✅ "EBITDA in Aug-25" → Aug-25 in well-formed list
  ✅ "EBITDA in Q3 2025" → Maps to Jul-25, Aug-25, Sep-25 (Story 2.15)
  ❌ "EBITDA in Q3 2025 YTD" → YTD not available → Use "Aug-25" instead
  ❌ "EBITDA in 147.068 Angola" → Malformed → Skip
```

#### Step 3: Entity Check
```
Question: Is entity in "Available Entities" base list OR fuzzy-matchable?
Action:
  - YES → Proceed to Step 4
  - NO → Remove query OR use available entity

Example:
  ✅ "Portugal EBITDA" → Portugal in entity list
  ✅ "Angola EBITDA" → Angola in entity list
  ✅ "Group EBITDA" → Group in entity list
  ❌ "Morocco EBITDA" → NOT in entities → Remove query
```

#### Step 4: Unit Check
```
Question: Does query expect EUR or percentage?
Action:
  - YES → Proceed with query
  - NO → Convert to EUR request OR remove query

Example:
  ✅ "EBITDA in EUR" → EUR available
  ✅ "Profitability %" → % available
  ❌ "EBITDA in USD" → USD not base unit → Convert to EUR OR skip
```

### Enforcement

**Pre-Validation Gate:**
- Test creation scripts MUST validate ALL queries against this 4-step process
- Queries failing validation MUST be flagged for review
- No query execution without successful validation

**Logging:**
- All validation failures MUST be logged with:
  - Query text
  - Failed validation step (1-4)
  - Reason for failure
  - Suggested fix (if available)

---

## Usage Examples

### Valid Query Examples

```
✅ "What is EBITDA for Portugal in Aug-25?"
   Metric: EBITDA (found)
   Entity: Portugal (found)
   Period: Aug-25 (well-formed)

✅ "Show me Revenue for Group in Q3 2025"
   Metric: Revenue (M EUR) (found)
   Entity: Group (found)
   Period: Q3 2025 → Jul-25, Aug-25, Sep-25 (mappable via Story 2.15)

✅ "What is Operational Profitability for Tunisia in Feb-25?"
   Metric: Operational Profitability (%) (found)
   Entity: Tunisia (found)
   Period: Feb-25 (well-formed)
```

### Invalid Query Examples (With Fixes)

```
❌ "What is Variable Cost for Portugal in Aug-25?"
   Issue: Variable Cost NOT in metrics
   Fix: Use "Operational" or skip query

❌ "Show me EBITDA for Morocco"
   Issue: Morocco NOT in entities
   Fix: Remove query

❌ "What is Revenue in Q3 2025 YTD?"
   Issue: YTD periods not available
   Fix: Use "Aug-25" (latest Q3 month)

❌ "What is EBITDA in USD?"
   Issue: USD not base currency
   Fix: Convert to EUR request
```

---

## References

### Source Code
- Database client: `raglite/shared/clients.py:get_postgresql_connection()`
- Table schema: `raglite/shared/models.py` (financial_tables)
- Inspection script: `scripts/inspect-database-for-epic-3.py`
- JSON catalog: `docs/data-dictionary-epic-3.json`

### Related Stories
- [Story 2.14: SQL Generation Edge Case Refinement](../stories/2-14-sql-generation-edge-case-refinement.md) - Entity fuzzy matching
- [Story 2.15: Ground Truth Normalization](../stories/2-15-ground-truth-normalization-epic-2-final-validation.md) - Period normalization
- [Epic 2 Retrospective](../retrospectives/epic-2-retro-2025-11-05.md) - Ground truth misalignment issue (12% → 77.6%)

### Documentation
- [Epic 3 Tech Spec](../tech-spec-epic-3-prep.md) - Story 3.0.2 specification
- [Epic 3 Overview](../epics.md#epic-3-ai-intelligence--orchestration) - Agentic orchestration goals

---

## Changelog

**2025-11-06:**
- Initial data dictionary created from database inspection
- Documented 1,547 rows (reduced dataset)
- Identified 28 metrics, 152 periods (14 well-formed), 36 entities, 38 units
- Documented data quality issues (noisy metrics, malformed periods)
- Created 4-step validation process for test queries
- Established limitations section to prevent Epic 2's ground truth misalignment

---

**Epic 3 Test Creation Status:** ✅ Data dictionary COMPLETE
**Next Step:** Winston architecture review (AC3)
**Epic 3 Implementation:** BLOCKED until dictionary approval
