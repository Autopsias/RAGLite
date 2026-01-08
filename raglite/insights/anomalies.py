"""Anomaly detection for financial time-series data.

Story 4.5: Statistical anomaly detection with Z-score analysis.
Target: ~50 lines per Tech Spec Section 3.3.
"""

import numpy as np

from raglite.shared.logging import get_logger
from raglite.shared.models import Anomaly, AnomalyDetectionResult, AnomalySeverity, TimeSeriesData

logger = get_logger(__name__)


def _extract_timeseries_data(timeseries: TimeSeriesData) -> tuple[list[float], list[str]]:
    """Extract values and date labels from time-series data.

    Args:
        timeseries: Time-series data with points

    Returns:
        Tuple of (values list, date labels list)
    """
    values = [p.value for p in timeseries.points]
    dates = [p.label or p.date.strftime("%Y-%m-%d") for p in timeseries.points]
    return values, dates


def _calculate_statistics(values: list[float]) -> tuple[float, float]:
    """Calculate mean and standard deviation.

    Args:
        values: List of numerical values

    Returns:
        Tuple of (mean, standard_deviation)
    """
    mean = float(np.mean(values))
    std = float(np.std(values))
    return mean, std


def _determine_severity(abs_z: float, include_minor: bool) -> AnomalySeverity | None:
    """Determine anomaly severity based on Z-score.

    Args:
        abs_z: Absolute value of Z-score
        include_minor: Whether to include MINOR severity (1.5 < |z| <= 2)

    Returns:
        AnomalySeverity if threshold met, None otherwise
    """
    if abs_z > 3:
        return AnomalySeverity.CRITICAL
    elif abs_z > 2:
        return AnomalySeverity.MODERATE
    elif include_minor and abs_z > 1.5:
        return AnomalySeverity.MINOR
    return None


def _get_detection_method(include_minor: bool) -> str:
    """Get detection method description based on threshold.

    Args:
        include_minor: Whether minor anomalies are included

    Returns:
        Detection method description string
    """
    threshold = "|z| > 1.5" if include_minor else "|z| > 2"
    return f"Z-score analysis (threshold: {threshold})"


def _log_detection_start(
    metric: str,
    data_points: int,
    mean: float,
    std: float,
    include_minor: bool,
    auto_explain: bool,
) -> None:
    """Log the start of anomaly detection process.

    Args:
        metric: Metric name
        data_points: Number of data points
        mean: Mean value
        std: Standard deviation
        include_minor: Whether minor anomalies included
        auto_explain: Whether auto-explanation enabled
    """
    min_threshold = 1.5 if include_minor else 2.0
    logger.info(
        "Detecting anomalies",
        extra={
            "metric": metric,
            "data_points": data_points,
            "mean": round(mean, 2),
            "std": round(std, 2),
            "include_minor": include_minor,
            "auto_explain": auto_explain,
            "min_threshold": min_threshold,
        },
    )


def _log_anomaly_detected(
    metric: str,
    date: str,
    value: float,
    z_score: float,
    severity: AnomalySeverity,
    magnitude_pct: float,
) -> None:
    """Log a detected anomaly.

    Args:
        metric: Metric name
        date: Date label
        value: Observed value
        z_score: Z-score
        severity: Anomaly severity
        magnitude_pct: Magnitude percentage
    """
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


async def _detect_anomalies_in_data(
    values: list[float],
    dates: list[str],
    metric: str,
    mean: float,
    std: float,
    include_minor: bool,
    auto_explain: bool,
) -> list[Anomaly]:
    """Detect anomalies in time-series data.

    Args:
        values: List of values
        dates: List of date labels
        metric: Metric name
        mean: Mean of distribution
        std: Standard deviation
        include_minor: Whether to include minor anomalies
        auto_explain: Whether to generate explanations

    Returns:
        List of detected anomalies
    """
    anomalies = []
    for value, date in zip(values, dates, strict=True):
        z_score = (value - mean) / std
        abs_z = abs(z_score)

        # AC2/AC3: Z-score thresholds for severity
        severity = _determine_severity(abs_z, include_minor)
        if severity is None:
            continue

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

        if auto_explain:
            anomaly.reason = await explain_anomaly(anomaly)

        anomalies.append(anomaly)
        _log_anomaly_detected(metric, date, value, z_score, severity, magnitude_pct)

    return anomalies


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

    values, dates = _extract_timeseries_data(timeseries)
    mean, std = _calculate_statistics(values)

    _log_detection_start(metric, len(values), mean, std, include_minor, auto_explain)

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

    # Detect anomalies
    anomalies = await _detect_anomalies_in_data(
        values, dates, metric, mean, std, include_minor, auto_explain
    )

    logger.info(
        "Anomaly detection complete",
        extra={
            "metric": metric,
            "anomalies_found": len(anomalies),
            "data_points_analyzed": len(values),
        },
    )

    detection_method = _get_detection_method(include_minor)

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
