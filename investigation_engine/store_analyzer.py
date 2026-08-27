# investigation_engine/store_analyzer.py

import pandas as pd
import numpy as np
from utils.constants import (
    MIN_STORE_TRANSACTIONS,
    MIN_DISTINCT_STORES,
    MIN_WEEKS_FOR_GROUP,
    STORE_UNIQUENESS_SATURATION,
    MAGNITUDE_SATURATION_STD,
)


def _add_year_week(df: pd.DataFrame, date_col: str = "Date") -> pd.DataFrame:
    """Same convention as kpi_engine.py / product_analyzer.py / category_analyzer.py
    — kept local so this module is self-contained."""
    df = df.copy()
    dates = pd.to_datetime(df[date_col], errors="coerce")
    iso = dates.dt.isocalendar()
    df["Year"] = iso["year"]
    df["Week"] = iso["week"]
    return df


def analyze_store(
    processed_df: pd.DataFrame,
    store: str,
    category: str,
    year: int,
    week: int,
    metric: str = "Revenue",
) -> dict:
    """
    Investigates a single flagged Store+Category+Week anomaly at the Store
    level — mirrors Category Analyzer, but one axis over: instead of asking
    "is this category behaving oddly within this store?", it asks "is this
    store behaving oddly compared to other stores selling the same category?"

    This is the analyzer that directly answers "is only Store A affected,
    or did every store see this?" — the single most decisive piece of
    evidence for isolating a store-specific cause (e.g. local stockout,
    local staffing issue) from a category-wide or company-wide one.

    Runs ONLY on transaction rows for this Category, across all stores
    (never the whole dataset), same sparsity discipline as the other
    analyzers.

    Two things get combined into "specificity", same pattern as before:
      - concentration: this week, is this Category's revenue spread evenly
        across all stores, or dominated by a few? (normalized HHI)
      - uniqueness: did THIS store's share of the category's total revenue
        this week deviate from its own historical average share? (i.e. is
        this store behaving differently than usual for this category, not
        just being a naturally bigger/smaller store)

    magnitude: how unusual this Store+Category's total for `metric` was
    this week, relative to its own history — same z-score logic used
    throughout the Investigation Engine, recomputed locally so this
    analyzer can run standalone.

    analyzer_score = magnitude * specificity

    Returns a dict. If the data isn't sufficient to trust a store-level
    comparison (too few transactions, too few distinct stores selling this
    category that week, or too little history), returns
    {"sufficient_data": False, "reason": ..., "analyzer_score": None} —
    None, not 0, so it's excluded (not counted) from the confidence
    formula's weighted average rather than treated as confidently finding
    nothing.
    """
    df = _add_year_week(processed_df)
    category_df = df[df["Category"] == category]

    this_week = category_df[(category_df["Year"] == year) & (category_df["Week"] == week)]
    history = category_df[~((category_df["Year"] == year) & (category_df["Week"] == week))]

    # --- Sufficiency guards ---
    if len(this_week) < MIN_STORE_TRANSACTIONS:
        return {
            "sufficient_data": False,
            "reason": f"Only {len(this_week)} transaction(s) this week (need {MIN_STORE_TRANSACTIONS}+)",
            "analyzer_score": None,
        }

    n_stores_this_week = this_week["Store"].nunique()
    if n_stores_this_week < MIN_DISTINCT_STORES:
        return {
            "sufficient_data": False,
            "reason": f"Only {n_stores_this_week} distinct store(s) sold this category this week (need {MIN_DISTINCT_STORES}+)",
            "analyzer_score": None,
        }

    n_historical_weeks = history[["Year", "Week"]].drop_duplicates().shape[0]
    if n_historical_weeks < MIN_WEEKS_FOR_GROUP:
        return {
            "sufficient_data": False,
            "reason": f"Only {n_historical_weeks} historical week(s) for this category (need {MIN_WEEKS_FOR_GROUP}+)",
            "analyzer_score": None,
        }

    if store not in this_week["Store"].unique():
        return {
            "sufficient_data": False,
            "reason": f"Store '{store}' had no transactions for this category this week",
            "analyzer_score": None,
        }

    # --- Concentration (this week's store mix, for this category) ---
    this_week_stores = this_week.groupby("Store")[metric].sum()
    total_this_week = this_week_stores.sum()
    shares_this_week = this_week_stores / total_this_week

    n = len(shares_this_week)
    hhi = (shares_this_week ** 2).sum()
    concentration = (hhi - 1 / n) / (1 - 1 / n) if n > 1 else 1.0

    # --- Uniqueness (vs this store's own historical share of the category) ---
    hist_weekly = history.groupby(["Year", "Week", "Store"])[metric].sum().reset_index()
    hist_week_totals = hist_weekly.groupby(["Year", "Week"])[metric].transform("sum")
    hist_weekly["share"] = hist_weekly[metric] / hist_week_totals
    historical_avg_share = hist_weekly.groupby("Store")["share"].mean()

    this_store_share = shares_this_week.get(store, 0.0)
    this_store_hist_share = historical_avg_share.get(store, 0.0)
    uniqueness = min(
        abs(this_store_share - this_store_hist_share) / STORE_UNIQUENESS_SATURATION,
        1.0,
    )

    specificity = (concentration + uniqueness) / 2

    # --- Magnitude (this Store+Category's total vs its own history) ---
    this_store_total = this_week_stores.get(store, 0.0)
    hist_store_weekly = (
        history[history["Store"] == store]
        .groupby(["Year", "Week"])[metric]
        .sum()
    )
    hist_mean = hist_store_weekly.mean()
    hist_std = hist_store_weekly.std()

    if hist_std and hist_std > 0:
        z = (this_store_total - hist_mean) / hist_std
    else:
        z = 0.0 if this_store_total == hist_mean else np.inf
    magnitude = min(abs(z) / MAGNITUDE_SATURATION_STD, 1.0)

    analyzer_score = magnitude * specificity

    other_stores = (
        this_week_stores.drop(labels=[store], errors="ignore")
        .sort_values(ascending=False)
        .head(3)
        .rename("this_week_value")
        .reset_index()
    )
    other_stores["historical_avg_share"] = other_stores["Store"].map(historical_avg_share).fillna(0.0)
    other_stores["this_week_share"] = other_stores["Store"].map(shares_this_week)

    return {
        "sufficient_data": True,
        "store": store,
        "category": category,
        "year": year,
        "week": week,
        "metric": metric,
        "magnitude": round(float(magnitude), 4),
        "concentration": round(float(concentration), 4),
        "uniqueness": round(float(uniqueness), 4),
        "specificity": round(float(specificity), 4),
        "analyzer_score": round(float(analyzer_score), 4),
        "this_store_share": round(float(this_store_share), 4),
        "this_store_historical_avg_share": round(float(this_store_hist_share), 4),
        "other_stores_this_week": other_stores.to_dict("records"),
    }


def print_store_analysis(result: dict):
    print("\nStore Analyzer")
    if not result["sufficient_data"]:
        print(f"  Insufficient data: {result['reason']}")
        print()
        return

    print(f"  {result['store']} / {result['category']} — {result['year']}-W{result['week']:02d}")
    print(f"  Magnitude: {result['magnitude']}  Specificity: {result['specificity']} "
          f"(concentration={result['concentration']}, uniqueness={result['uniqueness']})")
    print(f"  Analyzer score: {result['analyzer_score']}")
    print(f"  This store's share of category revenue: {result['this_store_share']:.1%} "
          f"(historical avg: {result['this_store_historical_avg_share']:.1%})")
    print("  Other stores this week:")
    for s in result["other_stores_this_week"]:
        print(f"    {s['Store']}: {s['this_week_value']:.2f} "
              f"(share {s['this_week_share']:.1%}, historical avg share {s['historical_avg_share']:.1%})")
    print()