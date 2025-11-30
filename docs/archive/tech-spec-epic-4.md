# Technical Specification: Epic 4 - Forecasting & Proactive Insights

**Epic:** Epic 4 - Forecasting & Proactive Insights
**Phase:** Phase 3 (concurrent with or after Epic 3)
**Goal:** Predictive intelligence and strategic recommendations via AI-powered forecasting
**Status:** NOT STARTED
**Version:** 1.0
**Date:** 2025-10-12
**Author:** Sarah (Product Owner)

---

## 1. Executive Summary

Epic 4 adds predictive intelligence to RAGLite, enabling time-series forecasting, anomaly detection, trend analysis, and proactive insight generation. The system autonomously surfaces risks, opportunities, and strategic priorities without user prompting.

**Target:** ~200-250 additional lines of Python code
**Timeline:** Concurrent with Epic 3 (Weeks 9-12 or 5-8)
**Approach:** Hybrid LLM + statistical forecasting (Prophet + Claude reasoning)

**Capabilities Enabled:**
- Financial forecasting (revenue, cash flow, expenses) with ±15% accuracy
- Anomaly detection (unexpected spikes, drops, outliers)
- Trend analysis (growth patterns, correlations)
- Proactive insights (risks, opportunities, recommendations)
- MCP tools: get_financial_forecast(), get_financial_insights()

---

## 2. Architecture Overview

### 2.1 Forecasting & Insights Architecture

```
┌────────────────────────────────────────────────────────┐
│  MCP Clients (Claude Code, Claude Desktop)           │
└────────────────────┬───────────────────────────────────┘
                     │ Model Context Protocol
┌────────────────────▼───────────────────────────────────┐
│  RAGLite Monolithic Server (main.py)                  │
│                                                        │
│  ┌───────────────────────────────────────────────────┐│
│  │  MCP Tools Layer                                  ││
│  │  • get_financial_forecast() (NEW)                ││
│  │  • get_financial_insights() (NEW)                ││
│  └───────────────────────────────────────────────────┘│
│                                                        │
│  ┌───────────────────────────────────────────────────┐│
│  │  Intelligence Layer (NEW ~200 lines)             ││
│  │                                                   ││
│  │  Forecasting Module (~100 lines)                 ││
│  │  ├─ forecasting/hybrid.py                        ││
│  │  │  • Prophet statistical forecasting            ││
│  │  │  • LLM reasoning for context/confidence       ││
│  │  └─ forecasting/timeseries_extract.py            ││
│  │                                                   ││
│  │  Insights Module (~100 lines)                    ││
│  │  ├─ insights/anomalies.py                        ││
│  │  │  • Statistical anomaly detection              ││
│  │  └─ insights/trends.py                           ││
│  │     • Trend analysis + LLM reasoning             ││
│  └───────────────────────────────────────────────────┘│
│                                                        │
│  ┌───────────────────────────────────────────────────┐│
│  │  Business Logic (Epic 1-3 ✅)                    ││
│  │  ├─ ingestion/, retrieval/, orchestration/       ││
│  └───────────────────────────────────────────────────┘│
└────────────────────┬───────────────────────────────────┘
                     │
┌────────────────────▼───────────────────────────────────┐
│  Data Layer                                            │
│  ├─ Qdrant (Vector DB) ✅                             │
│  ├─ Neo4j (Knowledge Graph) - CONDITIONAL Epic 2      │
│  └─ Time-Series Data Store (embedded in Qdrant)       │
└────────────────────────────────────────────────────────┘
```

### 2.2 Hybrid Forecasting Approach

**Combines:**
1. **Prophet (Statistical):** Time-series forecasting with seasonality, trends
2. **Claude API (LLM):** Contextual reasoning, confidence intervals, explanations

**Why Hybrid?**
- Prophet: Accurate numerical predictions (±10-15% for clean data)
- LLM: Contextual insights ("Revenue forecast is conservative due to new product launch in Q4")
- Best of both: Statistical rigor + human-like reasoning

---

## 3. Component Specifications

### 3.1 Time-Series Extraction (raglite/forecasting/timeseries_extract.py ~50 lines)

**Purpose:** Extract time-series financial data from documents for forecasting.

