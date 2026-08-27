# investigation_engine/category_analyzer.py

import pandas as pd
import numpy as np
from utils.constants import (
    MIN_CATEGORY_TRANSACTIONS,
    MIN_DISTINCT_CATEGORIES,
    MIN_WEEKS_FOR_GROUP,
    CATEGORY_UNIQUENESS_SATURATION,
    MAGNITUDE_SATURATION_STD,
)


def _add_year_week(df: pd.DataFrame, date_col: str = "Date") -> pd.DataFrame:
    """Same convention as kpi_engine.py / product_analyzer.py — kept local
    so this module is self-contained."""
    df = df.copy()
    dates = pd.to_datetime(df[date_col], errors="coerce")
    iso = dates.dt.isocalendar()
    df["Year"] = iso["year"]
    df["Week"] = iso["week"]
    return df


def analyze_category(
    processed_df: pd.DataFrame,
    store: str,
    category: str,
    year: int,
    week: int,
    metric: str = "Revenue",
) -> dict:
    """
    Investigates a single flagged Store+Category+Week anomaly at the Category
    level — one grain up from Product Analyzer. Instead of asking "which
    products drove this?", it asks "is this decline specific to this one
    category, or is the whole store having a bad week?"

    Runs ONLY on this Store's transaction rows (never scans the whole
    dataset), same sparsity discipline as Product Analyzer.

    Two things get combined into "specificity", mirroring Product Analyzer:
      - concentration: this week, is the store's revenue spread evenly
        across all its categories, or dominated by a few? (normalized HHI)
        High concentration on its own doesn't prove THIS category is the
        problem — it's combined with uniqueness below to check that.
      - uniqueness: did THIS category's share of the store's revenue this
        week deviate from its own historical average share? (i.e. is this
        category behaving differently than usual, not just being big)

    magnitude: how unusual this Store+Category's total for `metric` was
    this week, relative to its own history — same z-score logic as
    isolation_forest_detector.py and product_analyzer.py, recomputed
    locally so this analyzer can run standalone.

    analyzer_score = magnitude * specificity

    Returns a dict. If the data isn't sufficient to trust a category-level
    breakdown (too few transactions, too few distinct categories in the
    store that week, or too little history), returns
    {"sufficient_data": False, "reason": ..., "analyzer_score": None} —
    None, not 0, so an analyzer with no data is excluded (not counted) in
    the confidence formula's weighted average, rather than treated as
    confidently finding nothing.
    """
    df = _add_year_week(processed_df)
    store_df = df[df["Store"] == store]

    this_week = store_df[(store_df["Year"] == year) & (store_df["Week"] == week)]
    history = store_df[~((store_df["Year"] == year) & (store_df["Week"] == week))]

    # --- Sufficiency guards ---
    if len(this_week) < MIN_CATEGORY_TRANSACTIONS:
        return {
            "sufficient_data": False,
            "reason": f"Only {len(this_week)} transaction(s) this week (need {MIN_CATEGORY_TRANSACTIONS}+)",
            "analyzer_score": None,
        }

    n_categories_this_week = this_week["Category"].nunique()
    if n_categories_this_week < MIN_DISTINCT_CATEGORIES:
        return {
            "sufficient_data": False,
            "reason": f"Only {n_categories_this_week} distinct categor(y/ies) this week (need {MIN_DISTINCT_CATEGORIES}+)",
            "analyzer_score": None,
        }

    n_historical_weeks = history[["Year", "Week"]].drop_duplicates().shape[0]
    if n_historical_weeks < MIN_WEEKS_FOR_GROUP:
        return {
            "sufficient_data": False,
            "reason": f"Only {n_historical_weeks} historical week(s) for this store (need {MIN_WEEKS_FOR_GROUP}+)",
            "analyzer_score": None,
        }

    if category not in this_week["Category"].unique():
        return {
            "sufficient_data": False,
            "reason": f"Category '{category}' had no transactions for this store this week",
            "analyzer_score": None,
        }

    # --- Concentration (this week's category mix, store-wide) ---
    this_week_categories = this_week.groupby("Category")[metric].sum()
    total_this_week = this_week_categories.sum()
    shares_this_week = this_week_categories / total_this_week

    n = len(shares_this_week)
    hhi = (shares_this_week ** 2).sum()
    concentration = (hhi - 1 / n) / (1 - 1 / n) if n > 1 else 1.0

    # --- Uniqueness (vs this category's own historical share of the store) ---
    hist_weekly = history.groupby(["Year", "Week", "Category"])[metric].sum().reset_index()
    hist_week_totals = hist_weekly.groupby(["Year", "Week"])[metric].transform("sum")
    hist_weekly["share"] = hist_weekly[metric] / hist_week_totals
    historical_avg_share = hist_weekly.groupby("Category")["share"].mean()

    this_category_share = shares_this_week.get(category, 0.0)
    this_category_hist_share = historical_avg_share.get(category, 0.0)
    uniqueness = min(
        abs(this_category_share - this_category_hist_share) / CATEGORY_UNIQUENESS_SATURATION,
        1.0,
    )

    specificity = (concentration + uniqueness) / 2

    # --- Magnitude (this Store+Category's total vs its own history) ---
    this_category_total = this_week_categories.get(category, 0.0)
    hist_category_weekly = (
        history[history["Category"] == category]
        .groupby(["Year", "Week"])[metric]
        .sum()
    )
    hist_mean = hist_category_weekly.mean()
    hist_std = hist_category_weekly.std()

    if hist_std and hist_std > 0:
        z = (this_category_total - hist_mean) / hist_std
    else:
        z = 0.0 if this_category_total == hist_mean else np.inf
    magnitude = min(abs(z) / MAGNITUDE_SATURATION_STD, 1.0)

    analyzer_score = magnitude * specificity

    other_categories = (
        this_week_categories.drop(labels=[category], errors="ignore")
        .sort_values(ascending=False)
        .head(3)
        .rename("this_week_value")
        .reset_index()
    )
    other_categories["historical_avg_share"] = other_categories["Category"].map(historical_avg_share).fillna(0.0)
    other_categories["this_week_share"] = other_categories["Category"].map(shares_this_week)

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
        "this_category_share": round(float(this_category_share), 4),
        "this_category_historical_avg_share": round(float(this_category_hist_share), 4),
        "other_categories_this_week": other_categories.to_dict("records"),
    }


def print_category_analysis(result: dict):
    print("\nCategory Analyzer")
    if not result["sufficient_data"]:
        print(f"  Insufficient data: {result['reason']}")
        print()
        return

    print(f"  {result['store']} / {result['category']} — {result['year']}-W{result['week']:02d}")
    print(f"  Magnitude: {result['magnitude']}  Specificity: {result['specificity']} "
          f"(concentration={result['concentration']}, uniqueness={result['uniqueness']})")
    print(f"  Analyzer score: {result['analyzer_score']}")
    print(f"  This category's share of store revenue: {result['this_category_share']:.1%} "
          f"(historical avg: {result['this_category_historical_avg_share']:.1%})")
    print("  Other categories this week:")
    for c in result["other_categories_this_week"]:
        print(f"    {c['Category']}: {c['this_week_value']:.2f} "
              f"(share {c['this_week_share']:.1%}, historical avg share {c['historical_avg_share']:.1%})")
    print()