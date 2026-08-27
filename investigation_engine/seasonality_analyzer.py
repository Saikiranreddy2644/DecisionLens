# investigation_engine/seasonality_analyzer.py

import pandas as pd
import numpy as np
from utils.constants import (
    MIN_SEASONALITY_WEEKS,
    MIN_SEASONALITY_TRANSACTIONS,
    SEASONALITY_CONSISTENCY_SATURATION,
    MAGNITUDE_SATURATION_STD,
)


def _add_year_week(df: pd.DataFrame, date_col: str = "Date") -> pd.DataFrame:
    """Same convention as the other analyzers — kept local so this module
    is self-contained."""
    df = df.copy()
    dates = pd.to_datetime(df[date_col], errors="coerce")
    iso = dates.dt.isocalendar()
    df["Year"] = iso["year"]
    df["Week"] = iso["week"]
    return df


def analyze_seasonality(
    processed_df: pd.DataFrame,
    store: str,
    category: str,
    year: int,
    week: int,
    metric: str = "Revenue",
) -> dict:
    """
    Investigates a single flagged Store+Category+Week anomaly for seasonality:
    is this week's performance consistent with what we'd expect for this
    calendar week (Week 26, Week 1, etc.) based on prior years?

    This analyzer has MUCH stricter data requirements than the others —
    it needs roughly one full year (~52 weeks) of prior history to even
    attempt to find a seasonal pattern. Without that, there's no meaningful
    seasonal baseline to compare against.

    magnitude: how much does this week deviate from the seasonal norm for
    this calendar week (across all prior years) — same z-score/saturation
    convention as the other analyzers.

    seasonal_consistency (this analyzer's version of specificity): how
    tightly does this calendar week repeat across prior years? A week that's
    rock-solid consistent (±5% every year) is different from a week that
    swings wildly (±40%). High consistency means a deviation is significant;
    low consistency means the deviation might just be normal variance for
    this week.
        seasonal_consistency = 1.0 - min(
            (std_of_prior_years / mean_of_prior_years) / SATURATION, 1.0
        )

    analyzer_score = magnitude * seasonal_consistency

    Returns a dict. If there isn't enough full-year history to establish a
    seasonal pattern, returns {"sufficient_data": False, "reason": ...,
    "analyzer_score": None} — None, not 0, so it's excluded (not counted)
    from the confidence formula's weighted average rather than treated as
    confidently finding nothing.
    """
    df = _add_year_week(processed_df)
    group_df = df[(df["Store"] == store) & (df["Category"] == category)]

    this_week = group_df[(group_df["Year"] == year) & (group_df["Week"] == week)]
    history = group_df[~((group_df["Year"] == year) & (group_df["Week"] == week))]

    # --- Sufficiency guards: much stricter than other analyzers ---
    if len(this_week) < MIN_SEASONALITY_TRANSACTIONS:
        return {
            "sufficient_data": False,
            "reason": f"Only {len(this_week)} transaction(s) this week (need {MIN_SEASONALITY_TRANSACTIONS}+)",
            "analyzer_score": None,
        }

    n_historical_weeks = history[["Year", "Week"]].drop_duplicates().shape[0]
    if n_historical_weeks < MIN_SEASONALITY_WEEKS:
        return {
            "sufficient_data": False,
            "reason": f"Only {n_historical_weeks} historical week(s) (need ~{MIN_SEASONALITY_WEEKS} for a full-year seasonal pattern)",
            "analyzer_score": None,
        }

    # --- Extract the seasonal baseline: all prior instances of this
    # calendar week (Week 26 in all other years, Week 1 in all other years, etc.) ---
    seasonal_history = history[history["Week"] == week].groupby(["Year", "Week"])[metric].sum()

    if len(seasonal_history) < 1:
        return {
            "sufficient_data": False,
            "reason": f"No prior occurrences of Week {week} in history",
            "analyzer_score": None,
        }


    seasonal_mean = seasonal_history.mean()
    seasonal_std = seasonal_history.std()

    # --- Check if we have enough variation to calculate consistency ---
    # If std is NaN or 0, we can't meaningfully assess seasonality
    if pd.isna(seasonal_std) or seasonal_std == 0:
        return {
            "sufficient_data": False,
            "reason": f"Insufficient seasonal variation (only {len(seasonal_history)} prior year(s) of Week {week}; need 2+ years for reliable seasonality pattern)",
            "analyzer_score": None,
    }

# --- Magnitude: how unusual is this week vs the seasonal baseline ---
    

    # --- Magnitude: how unusual is this week vs the seasonal baseline ---
    this_week_total = this_week[metric].sum()

    if seasonal_std and seasonal_std > 0:
        z = (this_week_total - seasonal_mean) / seasonal_std
    else:
        z = 0.0 if this_week_total == seasonal_mean else np.inf
    magnitude = min(abs(z) / MAGNITUDE_SATURATION_STD, 1.0)

    # --- Seasonal consistency: how much does this calendar week vary
    # across prior years? High consistency (tight pattern) means a deviation
    # is more significant; low consistency (wild swings) means it's noise ---
    cv = (seasonal_std / seasonal_mean) if seasonal_mean != 0 else 0.0
    seasonal_consistency = 1.0 - min(abs(cv) / SEASONALITY_CONSISTENCY_SATURATION, 1.0)
    seasonal_consistency = max(0.0, min(seasonal_consistency, 1.0))

    analyzer_score = magnitude * seasonal_consistency

    prior_years = [
    {"year": int(idx[0]), "week": int(idx[1]), "value": round(float(v), 2)}
    for idx, v in seasonal_history.items()
    ]


    return {
        "sufficient_data": True,
        "store": store,
        "category": category,
        "year": year,
        "week": week,
        "metric": metric,
        "this_week_value": round(float(this_week_total), 2),
        "seasonal_baseline_mean": round(float(seasonal_mean), 2),
        "seasonal_baseline_std": round(float(seasonal_std), 2),
        "magnitude": round(float(magnitude), 4),
        "seasonal_consistency": round(float(seasonal_consistency), 4),
        "specificity": round(float(seasonal_consistency), 4),  # kept for naming consistency
        "analyzer_score": round(float(analyzer_score), 4),
        "prior_year_weeks": prior_years,
    }


def print_seasonality_analysis(result: dict):
    print("\nSeasonality Analyzer")
    if not result["sufficient_data"]:
        print(f"  Insufficient data: {result['reason']}")
        print()
        return

    print(f"  {result['store']} / {result['category']} — {result['year']}-W{result['week']:02d}")
    print(f"  This week: {result['this_week_value']:.2f}  (seasonal baseline: {result['seasonal_baseline_mean']:.2f} ± {result['seasonal_baseline_std']:.2f})")
    print(f"  Magnitude: {result['magnitude']}  Seasonal Consistency: {result['seasonal_consistency']} "
          f"(pattern tightness: {(1.0 - result['seasonal_consistency']) * 100:.0f}% variance expected)")
    print(f"  Analyzer score: {result['analyzer_score']}")
    print("  Prior year Week {week} values:".format(week=result['week']))
    for y in result["prior_year_weeks"]:
        print(f"    {y['year']}-W{result['week']:02d}: {y['value']}")
    print()