**Key Function:**
```python
async def extract_timeseries(docs: List[str]) -> TimeSeriesData:
    """Extract time-series data from financial documents.

    Args:
        docs: List of document IDs or filenames

    Returns:
        TimeSeriesData with metric_name, values, timestamps

    Extracts:
        - Revenue (monthly, quarterly)
        - Cash flow (monthly)
        - Expense categories (quarterly)
        - Headcount (quarterly)
    """
```

**Implementation Approach:**
1. Use Epic 1 retrieval to find time-series mentions
2. LLM extraction: "Extract all revenue values with dates from these chunks"
3. Normalize to consistent time intervals (monthly, quarterly)
4. Handle fiscal period labels: "Q3 FY24" → 2024-Q3

**NFRs:**
- Extraction accuracy: 90%+ (validated on sample docs)
- Processing time: <2 min for 5 documents

**Testing:**
- Unit tests: Mock document chunks with time-series data
- Integration tests: Extract from real financial PDFs
- Accuracy tests: Manual validation on 50+ data points

---

### 3.2 Hybrid Forecasting Engine (raglite/forecasting/hybrid.py ~100 lines)

**Purpose:** Generate financial forecasts using Prophet + Claude reasoning.

**Key Functions:**
```python
async def generate_forecast(
    metric: str,
    historical_data: TimeSeriesData,
    periods_ahead: int = 4
) -> ForecastResult:
    """Generate forecast for financial metric.

    Args:
        metric: Metric name (e.g., "revenue", "cash_flow")
        historical_data: Time-series data (dates, values)
        periods_ahead: Number of periods to forecast (default 4 quarters)

    Returns:
        ForecastResult with predictions, confidence intervals, reasoning

    Process:
        1. Statistical forecast (Prophet):
           - Fit model to historical data
           - Generate point predictions + confidence intervals
        2. LLM reasoning (Claude):
           - Analyze forecast context (trends, events)
           - Generate confidence rationale
           - Identify risks/opportunities
    """

async def explain_forecast(forecast: ForecastResult, context: str) -> str:
    """Use LLM to explain forecast with context.

    Args:
        forecast: Prophet forecast result
        context: Retrieved document context (new products, market changes)

    Returns:
        Natural language explanation with confidence rationale
    """
```

**Prophet Configuration:**
```python
from prophet import Prophet

model = Prophet(
    yearly_seasonality=True,
    quarterly_seasonality=True,
    changepoint_prior_scale=0.05  # Conservative (prevent overfitting)
)

# Fit to historical data
model.fit(df_historical)

# Generate forecast
future = model.make_future_dataframe(periods=4, freq='Q')
forecast = model.predict(future)

# Extract predictions + confidence intervals
predictions = forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']]
```

**NFRs:**
- NFR10: ±15% forecast accuracy (validated on historical data)
- FR19: Confidence intervals included in all forecasts
- Processing time: <30s for 4-quarter forecast

**Testing:**
- Unit tests: Mock Prophet model
- Integration tests: Forecast on real historical data
- Accuracy tests: Compare predictions to actuals (±15% threshold)

---

### 3.3 Anomaly Detection (raglite/insights/anomalies.py ~50 lines)

**Purpose:** Detect anomalies and outliers in financial data.

**Key Function:**
```python
async def detect_anomalies(
    metric: str,
    timeseries: TimeSeriesData
) -> List[Anomaly]:
    """Detect anomalies using statistical thresholds.

    Args:
        metric: Metric name
        timeseries: Historical data

    Returns:
        List of Anomaly objects (date, value, severity, reason)

    Method:
        - Z-score analysis (outliers > 2 std deviations)
        - Trend deviation (sudden spikes/drops)
        - LLM contextual reasoning for anomaly explanation
    """
```

**Anomaly Detection Logic:**
```python
import numpy as np

# Calculate Z-scores
mean = np.mean(values)
std = np.std(values)
z_scores = [(v - mean) / std for v in values]

# Flag anomalies (|z| > 2)
anomalies = [
    Anomaly(
        date=dates[i],
        value=values[i],
        z_score=z_scores[i],
        severity="critical" if abs(z_scores[i]) > 3 else "moderate"
    )
    for i, z in enumerate(z_scores) if abs(z) > 2
]

# LLM explains anomaly
explanation = await explain_anomaly(anomaly, context)
```

