"""Anomaly detection for financial time-series data.

Story 4.5: Statistical anomaly detection with Z-score analysis.
Target: ~50 lines per Tech Spec Section 3.3.
"""

import numpy as np

from raglite.shared.logging import get_logger
from raglite.shared.models import Anomaly, AnomalyDetectionResult, AnomalySeverity, TimeSeriesData

logger = get_logger(__name__)


async def detect_anomalies(
    metric: str,
    timeseries: TimeSeriesData,
    *,
    include_minor: bool = False,
    auto_explain: bool = False,
) -> AnomalyDetectionResult:
    """Detect anomalies using statistical thresholds.

    Story 4.5 AC1-AC5: Statistical anomaly detection with Z-score analysis.

    Args:
        metric: Metric name (e.g., "revenue", "cash_flow", "expenses")
        timeseries: Historical time-series data from Story 4.1 extraction
        include_minor: If True, include MINOR severity anomalies (1.5 < |z| <= 2).
            Default False for backward compatibility. Useful for trend-based
            detection in Story 4.6 integration.
        auto_explain: If True, automatically generate LLM explanations for each
            detected anomaly. Default False to reduce API calls in bulk processing.
            Set True for interactive single-query scenarios.

    Returns:
        AnomalyDetectionResult containing:
          - anomalies: List of detected Anomaly objects
          - metric_name: Name of analyzed metric
          - data_points_analyzed: Number of data points processed
          - detection_method: "Z-score analysis (threshold: |z| > 2)" or
            "Z-score analysis (threshold: |z| > 1.5)" if include_minor=True

    Raises:
        ValueError: If timeseries has fewer than 3 data points

    Example:
        >>> from raglite.shared.models import TimeSeriesData, TimeSeriesPoint
        >>> from datetime import datetime
        >>> points = [TimeSeriesPoint(date=datetime(2024, i, 1), value=10+i*0.5) for i in range(1, 9)]
        >>> data = TimeSeriesData(metric_name="revenue", points=points)
        >>> result = await detect_anomalies("revenue", data)
        >>> print(len(result.anomalies))

        # With minor anomalies and auto-explanation:
        >>> result = await detect_anomalies("revenue", data, include_minor=True, auto_explain=True)
    """
    if len(timeseries.points) < 3:
        raise ValueError(
            f"Insufficient data: {len(timeseries.points)} points. Minimum 3 required for statistical analysis."
        )

    values = [p.value for p in timeseries.points]
    dates = [p.label or p.date.strftime("%Y-%m-%d") for p in timeseries.points]

    mean = float(np.mean(values))
    std = float(np.std(values))

    # Determine threshold based on include_minor flag
    min_threshold = 1.5 if include_minor else 2.0

    logger.info(
        "Detecting anomalies",
        extra={
            "metric": metric,
            "data_points": len(values),
            "mean": round(mean, 2),
            "std": round(std, 2),
            "include_minor": include_minor,
            "auto_explain": auto_explain,
            "min_threshold": min_threshold,
        },
    )

    # No variance = no anomalies
    if std == 0:
        logger.info(
            "No variance in data - no anomalies detected",
            extra={"metric": metric, "mean": mean},
        )
        return AnomalyDetectionResult(
            metric_name=metric,
            anomalies=[],
            data_points_analyzed=len(values),
            mean_value=mean,
            std_deviation=std,
        )

    # Calculate Z-scores and identify anomalies
    anomalies = []
    for value, date in zip(values, dates, strict=True):
        z_score = (value - mean) / std
        abs_z = abs(z_score)

        # AC2/AC3: Z-score thresholds for severity
        # CRITICAL: |z| > 3.0, MODERATE: |z| > 2.0, MINOR: |z| > 1.5 (if include_minor)
        if abs_z > 3:
            severity = AnomalySeverity.CRITICAL
        elif abs_z > 2:
            severity = AnomalySeverity.MODERATE
        elif include_minor and abs_z > 1.5:
            severity = AnomalySeverity.MINOR
        else:
            continue  # Not an anomaly

        magnitude_pct = ((value - mean) / mean * 100) if mean != 0 else 0.0

        anomaly = Anomaly(
            date=date,
            metric=metric,
            value=value,
            expected_value=round(mean, 2),
            z_score=round(z_score, 2),
            severity=severity,
            magnitude_pct=round(magnitude_pct, 1),
        )

        # Auto-explain if requested (reduces LLM API calls when False)
        if auto_explain:
            anomaly.reason = await explain_anomaly(anomaly)

        anomalies.append(anomaly)

        # AC4: Structured logging for each detected anomaly
        logger.info(
            "Anomaly detected",
            extra={
                "metric": metric,
                "date": date,
                "value": value,
                "z_score": round(z_score, 2),
                "severity": severity.value,
                "magnitude_pct": round(magnitude_pct, 1),
            },
        )

    logger.info(
        "Anomaly detection complete",
        extra={
            "metric": metric,
            "anomalies_found": len(anomalies),
            "data_points_analyzed": len(values),
        },
    )

    # Set detection method based on threshold used
    detection_method = (
        "Z-score analysis (threshold: |z| > 1.5)"
        if include_minor
        else "Z-score analysis (threshold: |z| > 2)"
    )

    return AnomalyDetectionResult(
        metric_name=metric,
        anomalies=anomalies,
        data_points_analyzed=len(values),
        detection_method=detection_method,
        mean_value=round(mean, 2),
        std_deviation=round(std, 2),
    )


async def explain_anomaly(anomaly: Anomaly) -> str:
    """Generate LLM-powered explanation for an anomaly.

    Story 4.5 AC4: Contextual reasoning for why anomaly occurred.

    Args:
        anomaly: Detected anomaly to explain

    Returns:
        LLM-generated explanation string

    Example:
        >>> explanation = await explain_anomaly(anomaly)
        >>> print(explanation)
        "Revenue in Q3 2024 was 45% above expected, likely due to seasonal factors..."
    """
    from raglite.shared.clients import get_mistral_client

    prompt = f"""Analyze this financial anomaly and provide a brief explanation (2-3 sentences):

Metric: {anomaly.metric}
Date: {anomaly.date}
Actual Value: {anomaly.value}
Expected Value: {anomaly.expected_value}
Deviation: {anomaly.magnitude_pct}% from expected
Z-Score: {anomaly.z_score} ({"above" if anomaly.z_score > 0 else "below"} average)
Severity: {anomaly.severity.value}

Provide possible business reasons for this deviation. Be specific but concise."""

    try:
        client = get_mistral_client()
        response = client.chat.complete(
            model="mistral-large-latest",
            messages=[{"role": "user", "content": prompt}],
        )
        explanation = response.choices[0].message.content if response.choices else ""

        logger.info(
            "Anomaly explanation generated",
            extra={
                "metric": anomaly.metric,
                "date": anomaly.date,
                "severity": anomaly.severity.value,
            },
        )

        return explanation.strip()
    except Exception as e:
        logger.warning(
            "Failed to generate anomaly explanation",
            extra={"metric": anomaly.metric, "date": anomaly.date, "error": str(e)},
        )
        return f"Anomaly detected: {anomaly.metric} value of {anomaly.value} deviates {anomaly.magnitude_pct}% from expected."
