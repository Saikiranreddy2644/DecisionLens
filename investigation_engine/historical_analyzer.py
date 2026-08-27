# investigation_engine/historical_analyzer.py

import pandas as pd
import numpy as np
from utils.constants import (
    MIN_HISTORICAL_TRANSACTIONS,
    MIN_WEEKS_FOR_GROUP,
    HISTORICAL_PRECEDENT_Z_THRESHOLD,
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


def analyze_historical(
    processed_df: pd.DataFrame,
    store: str,
    category: str,
    year: int,
    week: int,
    metric: str = "Revenue",
) -> dict:
    """
    Investigates a single flagged Store+Category+Week anomaly for precedent:
    has a deviation like this happened before for this group, or is it
    genuinely unprecedented? This is a different question from magnitude
    alone — a -30% week that recurs every quarter is a known pattern, not
    really "anomalous" in the way a -30% week that's never happened before
    is. Precedent, not size, is what makes something historically notable.

    magnitude: same z-score/saturation convention as the other analyzers —
    how unusual this week's total was vs this Store+Category's history.

    specificity: here this is "novelty", not a share/concentration measure.
    It scans every OTHER historical week for this group and counts how many
    had a comparably extreme deviation (|z| >= HISTORICAL_PRECEDENT_Z_THRESHOLD)
    in the SAME direction as this week. The more precedents found, the less
    novel this week is:
        novelty = 1 - (precedent_count / total_historical_weeks)
    A week with zero precedents (this has truly never happened before)
    scores novelty = 1.0. A week where this happens constantly scores near 0.

    analyzer_score = magnitude * novelty

    Returns a dict. If there isn't enough history to meaningfully search for
    precedent, returns {"sufficient_data": False, "reason": ...,
    "analyzer_score": None} — None, not 0, so it's excluded (not counted)
    from the confidence formula's weighted average rather than treated as
    confidently finding nothing.
    """
    df = _add_year_week(processed_df)
    group_df = df[(df["Store"] == store) & (df["Category"] == category)]

    this_week = group_df[(group_df["Year"] == year) & (group_df["Week"] == week)]
    history = group_df[~((group_df["Year"] == year) & (group_df["Week"] == week))]

    # --- Sufficiency guards ---
    if len(this_week) < MIN_HISTORICAL_TRANSACTIONS:
        return {
            "sufficient_data": False,
            "reason": f"Only {len(this_week)} transaction(s) this week (need {MIN_HISTORICAL_TRANSACTIONS}+)",
            "analyzer_score": None,
        }

    hist_weekly = history.groupby(["Year", "Week"])[metric].sum()
    n_historical_weeks = len(hist_weekly)
    if n_historical_weeks < MIN_WEEKS_FOR_GROUP:
        return {
            "sufficient_data": False,
            "reason": f"Only {n_historical_weeks} historical week(s) for this group (need {MIN_WEEKS_FOR_GROUP}+)",
            "analyzer_score": None,
        }

    this_week_total = this_week[metric].sum()
    hist_mean = hist_weekly.mean()
    hist_std = hist_weekly.std()

    # --- Magnitude: this week's own deviation ---
    if hist_std and hist_std > 0:
        this_z = (this_week_total - hist_mean) / hist_std
    else:
        this_z = 0.0 if this_week_total == hist_mean else np.inf
    magnitude = min(abs(this_z) / MAGNITUDE_SATURATION_STD, 1.0)

    # --- Novelty: scan history for weeks with a comparably extreme,
    # same-direction deviation ---
    if hist_std and hist_std > 0:
        hist_z_scores = (hist_weekly - hist_mean) / hist_std
    else:
        hist_z_scores = pd.Series(0.0, index=hist_weekly.index)

    same_direction = hist_z_scores > 0 if this_z >= 0 else hist_z_scores < 0
    precedent_mask = same_direction & (hist_z_scores.abs() >= HISTORICAL_PRECEDENT_Z_THRESHOLD)
    precedent_count = int(precedent_mask.sum())

    novelty = 1.0 - (precedent_count / n_historical_weeks)
    novelty = max(0.0, min(novelty, 1.0))

    analyzer_score = magnitude * novelty

    precedent_weeks = [
        {"year": int(y), "week": int(w), "value": round(float(v), 2)}
        for (y, w), v in hist_weekly[precedent_mask].sort_values(
            ascending=(this_z < 0)
        ).head(3).items()
    ]

    return {
        "sufficient_data": True,
        "store": store,
        "category": category,
        "year": year,
        "week": week,
        "metric": metric,
        "this_week_value": round(float(this_week_total), 2),
        "historical_avg": round(float(hist_mean), 2),
        "magnitude": round(float(magnitude), 4),
        "precedent_count": precedent_count,
        "total_historical_weeks": n_historical_weeks,
        "novelty": round(float(novelty), 4),
        "specificity": round(float(novelty), 4),  # kept for naming consistency with other analyzers
        "analyzer_score": round(float(analyzer_score), 4),
        "similar_past_weeks": precedent_weeks,
    }


def print_historical_analysis(result: dict):
    print("\nHistorical Analyzer")
    if not result["sufficient_data"]:
        print(f"  Insufficient data: {result['reason']}")
        print()
        return

    print(f"  {result['store']} / {result['category']} — {result['year']}-W{result['week']:02d}")
    print(f"  This week: {result['this_week_value']:.2f}  (historical avg: {result['historical_avg']:.2f})")
    print(f"  Magnitude: {result['magnitude']}  Novelty: {result['novelty']} "
          f"({result['precedent_count']}/{result['total_historical_weeks']} historical weeks show a similar deviation)")
    print(f"  Analyzer score: {result['analyzer_score']}")
    if result["similar_past_weeks"]:
        print("  Similar past weeks:")
        for w in result["similar_past_weeks"]:
            print(f"    {w['year']}-W{w['week']:02d}: {w['value']}")
    else:
        print("  No similar past weeks found — this appears unprecedented.")
    print()