**NFRs:**
- Anomaly detection accuracy: 85%+ (validated on sample data with known outliers)
- False positive rate: <10%

**Testing:**
- Unit tests: Synthetic data with known anomalies
- Integration tests: Real financial data with expert-labeled outliers
- Accuracy tests: Precision/recall metrics

---

### 3.4 Trend Analysis (raglite/insights/trends.py ~50 lines)

**Purpose:** Identify growth patterns, correlations, and trends.

**Key Function:**
```python
async def analyze_trends(
    metrics: List[str],
    timeseries_data: Dict[str, TimeSeriesData]
) -> List[Trend]:
    """Analyze trends and patterns in financial data.

    Args:
        metrics: List of metric names to analyze
        timeseries_data: Historical data for each metric

    Returns:
        List of Trend objects (metric, direction, magnitude, correlation)

    Detects:
        - Growth patterns (CAGR, QoQ growth rate)
        - Cyclical trends (seasonality)
        - Correlations (e.g., marketing spend vs revenue)
    """
```

**Trend Analysis Logic:**
```python
# Calculate CAGR (Compound Annual Growth Rate)
def calculate_cagr(start_value, end_value, years):
    return ((end_value / start_value) ** (1 / years)) - 1

# Detect correlation
from scipy.stats import pearsonr
correlation, p_value = pearsonr(metric_1_values, metric_2_values)

# LLM contextual reasoning
trend_explanation = await explain_trend(
    metric, cagr, correlation, context
)
```

**NFRs:**
- Trend detection accuracy: 90%+ (expert validation)
- Processing time: <10s for 5 metrics

**Testing:**
- Unit tests: Synthetic data with known trends
- Integration tests: Real financial data with expert analysis
- Accuracy tests: Compare to human expert trend identification

---

### 3.5 Proactive Insight Generation (integrated across modules ~50 lines)

**Purpose:** Synthesize anomalies, trends, and forecasts into actionable insights.

**Key Function:**
```python
async def generate_insights(
    anomalies: List[Anomaly],
    trends: List[Trend],
    forecasts: List[ForecastResult]
) -> List[Insight]:
    """Generate prioritized insights from analysis.

    Args:
        anomalies: Detected anomalies
        trends: Identified trends
        forecasts: Generated forecasts

    Returns:
        List of Insight objects ranked by priority

    Insight Types:
        - RISK: Negative trends, forecast downturn, anomalies
        - OPPORTUNITY: Positive trends, growth potential
        - ANOMALY: Unexplained outliers requiring investigation
        - STRATEGIC_PRIORITY: High-impact areas needing attention
    """
```

**LLM-Powered Insight Synthesis:**
```python
prompt = f"""
Analyze this financial data and generate actionable insights:

Anomalies:
- Q3 marketing spend increased 30% YoY with no revenue increase

Trends:
- Revenue CAGR: +15%
- Marketing spend CAGR: +25%
- ROI declining trend (0.8 → 0.6)

Forecasts:
- Q4 revenue forecast: $12M (±$1.5M)
- Marketing spend projected to exceed budget by 20%

Generate 3-5 prioritized insights with:
1. Category (RISK, OPPORTUNITY, STRATEGIC_PRIORITY)
2. Summary (1 sentence)
3. Supporting data
4. Recommended action
"""

# Claude generates insights
insights = await claude_api.messages.create(
    model="claude-3-7-sonnet-20250219",
    max_tokens=1000,
    messages=[{"role": "user", "content": prompt}]
)
```

**NFRs:**
- Insight usefulness: 75%+ rated useful/actionable (user testing)
- Insight accuracy: 80%+ alignment with expert analysis

**Testing:**
- Unit tests: Mock anomalies/trends/forecasts
- Integration tests: End-to-end insight generation
- User testing: Relevance and usefulness validation

---

## 4. API Contracts

### 4.1 New MCP Tool: get_financial_forecast

**Input:**
```json
{
  "metric": "revenue",
  "periods_ahead": 4,
  "time_unit": "quarter"
}
```

