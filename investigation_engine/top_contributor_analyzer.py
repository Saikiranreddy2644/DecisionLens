# investigation_engine/top_contributor_analyzer.py

import pandas as pd
import numpy as np
from utils.constants import (
    MIN_CONTRIBUTOR_TRANSACTIONS,
    MIN_DISTINCT_CONTRIBUTOR_PRODUCTS,
    MIN_WEEKS_FOR_GROUP,
    TOP_CONTRIBUTOR_N,
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


def analyze_top_contributor(
    processed_df: pd.DataFrame,
    store: str,
    category: str,
    year: int,
    week: int,
    metric: str = "Revenue",
) -> dict:
    """
    Ranks products by ABSOLUTE business impact — not share deviation like
    Product Analyzer. Product Analyzer answers "is this store+category's
    product MIX behaving oddly?"; this answers the direct business question:
    "which specific products are responsible, in real revenue/unit terms?"

    contribution = (this week's actual value) - (this product's own average
    historical weekly value), for every product seen either this week or
    historically. A product absent this week that used to sell regularly
    gets a large negative contribution — a real signal, not noise.

    magnitude: same z-score/saturation convention as the other analyzers.

    specificity ("impact concentration"): what fraction of total absolute
    deviation across all products is explained by just the top N products?
        specificity = sum(|contribution| for top N) / sum(|contribution| for all)

    analyzer_score = magnitude * specificity
    """
    df = _add_year_week(processed_df)
    group_df = df[(df["Store"] == store) & (df["Category"] == category)]

    this_week = group_df[(group_df["Year"] == year) & (group_df["Week"] == week)]
    history = group_df[~((group_df["Year"] == year) & (group_df["Week"] == week))]

    if len(this_week) < MIN_CONTRIBUTOR_TRANSACTIONS:
        return {
            "sufficient_data": False,
            "reason": f"Only {len(this_week)} transaction(s) this week (need {MIN_CONTRIBUTOR_TRANSACTIONS}+)",
            "analyzer_score": None,
        }

    n_historical_weeks = history[["Year", "Week"]].drop_duplicates().shape[0]
    if n_historical_weeks < MIN_WEEKS_FOR_GROUP:
        return {
            "sufficient_data": False,
            "reason": f"Only {n_historical_weeks} historical week(s) for this group (need {MIN_WEEKS_FOR_GROUP}+)",
            "analyzer_score": None,
        }

    this_week_products = this_week.groupby("Product")[metric].sum()
    hist_total_per_product = history.groupby("Product")[metric].sum()
    historical_avg_per_product = hist_total_per_product / n_historical_weeks

    all_products = set(this_week_products.index) | set(historical_avg_per_product.index)
    if len(all_products) < MIN_DISTINCT_CONTRIBUTOR_PRODUCTS:
        return {
            "sufficient_data": False,
            "reason": f"Only {len(all_products)} distinct product(s) between this week and history (need {MIN_DISTINCT_CONTRIBUTOR_PRODUCTS}+)",
            "analyzer_score": None,
        }

    contributions = {}
    for product in all_products:
        actual = this_week_products.get(product, 0.0)
        expected = historical_avg_per_product.get(product, 0.0)
        contributions[product] = actual - expected

    total_abs_deviation = sum(abs(c) for c in contributions.values())
    if total_abs_deviation == 0:
        return {
            "sufficient_data": False,
            "reason": "No deviation from historical norms detected at the product level",
            "analyzer_score": None,
        }

    ranked = sorted(contributions.items(), key=lambda kv: abs(kv[1]), reverse=True)
    top_contributors = ranked[:TOP_CONTRIBUTOR_N]
    top_n_abs_sum = sum(abs(c) for _, c in top_contributors)
    specificity = min(top_n_abs_sum / total_abs_deviation, 1.0)

    this_week_total = this_week[metric].sum()
    hist_group_weekly = history.groupby(["Year", "Week"])[metric].sum()
    hist_mean = hist_group_weekly.mean()
    hist_std = hist_group_weekly.std()

    if hist_std and hist_std > 0:
        z = (this_week_total - hist_mean) / hist_std
    else:
        z = 0.0 if this_week_total == hist_mean else np.inf
    magnitude = min(abs(z) / MAGNITUDE_SATURATION_STD, 1.0)

    analyzer_score = magnitude * specificity

    top_contributors_out = [
        {
            "product": product,
            "contribution": round(float(contribution), 2),
            "this_week_value": round(float(this_week_products.get(product, 0.0)), 2),
            "historical_avg_weekly_value": round(float(historical_avg_per_product.get(product, 0.0)), 2),
        }
        for product, contribution in top_contributors
    ]

    return {
        "sufficient_data": True,
        "store": store,
        "category": category,
        "year": year,
        "week": week,
        "metric": metric,
        "magnitude": round(float(magnitude), 4),
        "specificity": round(float(specificity), 4),
        "analyzer_score": round(float(analyzer_score), 4),
        "total_abs_deviation": round(float(total_abs_deviation), 2),
        "top_contributors": top_contributors_out,
    }


def print_top_contributor_analysis(result: dict):
    print("\nTop Contributor Analyzer")
    if not result["sufficient_data"]:
        print(f"  Insufficient data: {result['reason']}")
        print()
        return

    print(f"  {result['store']} / {result['category']} — {result['year']}-W{result['week']:02d}")
    print(f"  Magnitude: {result['magnitude']}  Specificity (impact concentration): {result['specificity']}")
    print(f"  Analyzer score: {result['analyzer_score']}")
    print(f"  Top contributors (of {result['total_abs_deviation']:.2f} total absolute deviation):")
    for c in result["top_contributors"]:
        sign = "+" if c["contribution"] >= 0 else ""
        print(f"    {c['product']}: {sign}{c['contribution']:.2f} "
              f"(this week: {c['this_week_value']:.2f}, historical avg: {c['historical_avg_weekly_value']:.2f})")
    print()