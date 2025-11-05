# Phase 2.7.4: Comprehensive Table Type Taxonomy & Solution

**Date**: 2025-10-27
**Status**: Analysis Complete, Implementation Pending Page 23 Results
**Objective**: Build robust adaptive table detection for ANY table structure

---

## 📊 Complete Table Taxonomy

Based on analysis of chunk PDF (test-chunk-pages-18-23.pdf), we've identified **4 distinct table types**:

### Type A: Transposed Metric-Entity Tables ✅ WORKING

**Structure:**
- **Column 0**: Metric names (Sales Volumes, Sales Price, EBITDA, etc.)
- **Column 1**: Units (kton, Eur/ton, LCU/ton, EUR, %, etc.)
- **Column 2+**: Data values
- **Headers**: Entities (Portugal, Tunisia, Brazil) or Temporal (Aug-25, Budget)

**Examples**: Tables 3-6 (Pages 3-4)

**Detection Signature:**
- `metric_ratio > 0.5` (68-80% in practice)
- `aspect_ratio < 2.0` (more columns than rows)
- Entity/temporal patterns in headers

**Unit Extraction Strategy**: Column 1 statistical analysis (Phase 2.7.3)

**Current Status**: ✅ **Working correctly** - 96.77% accuracy on Pages 20-21

---

### Type B: Entity-Column Tables with Junk Column 0 ❌ BROKEN

**Structure:**
- **Column 0**: Numeric junk/indices (14.003, 8.430, 26, 11, 127)
- **Column 1**: Entity names (Portugal, Portugal Cement, Portugal Madeira)
- **Column 2+**: Data values
- **Headers**: Metric categories (Total R SUSTAINING, Total D DEVELOPMENT, IFRS 16)

**Examples**: Tables 1-2 (Pages 1-2)

**Detection Signature:**
- `col_0: numeric_ratio = 87-100%` (pure numbers)
- `col_1: entity_ratio > 50%` (entity names)
- `aspect_ratio > 1.5` (tall tables)

**Problem**: Currently detected as "normal" table, triggering incorrect unit extraction that treats Column 1 entities as units!

**Unit Extraction Strategy**: TBD - units not found in first 3 rows. Need to:
1. Check if units are in metric names (header row)
2. Check for dedicated unit row beyond row 2
3. Parse from data cells as fallback

**Current Status**: ❌ **Broken** - 80.82% unit population (entities being used as units)

---

### Type C: Normal Metric-Entity Tables ⚠️ BORDERLINE

**Structure:**
- **Column 0**: Metric names (EBITDA IFRS, Income Tax, Net interest expenses, CAPEX)
- **Column 1+**: Data values
- **Headers**: Entities (GROUP, PORTUGAL, ANGOLA, TUNISIA)

**Examples**: Tables 7-8 (Pages 5-6)

**Detection Signature:**
- `metric_ratio = 40-50%` (borderline - some metrics not recognized)
- `col_1: numeric_ratio > 70%` (data values)
- `aspect_ratio > 1.5`

**Problem**: Metric detection threshold (0.5) too high, missing some financial metrics

**Unit Extraction Strategy**:
1. Check for dedicated unit row (row 0-2)
2. Parse from metric names (e.g., "CAPEX (EUR million)")
3. Parse from data cells

**Current Status**: ⚠️ **Partial** - Detected correctly but metric patterns incomplete

---

### Type D: Page 23 Target Table 🎯 PENDING

**Structure**: Unknown - awaiting test results

**Expected**: Normal table with entities in columns, metrics in rows, units in dedicated row

**Current Status**: 🎯 **Testing in progress**

---

## 🔧 Comprehensive Solution Design

### Phase 1: Enhanced Multi-Column Analysis

```python
def _analyze_column(cells, col_idx, metric_patterns, entity_patterns, unit_patterns):
    """Analyze single column content with multiple pattern types."""

    col_cells = [c for c in cells if c.start_col_offset_idx == col_idx and not c.column_header]

    metric_count = 0
    entity_count = 0
    unit_count = 0
    numeric_count = 0

    for cell in col_cells:
        if any(p.upper() in cell.text.upper() for p in metric_patterns):
            metric_count += 1
        elif any(p.upper() in cell.text.upper() for p in entity_patterns):
            entity_count += 1
        elif any(p.lower() in cell.text.lower() for p in unit_patterns):
            unit_count += 1
        elif _is_numeric_value(cell.text):
            numeric_count += 1

    total = len(col_cells)

    return {
        'metric_count': metric_count,
        'entity_count': entity_count,
        'unit_count': unit_count,
        'numeric_count': numeric_count,
        'total': total,
        'metric_ratio': metric_count / total if total > 0 else 0,
        'entity_ratio': entity_count / total if total > 0 else 0,
        'unit_ratio': unit_count / total if total > 0 else 0,
        'numeric_ratio': numeric_count / total if total > 0 else 0,
    }
```

### Phase 2: Enhanced Orientation Detection