**Output:**
```json
{
  "metric": "revenue",
  "historical_data": [
    {"date": "2024-Q1", "value": 10.0},
    {"date": "2024-Q2", "value": 10.5},
    {"date": "2024-Q3", "value": 12.0}
  ],
  "forecast": [
    {"date": "2024-Q4", "value": 12.8, "lower": 11.3, "upper": 14.3},
    {"date": "2025-Q1", "value": 13.5, "lower": 11.8, "upper": 15.2},
    {"date": "2025-Q2", "value": 14.2, "lower": 12.1, "upper": 16.3},
    {"date": "2025-Q3", "value": 15.0, "lower": 12.5, "upper": 17.5}
  ],
  "confidence_reasoning": "Forecast assumes continued growth trend (+15% CAGR) with conservative confidence intervals due to new product launch uncertainty in Q4.",
  "basis": "Prophet model trained on 8 quarters of historical data (Q1 2022 - Q3 2024)",
  "accuracy_estimate": "±15% (NFR10 target)"
}
```

---

### 4.2 New MCP Tool: get_financial_insights

**Input:**
```json
{
  "category": "all",
  "time_period": "current_quarter",
  "limit": 5
}
```

**Output:**
```json
{
  "insights": [
    {
      "priority": 1,
      "category": "RISK",
      "summary": "Marketing spend increased 30% YoY with no corresponding revenue increase",
      "supporting_data": {
        "marketing_spend_q3_2023": 2.0,
        "marketing_spend_q3_2024": 2.6,
        "revenue_q3_2023": 10.0,
        "revenue_q3_2024": 10.2
      },
      "recommended_action": "Review marketing campaign effectiveness and ROI by channel",
      "sources": ["Q3_2024_Report.pdf (p.15)", "Marketing_Budget_2024.xlsx"]
    },
    {
      "priority": 2,
      "category": "OPPORTUNITY",
      "summary": "Cloud infrastructure costs trending 40% under budget with stable usage",
      "supporting_data": {
        "cloud_budget_q3": 5.0,
        "cloud_actual_q3": 3.0,
        "usage_trend": "stable"
      },
      "recommended_action": "Reallocate savings to high-ROI initiatives like product development",
      "sources": ["Cloud_Costs_Q3_2024.pdf"]
    }
  ],
  "total_insights_generated": 12,
  "filtered_by": "priority (top 5)",
  "generated_at": "2024-10-12T14:30:00Z"
}
```

---

## 5. NFR Validation Criteria

### Forecast Accuracy (NFR10)
**Target:** ±15% for key indicators (revenue, cash flow, expenses)

**Validation Method:**
- Backtesting: Train on historical data (Q1 2022 - Q1 2024), predict Q2-Q3 2024
- Compare predictions to actuals: |predicted - actual| / actual ≤ 15%
- Test on 20+ forecast scenarios

### Insight Usefulness (MVP Success Criteria)
**Target:** 75%+ rated useful/actionable by users

**Validation Method:**
- User testing: 10+ users review 20+ generated insights
- Rating scale: 1-5 (useful, actionable, relevant)
- Calculate: (Ratings ≥4 / Total ratings) × 100%

### Recommendation Alignment (MVP Success Criteria)
**Target:** 80%+ alignment with expert analysis

**Validation Method:**
- Expert validation: Financial analyst reviews 20+ recommendations
- Binary: Aligned (1) or Not Aligned (0)
- Calculate: (Aligned recommendations / Total) × 100%

---

## 6. Implementation Timeline

### Weeks 9-10 (or 5-6): Time-Series & Forecasting
**Stories:**
- Story 4.1: Time-Series Data Extraction
- Story 4.2: Forecasting Engine Implementation
- Story 4.3: Automated Forecast Updates
- Story 4.4: Forecast Query Tool (MCP)

**Deliverables:**
- `raglite/forecasting/timeseries_extract.py`
- `raglite/forecasting/hybrid.py` (Prophet + Claude)
- MCP tool: get_financial_forecast()
- Forecast accuracy validation: ±15%

---

### Weeks 11-12 (or 7-8): Insights & Recommendations
**Stories:**
- Story 4.5: Anomaly Detection
- Story 4.6: Trend Analysis & Pattern Recognition
- Story 4.7: Proactive Insight Generation
- Story 4.8: Strategic Recommendation Engine
- Story 4.9: Proactive Insights Tool (MCP)
- Story 4.10: Forecasting & Insights Test Suite

