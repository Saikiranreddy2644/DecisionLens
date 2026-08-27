# investigation_engine/region_analyzer.py

import pandas as pd
import numpy as np
from utils.constants import (
    MIN_REGION_TRANSACTIONS,
    MIN_DISTINCT_REGIONS,
    MIN_WEEKS_FOR_GROUP,
    REGION_UNIQUENESS_SATURATION,
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


def analyze_region(
    processed_df: pd.DataFrame,
    store: str,
    category: str,
    year: int,
    week: int,
    metric: str = "Revenue",
) -> dict:
    """
    Investigates a single flagged Store+Category+Week anomaly at the Region
    level — one grain up from Store Analyzer. Where Store Analyzer asks "is
    this store's problem, or every store's?", Region Analyzer asks "is this
    store's whole REGION struggling for this category, or is the region
    fine and it's really just this one store?"

    Region is soft-required (per validator.py) — a dataset might not have
    it at all. This analyzer must degrade gracefully in that case, same as
    every other soft-required-dependent piece of the pipeline.

    Runs only on transaction rows for this Category, across all regions
    (never the whole dataset), same sparsity discipline as the other
    analyzers.

    Two things get combined into "specificity", same pattern as Store/
    Category Analyzers:
      - concentration: this week, is this Category's revenue spread evenly
        across all regions, or dominated by a few? (normalized HHI)
      - uniqueness: did THIS store's region's share of the category's total
        revenue this week deviate from its own historical average share?

    magnitude: how unusual this Region+Category's total for `metric` was
    this week, relative to its own history — same z-score logic used
    throughout the Investigation Engine.

    analyzer_score = magnitude * specificity

    Returns a dict. If Region isn't in the dataset at all, or there isn't
    enough data to trust a region-level comparison, returns
    {"sufficient_data": False, "reason": ..., "analyzer_score": None} —
    None, not 0, so it's excluded (not counted) from the confidence
    formula's weighted average rather than treated as confidently finding
    nothing.
    """
    if "Region" not in processed_df.columns:
        return {
            "sufficient_data": False,
            "reason": "Dataset has no Region column — Region Analyzer skipped",
            "analyzer_score": None,
        }

    df = _add_year_week(processed_df)
    category_df = df[df["Category"] == category]

    this_week = category_df[(category_df["Year"] == year) & (category_df["Week"] == week)]
    history = category_df[~((category_df["Year"] == year) & (category_df["Week"] == week))]

    # --- Sufficiency guards ---
    if len(this_week) < MIN_REGION_TRANSACTIONS:
        return {
            "sufficient_data": False,
            "reason": f"Only {len(this_week)} transaction(s) this week (need {MIN_REGION_TRANSACTIONS}+)",
            "analyzer_score": None,
        }

    n_regions_this_week = this_week["Region"].nunique()
    if n_regions_this_week < MIN_DISTINCT_REGIONS:
        return {
            "sufficient_data": False,
            "reason": f"Only {n_regions_this_week} distinct region(s) sold this category this week (need {MIN_DISTINCT_REGIONS}+)",
            "analyzer_score": None,
        }

    n_historical_weeks = history[["Year", "Week"]].drop_duplicates().shape[0]
    if n_historical_weeks < MIN_WEEKS_FOR_GROUP:
        return {
            "sufficient_data": False,
            "reason": f"Only {n_historical_weeks} historical week(s) for this category (need {MIN_WEEKS_FOR_GROUP}+)",
            "analyzer_score": None,
        }

    # --- Resolve which region this store belongs to ---
    store_region_rows = df[df["Store"] == store]["Region"]
    if store_region_rows.empty:
        return {
            "sufficient_data": False,
            "reason": f"Store '{store}' has no Region value in this dataset",
            "analyzer_score": None,
        }
    region = store_region_rows.mode().iloc[0]  # most common region for this store, in case of any inconsistency

    if region not in this_week["Region"].unique():
        return {
            "sufficient_data": False,
            "reason": f"Region '{region}' had no transactions for this category this week",
            "analyzer_score": None,
        }

    # --- Concentration (this week's region mix, for this category) ---
    this_week_regions = this_week.groupby("Region")[metric].sum()
    total_this_week = this_week_regions.sum()
    shares_this_week = this_week_regions / total_this_week

    n = len(shares_this_week)
    hhi = (shares_this_week ** 2).sum()
    concentration = (hhi - 1 / n) / (1 - 1 / n) if n > 1 else 1.0

    # --- Uniqueness (vs this region's own historical share of the category) ---
    hist_weekly = history.groupby(["Year", "Week", "Region"])[metric].sum().reset_index()
    hist_week_totals = hist_weekly.groupby(["Year", "Week"])[metric].transform("sum")
    hist_weekly["share"] = hist_weekly[metric] / hist_week_totals
    historical_avg_share = hist_weekly.groupby("Region")["share"].mean()

    this_region_share = shares_this_week.get(region, 0.0)
    this_region_hist_share = historical_avg_share.get(region, 0.0)
    uniqueness = min(
        abs(this_region_share - this_region_hist_share) / REGION_UNIQUENESS_SATURATION,
        1.0,
    )

    specificity = (concentration + uniqueness) / 2

    # --- Magnitude (this Region+Category's total vs its own history) ---
    this_region_total = this_week_regions.get(region, 0.0)
    hist_region_weekly = (
        history[history["Region"] == region]
        .groupby(["Year", "Week"])[metric]
        .sum()
    )
    hist_mean = hist_region_weekly.mean()
    hist_std = hist_region_weekly.std()

    if hist_std and hist_std > 0:
        z = (this_region_total - hist_mean) / hist_std
    else:
        z = 0.0 if this_region_total == hist_mean else np.inf
    magnitude = min(abs(z) / MAGNITUDE_SATURATION_STD, 1.0)

    analyzer_score = magnitude * specificity

    other_regions = (
        this_week_regions.drop(labels=[region], errors="ignore")
        .sort_values(ascending=False)
        .head(3)
        .rename("this_week_value")
        .reset_index()
    )
    other_regions["historical_avg_share"] = other_regions["Region"].map(historical_avg_share).fillna(0.0)
    other_regions["this_week_share"] = other_regions["Region"].map(shares_this_week)

    return {
        "sufficient_data": True,
        "store": store,
        "category": category,
        "region": region,
        "year": year,
        "week": week,
        "metric": metric,
        "magnitude": round(float(magnitude), 4),
        "concentration": round(float(concentration), 4),
        "uniqueness": round(float(uniqueness), 4),
        "specificity": round(float(specificity), 4),
        "analyzer_score": round(float(analyzer_score), 4),
        "this_region_share": round(float(this_region_share), 4),
        "this_region_historical_avg_share": round(float(this_region_hist_share), 4),
        "other_regions_this_week": other_regions.to_dict("records"),
    }


def print_region_analysis(result: dict):
    print("\nRegion Analyzer")
    if not result["sufficient_data"]:
        print(f"  Insufficient data: {result['reason']}")
        print()
        return

    print(f"  {result['store']} ({result['region']}) / {result['category']} — {result['year']}-W{result['week']:02d}")
    print(f"  Magnitude: {result['magnitude']}  Specificity: {result['specificity']} "
          f"(concentration={result['concentration']}, uniqueness={result['uniqueness']})")
    print(f"  Analyzer score: {result['analyzer_score']}")
    print(f"  This region's share of category revenue: {result['this_region_share']:.1%} "
          f"(historical avg: {result['this_region_historical_avg_share']:.1%})")
    print("  Other regions this week:")
    for r in result["other_regions_this_week"]:
        print(f"    {r['Region']}: {r['this_week_value']:.2f} "
              f"(share {r['this_week_share']:.1%}, historical avg share {r['historical_avg_share']:.1%})")
    print()