```python
def _detect_table_orientation_v2(table_cells, num_rows, num_cols, unit_patterns):
    """Enhanced 4-type detection with multi-column analysis."""

    # Analyze first 3 columns
    col_0 = _analyze_column(table_cells, 0, metric_patterns, entity_patterns, unit_patterns)
    col_1 = _analyze_column(table_cells, 1, metric_patterns, entity_patterns, unit_patterns)
    col_2 = _analyze_column(table_cells, 2, ...) if num_cols > 2 else None

    aspect_ratio = num_rows / num_cols if num_cols > 0 else 1.0

    # PRIORITY 1: Type A - Transposed Metric-Entity
    if (col_0['metric_ratio'] > 0.4 and  # LOWERED from 0.5
        col_1['unit_ratio'] > 0.5):
        orientation = 'transposed_metric'
        confidence = min(col_0['metric_ratio'] + col_1['unit_ratio'], 0.95)
        extraction_strategy = 'column_1_units'

    # PRIORITY 2: Type B - Entity-Column with Junk Column 0
    elif (col_0['numeric_ratio'] > 0.7 and
          col_1['entity_ratio'] > 0.5 and
          aspect_ratio > 1.5):
        orientation = 'entity_column_junk'
        confidence = 0.90
        extraction_strategy = 'skip_col_0_find_units'

    # PRIORITY 3: Type C - Normal Metric-Entity
    elif (col_0['metric_ratio'] > 0.3 and  # LOWERED from 0.5
          col_1['numeric_ratio'] > 0.5):
        orientation = 'normal_metric'
        confidence = 0.85
        extraction_strategy = 'dedicated_row_or_metric_names'

    # PRIORITY 4: Fallback
    else:
        orientation = 'unknown'
        confidence = 0.50
        extraction_strategy = 'fallback_parse_cells'

    return orientation, confidence, extraction_strategy
```

### Phase 3: Type-Specific Unit Extraction

```python
def _extract_units_by_type(table_cells, orientation, unit_patterns):
    """Route to appropriate unit extraction strategy based on detected type."""

    if orientation == 'transposed_metric':
        # EXISTING - Column 1 statistical analysis
        return _extract_units_transposed_column_1(table_cells, unit_patterns)

    elif orientation == 'entity_column_junk':
        # NEW - Skip Column 0, find units elsewhere
        return _extract_units_entity_column_junk(table_cells, unit_patterns)

    elif orientation == 'normal_metric':
        # EXISTING but needs improvement
        return _extract_units_normal(table_cells, unit_patterns)

    else:
        # Fallback
        return {}

def _extract_units_entity_column_junk(table_cells, unit_patterns):
    """
    Extract units for Type B tables (junk column 0, entities in column 1).

    Strategy:
    1. Check column headers for unit patterns
    2. Check rows 3-5 for dedicated unit row (beyond typical row 0-2)
    3. Parse from metric names if present
    4. Fallback to cell-level parsing
    """

    units = {}

    # Strategy 1: Check column headers
    headers = [c for c in table_cells if c.column_header]
    for header in headers:
        if header.text:
            # Check for pattern like "Total R SUSTAINING (EUR million)"
            match = re.search(r'\(([^)]+)\)', header.text)
            if match and any(p.lower() in match.group(1).lower() for p in unit_patterns):
                units[header.start_col_offset_idx] = match.group(1).strip()

    # Strategy 2: Check rows 3-5 for unit row
    if not units:
        for row_idx in [3, 4, 5]:
            row_cells = [c for c in table_cells if c.start_row_offset_idx == row_idx]
            unit_count = sum(1 for c in row_cells
                           if c.text and any(p.lower() in c.text.lower() for p in unit_patterns))

            if unit_count / len(row_cells) > 0.70:  # 70% threshold
                for cell in row_cells:
                    if cell.text:
                        units[cell.start_col_offset_idx] = cell.text.strip()
                return units

    return units
```

---

## 📋 Implementation Plan

### Step 1: Wait for Page 23 Results ⏳
- Understand Type D structure
- Validate normal table unit extraction

### Step 2: Implement Enhanced Detection 🔨
- Add `_analyze_column()` helper
- Update `_detect_table_orientation()` → v2
- Lower metric detection threshold (0.5 → 0.3-0.4)

### Step 3: Implement Type B Handler 🔨
- Add `_extract_units_entity_column_junk()`
- Test on Tables 1-2 (chunk PDF)
- Target: 90%+ unit population

### Step 4: Expand Metric Patterns 📝
- Add more financial metric keywords
- Handle partial matches better
- Improve Type C detection (40% → 60%+ metric_ratio)

### Step 5: Full Validation ✅
- Test on chunk PDF (all 8 tables)
- Test on full PDF (all pages)
- Validate >85% accuracy across ALL table types

---

## 🎯 Success Criteria

1. **Type A (Transposed)**: Maintain 96.77% accuracy
2. **Type B (Entity-Column Junk)**: Achieve 90%+ accuracy (currently 80.82%)
3. **Type C (Normal)**: Achieve 85%+ accuracy
4. **Type D (Page 23)**: Achieve 85%+ accuracy
5. **Overall**: >90% average accuracy across all types

---

## 📊 Current Status

- **Phase 2.7.4 Implementation**: ✅ Complete (orientation detection + normal extraction)
- **Type A Support**: ✅ Working
- **Type B Support**: ❌ Broken (incorrect detection)
- **Type C Support**: ⚠️ Partial (borderline metric ratio)
- **Type D Support**: 🎯 Testing in progress
- **Next**: Await Page 23 results, then implement enhanced v2 detection