**Deliverables:**
- `raglite/insights/anomalies.py`
- `raglite/insights/trends.py`
- MCP tool: get_financial_insights()
- User testing validation: 75%+ useful insights

**Success Criteria:**
- ±15% forecast accuracy on 20+ scenarios
- 75%+ insight usefulness (user testing)
- 80%+ recommendation alignment (expert validation)

---

## 7. Dependencies & Blockers

### External Dependencies

**New Technologies:**
- prophet 1.1.5 (Facebook time-series forecasting)
- scipy 1.11+ (statistical analysis, correlations)
- numpy ✅ (already dependency via sentence-transformers)

**Existing Dependencies (Epic 1-3):**
- Claude API ✅
- Qdrant ✅
- Epic 1 retrieval (for time-series extraction)

### Dependency on Epic 3 (LOW)

**Epic 4 can proceed independently of Epic 3.** However, if Epic 3 agentic framework exists, forecasting agent can integrate for multi-step analytical workflows.

**Recommended Order:**
1. Epic 4 (Weeks 9-12): Standalone forecasting + insights
2. Epic 3 integration (if time permits): Add forecasting agent to orchestration

---

## 8. Success Criteria

### Phase 3 Completion Criteria (End of Week 12 or 8)

**Must Meet (GO Criteria):**
1. ✅ ±15% forecast accuracy on 20+ scenarios (NFR10)
2. ✅ 75%+ insight usefulness (user testing, MVP criteria)
3. ✅ 80%+ recommendation alignment (expert validation, MVP criteria)
4. ✅ MCP tools (get_financial_forecast, get_financial_insights) functional
5. ✅ Automated forecast updates on document ingestion

**Decision Gate:**
- **IF** all criteria met → **PROCEED to Epic 5** (Production Readiness)
- **IF** forecast accuracy <10% → **REASSESS** (improve model, data quality)
- **IF** insight usefulness <60% → **REFINE** (improve LLM prompts, insight ranking)

---

## 9. Risks & Mitigation

### Risk 1: Forecast Accuracy Insufficient (MEDIUM)
**Probability:** MEDIUM (±15% ambitious for limited data)
**Impact:** HIGH (blocks MVP success criteria)

**Mitigation:**
1. Start with clean data (quarterly revenue, 8+ data points)
2. Conservative Prophet settings (prevent overfitting)
3. LLM qualifies forecast: "Forecast is conservative due to limited data"
4. If accuracy <10%, extend data collection period (request more historical docs)

### Risk 2: Insight Usefulness Low (MEDIUM)
**Probability:** MEDIUM (LLM insights may be generic)
**Impact:** MEDIUM (reduces MVP value)

**Mitigation:**
1. User testing early (Week 10): Validate sample insights
2. Iterative prompt engineering: Improve specificity and actionability
3. Priority ranking: Focus on high-impact insights (top 3-5)
4. Context grounding: Insights always cite supporting data

### Risk 3: Limited Historical Data (HIGH)
**Probability:** HIGH (users may not have 2+ years of data)
**Impact:** MEDIUM (reduces forecast accuracy)

**Mitigation:**
1. Minimum data requirement: 8 quarters (2 years) for quarterly forecasts
2. Graceful degradation: If <8 data points, return "Insufficient data for forecast"
3. User guidance: "Upload historical financial reports for better forecasts"
4. Fallback: Simple trend extrapolation if Prophet fails

---

## 10. References

### Architecture Documents
- `docs/architecture/5-technology-stack-definitive.md` - Prophet, scipy
- `docs/architecture/8-phased-implementation-strategy-v11-simplified.md` - Phase 3 timeline

### PRD Documents
- `docs/prd/epic-4-forecasting-proactive-insights.md` - Epic 4 stories

### Research
- Prophet: https://facebook.github.io/prophet/
- Anthropic Contextual Retrieval (for insight generation)

---

**Document Version:** 1.0
**Created:** 2025-10-12
**Author:** Sarah (Product Owner)
**Next Update:** After Epic 3 completion (before Week 9 or 5)
