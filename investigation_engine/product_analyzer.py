# investigation_engine/product_analyzer.py

import pandas as pd
import numpy as np
from utils.constants import (
    MIN_PRODUCT_TRANSACTIONS,
    MIN_DISTINCT_PRODUCTS,
    MIN_WEEKS_FOR_GROUP,
    PRODUCT_UNIQUENESS_SATURATION,
    MAGNITUDE_SATURATION_STD,
)


def _add_year_week(df: pd.DataFrame, date_col: str = "Date") -> pd.DataFrame:
    """Same convention as kpi_engine.py — kept local so this module is self-contained."""
    df = df.copy()
    dates = pd.to_datetime(df[date_col], errors="coerce")
    iso = dates.dt.isocalendar()
    df["Year"] = iso["year"]
    df["Week"] = iso["week"]
    return df


def analyze_product(
    processed_df: pd.DataFrame,
    store: str,
    category: str,
    year: int,
    week: int,
    metric: str = "Revenue",
) -> dict:
    """
    Investigates a single flagged Store+Category+Week anomaly at the Product
    level — the "Store + Product, investigation-only" layer. Runs ONLY on
    the transaction rows for this one already-flagged group/week (never
    scans the whole dataset at product grain, which would hit the same
    sparsity problem City-as-Store did).

    Two things get combined into "specificity":
      - concentration: is the metric driven by a few products, or spread
        evenly across the whole product mix that week? (normalized HHI)
      - uniqueness: did specific products behave very differently from
        THEIR OWN historical norm, vs. just being big as usual? (compares
        each product's revenue share this week against its own historical
        average share for this Store+Category)

    magnitude: how unusual the group's total for `metric` was that week,
    relative to this Store+Category's own history (same z-score logic used
    in isolation_forest_detector.py, recomputed locally here so this
    analyzer can run standalone).

    analyzer_score = magnitude * specificity

    Returns a dict. If the data isn't sufficient to trust a product-level
    breakdown (too few transactions or too few distinct products that week),
    returns {"sufficient_data": False, "reason": ..., "analyzer_score": None}
    — None, not 0, because an analyzer with no data is "not counted" in the
    confidence formula's weighted average, not "confidently found nothing."
    """
    df = _add_year_week(processed_df)
    group_df = df[(df["Store"] == store) & (df["Category"] == category)]

    this_week = group_df[(group_df["Year"] == year) & (group_df["Week"] == week)]
    history = group_df[~((group_df["Year"] == year) & (group_df["Week"] == week))]

    # --- Sufficiency guards ---
    if len(this_week) < MIN_PRODUCT_TRANSACTIONS:
        return {
            "sufficient_data": False,
            "reason": f"Only {len(this_week)} transaction(s) this week (need {MIN_PRODUCT_TRANSACTIONS}+)",
            "analyzer_score": None,
        }

    n_products_this_week = this_week["Product"].nunique()
    if n_products_this_week < MIN_DISTINCT_PRODUCTS:
        return {
            "sufficient_data": False,
            "reason": f"Only {n_products_this_week} distinct product(s) this week (need {MIN_DISTINCT_PRODUCTS}+)",
            "analyzer_score": None,
        }

    n_historical_weeks = history[["Year", "Week"]].drop_duplicates().shape[0]
    if n_historical_weeks < MIN_WEEKS_FOR_GROUP:
        return {
            "sufficient_data": False,
            "reason": f"Only {n_historical_weeks} historical week(s) for this group (need {MIN_WEEKS_FOR_GROUP}+)",
            "analyzer_score": None,
        }

    # --- Concentration (this week's product mix) ---
    this_week_products = this_week.groupby("Product")[metric].sum()
    total_this_week = this_week_products.sum()
    shares_this_week = this_week_products / total_this_week

    n = len(shares_this_week)
    hhi = (shares_this_week ** 2).sum()
    concentration = (hhi - 1 / n) / (1 - 1 / n) if n > 1 else 1.0

    # --- Uniqueness (vs each product's own historical share) ---
    hist_weekly = history.groupby(["Year", "Week", "Product"])[metric].sum().reset_index()
    hist_week_totals = hist_weekly.groupby(["Year", "Week"])[metric].transform("sum")
    hist_weekly["share"] = hist_weekly[metric] / hist_week_totals
    historical_avg_share = hist_weekly.groupby("Product")["share"].mean()

    deviations = {
        product: abs(share - historical_avg_share.get(product, 0.0))
        for product, share in shares_this_week.items()
    }
    max_deviation = max(deviations.values()) if deviations else 0.0
    uniqueness = min(max_deviation / PRODUCT_UNIQUENESS_SATURATION, 1.0)

    specificity = (concentration + uniqueness) / 2

    # --- Magnitude (this week's group total vs its own history) ---
    hist_group_weekly = history.groupby(["Year", "Week"])[metric].sum()
    hist_mean = hist_group_weekly.mean()
    hist_std = hist_group_weekly.std()

    if hist_std and hist_std > 0:
        z = (total_this_week - hist_mean) / hist_std
    else:
        z = 0.0 if total_this_week == hist_mean else np.inf
    magnitude = min(abs(z) / MAGNITUDE_SATURATION_STD, 1.0)

    analyzer_score = magnitude * specificity

    top_products = (
        this_week_products.sort_values(ascending=False)
        .head(3)
        .rename("this_week_value")
        .reset_index()
    )
    top_products["historical_avg_share"] = top_products["Product"].map(historical_avg_share).fillna(0.0)
    top_products["this_week_share"] = top_products["Product"].map(shares_this_week)

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
        "top_products": top_products.to_dict("records"),
    }


def print_product_analysis(result: dict):
    print("\nProduct Analyzer")
    if not result["sufficient_data"]:
        print(f"  Insufficient data: {result['reason']}")
        print()
        return

    print(f"  {result['store']} / {result['category']} — {result['year']}-W{result['week']:02d}")
    print(f"  Magnitude: {result['magnitude']}  Specificity: {result['specificity']} "
          f"(concentration={result['concentration']}, uniqueness={result['uniqueness']})")
    print(f"  Analyzer score: {result['analyzer_score']}")
    print("  Top products this week:")
    for p in result["top_products"]:
        print(f"    {p['Product']}: {p['this_week_value']:.2f} "
              f"(share {p['this_week_share']:.1%}, historical avg share {p['historical_avg_share']:.1%})")
    print()