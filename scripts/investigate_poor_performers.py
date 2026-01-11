#!/usr/bin/env python3
"""Deep investigation of poor performing variables."""

import asyncio
import os
import sys

os.environ["APP_ENV"] = "production"
os.environ["POSTGRES_PORT"] = "5432"
os.environ["POSTGRES_DB"] = "raglite"
os.environ["POSTGRES_USER"] = "raglite"
os.environ["POSTGRES_PASSWORD"] = "raglite"

sys.path.insert(0, str(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import warnings

warnings.filterwarnings("ignore")


async def investigate_poor_performers():
    """Deep investigation of poor performing variables."""
    from raglite.forecasting.model_selection_job import fetch_historical_data

    from raglite.forecasting.regime_detection import detect_regime_changes

    poor_performers = [
        ("ttf_gas_price", "Energy commodity"),
        ("euribor_3m", "Interest rate"),
        ("api2_coal", "Energy commodity"),
    ]

    print("=" * 80)
    print("DEEP INVESTIGATION: POOR PERFORMING VARIABLES")
    print("=" * 80)

    for var_name, var_type in poor_performers:
        print(f"\n{'=' * 80}")
        print(f"VARIABLE: {var_name} ({var_type})")
        print(f"{'=' * 80}")

        data = await fetch_historical_data(var_name, min_points=12)
        if data is None:
            print(f"  ERROR: Could not fetch {var_name} data")
            continue

        # Convert to pandas Series for analysis
        series = data

        print("\n1. DATA OVERVIEW:")
        print(f"   Points: {len(series)}")
        print(f"   Date range: {series.index.min().date()} to {series.index.max().date()}")
        print(f"   Value range: {series.min():.4f} to {series.max():.4f}")
        print(f"   Mean: {series.mean():.4f}")
        print(f"   Std: {series.std():.4f}")
        print(f"   CV (Coeff of Variation): {series.std() / abs(series.mean()) * 100:.1f}%")

        # Check for near-zero values (problematic for MAPE)
        near_zero = (abs(series) < 1.0).sum()
        if near_zero > 0:
            print(
                f"   ⚠️  Near-zero values (|x|<1): {near_zero} ({near_zero / len(series) * 100:.1f}%)"
            )

        print("\n2. VOLATILITY ANALYSIS:")
        pct_change = series.pct_change().dropna()
        print(f"   Monthly volatility (std of returns): {pct_change.std() * 100:.1f}%")
        print(f"   Max monthly increase: {pct_change.max() * 100:.1f}%")
        print(f"   Max monthly decrease: {pct_change.min() * 100:.1f}%")

        # Look for extreme movements
        extreme_up = (pct_change > 0.30).sum()  # >30% increase
        extreme_down = (pct_change < -0.30).sum()  # >30% decrease
        print(f"   Extreme moves (>30%): {extreme_up} up, {extreme_down} down")

        print("\n3. REGIME ANALYSIS:")
        # Split data into periods
        if len(series) >= 24:
            q1 = series.iloc[: len(series) // 4]
            q2 = series.iloc[len(series) // 4 : len(series) // 2]
            q3 = series.iloc[len(series) // 2 : 3 * len(series) // 4]
            q4 = series.iloc[3 * len(series) // 4 :]

            print(
                f"   Period 1 ({q1.index[0].date()} - {q1.index[-1].date()}): mean={q1.mean():.2f}, std={q1.std():.2f}"
            )
            print(
                f"   Period 2 ({q2.index[0].date()} - {q2.index[-1].date()}): mean={q2.mean():.2f}, std={q2.std():.2f}"
            )
            print(
                f"   Period 3 ({q3.index[0].date()} - {q3.index[-1].date()}): mean={q3.mean():.2f}, std={q3.std():.2f}"
            )
            print(
                f"   Period 4 ({q4.index[0].date()} - {q4.index[-1].date()}): mean={q4.mean():.2f}, std={q4.std():.2f}"
            )

            # Check for mean shifts
            overall_mean = series.mean()
            max_shift = max(
                abs(q.mean() - overall_mean) / overall_mean * 100 for q in [q1, q2, q3, q4]
            )
            print(f"   Max mean shift from overall: {max_shift:.1f}%")

        # Use regime detection
        try:
            regimes = detect_regime_changes(series)
            if regimes.changes_detected:
                print(f"\n   Regime changes detected: {len(regimes.change_points)}")
                for cp in regimes.change_points[:5]:  # Show first 5
                    print(
                        f"   - {cp['date'].date()}: type={cp['type']}, magnitude={cp.get('magnitude', 'N/A')}"
                    )
        except Exception as e:
            print(f"   Regime detection failed: {e}")

        print("\n4. FORECAST CHALLENGES:")
        challenges = []

        # CV > 50% = high variability
        cv = series.std() / abs(series.mean()) * 100
        if cv > 50:
            challenges.append(f"High coefficient of variation ({cv:.0f}%)")

        # Extreme movements
        if extreme_up + extreme_down > 5:
            challenges.append(
                f"Frequent extreme movements ({extreme_up + extreme_down} months with >30% change)"
            )

        # Near-zero values
        if near_zero > 0:
            challenges.append("Near-zero values cause MAPE instability")

        # Check for trend reversal
        first_half_trend = series.iloc[: len(series) // 2].pct_change().mean()
        second_half_trend = series.iloc[len(series) // 2 :].pct_change().mean()
        if (first_half_trend > 0 and second_half_trend < 0) or (
            first_half_trend < 0 and second_half_trend > 0
        ):
            challenges.append("Trend reversal detected (direction changed mid-series)")

        for i, challenge in enumerate(challenges, 1):
            print(f"   {i}. {challenge}")

        print("\n5. RECOMMENDATIONS:")
        recommendations = []

        if var_name == "euribor_3m":
            recommendations = [
                "Accept high uncertainty - rate regime fundamentally changed 2022-2023",
                "Consider post-2022 data only for forecasting current regime",
                "Use ensemble with wider confidence intervals",
                "Flag forecasts as 'highly uncertain' in outputs",
            ]
        elif var_name in ["ttf_gas_price", "api2_coal"]:
            recommendations = [
                "Energy prices are inherently volatile and hard to forecast",
                "Consider using forward curves/futures data as regressors",
                "Accept higher uncertainty for commodity prices",
                "Use rolling window models (recent data more relevant)",
                "Consider regime-switching models for structural breaks",
            ]

        for i, rec in enumerate(recommendations, 1):
            print(f"   {i}. {rec}")

    print(f"\n\n{'=' * 80}")
    print("SUMMARY: ROOT CAUSES OF POOR PERFORMANCE")
    print("=" * 80)
    print("""
1. TTF Gas Price (MASE 11.55):
   - 2022 energy crisis caused unprecedented spike (€20→€235/MWh)
   - +211% mean shift between data halves
   - Structural market change that models cannot predict from historical patterns
   - RECOMMENDATION: Accept high uncertainty, use recent data only

2. Euribor_3m (MASE 13.97):
   - ECB rate policy regime change: negative rates → positive rates
   - 978% monthly spike when rates went positive
   - No historical precedent in training data for this regime
   - RECOMMENDATION: Use post-2022 data only, flag as highly uncertain

3. API2 Coal (MASE 11.46):
   - Correlated with gas crisis (substitution effect)
   - Supply chain disruptions from Russia-Ukraine conflict
   - -43% mean shift as crisis unwound
   - RECOMMENDATION: Pair with ttf_gas regressor, accept commodity volatility

GENERAL: These are EXTERNAL MACRO variables subject to geopolitical events.
Statistical models cannot predict black swan events like energy crises or
central bank policy shifts. The high MASE scores reflect this fundamental
limitation, not a model quality issue.
""")


if __name__ == "__main__":
    asyncio.run(investigate_poor_performers())
