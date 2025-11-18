# Data Dictionary - {{Project/Epic Name}}

**Generated:** {{date}}
**Source:** {{data_source}} ({{row_count}} rows)
**Purpose:** {{purpose_description}}
**Story:** {{story_id}} - {{story_name}}

---

## Available Metrics

| Metric | Sample Value | Notes |
|--------|--------------|-------|
| {{metric_1}} | {{sample_value_1}} | {{description_1}} |
| {{metric_2}} | {{sample_value_2}} | {{description_2}} |
| {{metric_3}} | {{sample_value_3}} | {{description_3}} |

**Total Unique Metrics:** {{metric_count}}

**Full Metrics List:**
- {{metric_1}} ⭐
- {{metric_2}}
- {{metric_3}}
- {{metric_4}}
- {{metric_5}} ⭐
- [... complete list]

⭐ = Core metrics for analytical queries

---

## Available Periods

### Well-Formed Periods ({{period_format}} Format)

| Period | Type | Description |
|--------|------|-------------|
| {{period_1}} | {{type_1}} | {{description_1}} |
| {{period_2}} | {{type_2}} | {{description_2}} |
| {{period_3}} | {{type_3}} | {{description_3}} |

**Well-Formed Period Count:** {{period_count}} periods

### Period Mappings

{{Period normalization rules or conversions}}

| Query Period | Maps To |
|--------------|---------|
| {{query_period_1}} | {{mapped_periods_1}} |
| {{query_period_2}} | {{mapped_periods_2}} |

**Note:** {{special_period_notes}}

**Total Unique Periods:** {{total_periods}} (includes {{malformed_notes}})

---

## Available Entities

| Entity | Aliases | Sample Data Available |
|--------|---------|----------------------|
| {{entity_1}} | {{aliases_1}} | {{sample_data_1}} |
| {{entity_2}} | {{aliases_2}} | {{sample_data_2}} |
| {{entity_3}} | {{aliases_3}} | {{sample_data_3}} |

**Total Unique Entities:** {{entity_count}}

**Full Entities List:**
- {{entity_1}} ⭐
- {{entity_2}}
- {{entity_3}} ({{alias}})
- [... complete list with aliases]

⭐ = Core entities frequently queried

---

## Data Schema

### Table Structure

**Primary Table:** {{table_name}}

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| {{column_1}} | {{type_1}} | {{description_1}} | {{example_1}} |
| {{column_2}} | {{type_2}} | {{description_2}} | {{example_2}} |
| {{column_3}} | {{type_3}} | {{description_3}} | {{example_3}} |

**Indexes:** {{index_list}}

---

## Limitations

**Data Coverage:**
- {{limitation_1}}
- {{limitation_2}}
- {{limitation_3}}

**Data Quality Issues:**
- {{quality_issue_1}}
- {{quality_issue_2}}

**Missing Data:**
- {{missing_data_1}}
- {{missing_data_2}}

**Known Issues:**
- {{known_issue_1}}
- {{known_issue_2}}

---

## Query Examples

### Example 1: {{query_type_1}}

```sql
{{example_query_1}}
```

**Expected Result:** {{expected_result_1}}

### Example 2: {{query_type_2}}

```sql
{{example_query_2}}
```

**Expected Result:** {{expected_result_2}}

---

## Usage Guidelines

**When Creating Test Queries:**
- {{guideline_1}}
- {{guideline_2}}
- {{guideline_3}}

**Validation Checklist:**
- [ ] Metric exists in "Available Metrics" section
- [ ] Period exists in "Available Periods" section
- [ ] Entity exists in "Available Entities" section
- [ ] Query aligns with data schema
- [ ] Expected result accounts for known limitations

---

## Change Log

**{{date}}:** Initial data dictionary created from {{source}}

---

**Last Updated:** {{date}}
**Maintained By:** {{maintainer}}
**Review Frequency:** {{review_frequency}}
