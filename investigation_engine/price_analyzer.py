# investigation_engine/price_analyzer.py

import pandas as pd
import numpy as np
from utils.constants import (
    MIN_PRICE_TRANSACTIONS,
    MIN_WEEKS_FOR_GROUP,
    PRICE_ELASTICITY_SATURATION_STD,
    PRICE_DISCOUNT_SATURATION,
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


def analyze_price(
    processed_df: pd.DataFrame,
    store: str,
    category: str,
    year: int,
    week: int,
) -> dict:
    """
    Investigates a single flagged Store+Category+Week anomaly for a pricing
    cause. Unlike Product/Category/Store/Region Analyzers — which compare
    this group against its peers — Price Analyzer looks INWARD at this one
    Store+Category and asks: did unit price move, and did quantity respond
    the way real price sensitivity would predict?

    magnitude: how unusual this week's unit price (Revenue / Quantity) was,
    relative to this Store+Category's own historical unit price — same
    z-score/saturation convention as every other analyzer.

    specificity: NOT a share/concentration measure like the other analyzers
    (there's no "peer group" for price). Instead it's built from up to two
    signals, averaged over whichever are available:
      - elasticity_signal: did quantity move in the OPPOSITE direction of
        price this week (the textbook signature of a price-driven change)?
        Scored by how large that quantity response was, but only counted
        if the directions actually oppose — same-direction or flat-quantity
        movement contributes nothing, since that looks like a demand shift
        having nothing to do with price.
      - discount_signal: if a Discount column happens to exist in this
        dataset, did the average discount this week deviate meaningfully
        from its historical average? This is direct evidence rather than
        an inference, so it's included whenever available, but never
        required — datasets without a Discount column still get a valid
        (if slightly less certain) Price Analyzer result via elasticity
        alone.

    analyzer_score = magnitude * specificity

    Returns a dict. If there isn't enough data to trust a price comparison
    (too few transactions, too little history, or Quantity is zero so a
    unit price can't even be computed), returns
    {"sufficient_data": False, "reason": ..., "analyzer_score": None} —
    None, not 0, so it's excluded (not counted) from the confidence
    formula's weighted average rather than treated as confidently finding
    nothing.
    """
    df = _add_year_week(processed_df)
    group_df = df[(df["Store"] == store) & (df["Category"] == category)]

    this_week = group_df[(group_df["Year"] == year) & (group_df["Week"] == week)]
    history = group_df[~((group_df["Year"] == year) & (group_df["Week"] == week))]

    # --- Sufficiency guards ---
    if len(this_week) < MIN_PRICE_TRANSACTIONS:
        return {
            "sufficient_data": False,
            "reason": f"Only {len(this_week)} transaction(s) this week (need {MIN_PRICE_TRANSACTIONS}+)",
            "analyzer_score": None,
        }

    n_historical_weeks = history[["Year", "Week"]].drop_duplicates().shape[0]
    if n_historical_weeks < MIN_WEEKS_FOR_GROUP:
        return {
            "sufficient_data": False,
            "reason": f"Only {n_historical_weeks} historical week(s) for this group (need {MIN_WEEKS_FOR_GROUP}+)",
            "analyzer_score": None,
        }

    this_week_qty = this_week["Quantity"].sum()
    if this_week_qty == 0:
        return {
            "sufficient_data": False,
            "reason": "Quantity is zero this week — cannot compute a unit price",
            "analyzer_score": None,
        }

    # --- Weekly unit price series (Revenue / Quantity, weighted — not a
    # mean of row-level prices, which would overweight low-volume rows) ---
    weekly = group_df.groupby(["Year", "Week"]).agg(
        Revenue=("Revenue", "sum"), Quantity=("Quantity", "sum")
    )
    weekly = weekly[weekly["Quantity"] > 0]
    weekly["unit_price"] = weekly["Revenue"] / weekly["Quantity"]

    this_week_key = (year, week)
    if this_week_key not in weekly.index:
        return {
            "sufficient_data": False,
            "reason": "Could not compute a valid unit price for this week",
            "analyzer_score": None,
        }

    this_week_price = weekly.loc[this_week_key, "unit_price"]
    hist_prices = weekly.drop(index=this_week_key, errors="ignore")["unit_price"]

    if len(hist_prices) < MIN_WEEKS_FOR_GROUP:
        return {
            "sufficient_data": False,
            "reason": f"Only {len(hist_prices)} historical week(s) with a valid unit price (need {MIN_WEEKS_FOR_GROUP}+)",
            "analyzer_score": None,
        }

    hist_price_mean = hist_prices.mean()
    hist_price_std = hist_prices.std()

    if hist_price_std and hist_price_std > 0:
        price_z = (this_week_price - hist_price_mean) / hist_price_std
    else:
        price_z = 0.0 if this_week_price == hist_price_mean else np.inf
    magnitude = min(abs(price_z) / MAGNITUDE_SATURATION_STD, 1.0)

    # --- Elasticity signal: did Quantity move opposite to Price? ---
    hist_qty = history.groupby(["Year", "Week"])["Quantity"].sum()
    hist_qty_mean = hist_qty.mean()
    hist_qty_std = hist_qty.std()

    if hist_qty_std and hist_qty_std > 0:
        qty_z = (this_week_qty - hist_qty_mean) / hist_qty_std
    else:
        qty_z = 0.0 if this_week_qty == hist_qty_mean else np.inf

    opposite_direction = (
        (price_z > 0 and qty_z < 0) or (price_z < 0 and qty_z > 0)
    )
    elasticity_signal = (
        min(abs(qty_z) / PRICE_ELASTICITY_SATURATION_STD, 1.0) if opposite_direction else 0.0
    )

    # --- Discount signal: direct evidence, only if the column exists ---
    discount_signal = None
    this_week_discount = None
    hist_discount_mean = None
    if "Discount" in group_df.columns:
        this_week_discount = this_week["Discount"].mean()
        hist_discount_mean = history["Discount"].mean()
        if pd.notna(this_week_discount) and pd.notna(hist_discount_mean):
            discount_deviation = abs(this_week_discount - hist_discount_mean)
            discount_signal = min(discount_deviation / PRICE_DISCOUNT_SATURATION, 1.0)

    signals = [elasticity_signal]
    if discount_signal is not None:
        signals.append(discount_signal)
    specificity = sum(signals) / len(signals)

    analyzer_score = magnitude * specificity

    result = {
        "sufficient_data": True,
        "store": store,
        "category": category,
        "year": year,
        "week": week,
        "this_week_unit_price": round(float(this_week_price), 4),
        "historical_avg_unit_price": round(float(hist_price_mean), 4),
        "magnitude": round(float(magnitude), 4),
        "elasticity_signal": round(float(elasticity_signal), 4),
        "opposite_direction_movement": bool(opposite_direction),
        "specificity": round(float(specificity), 4),
        "analyzer_score": round(float(analyzer_score), 4),
    }
    if discount_signal is not None:
        result["discount_signal"] = round(float(discount_signal), 4)
        result["this_week_avg_discount"] = round(float(this_week_discount), 4)
        result["historical_avg_discount"] = round(float(hist_discount_mean), 4)

    return result


def print_price_analysis(result: dict):
    print("\nPrice Analyzer")
    if not result["sufficient_data"]:
        print(f"  Insufficient data: {result['reason']}")
        print()
        return

    print(f"  {result['store']} / {result['category']} — {result['year']}-W{result['week']:02d}")
    print(f"  Unit price this week: {result['this_week_unit_price']:.2f} "
          f"(historical avg: {result['historical_avg_unit_price']:.2f})")
    print(f"  Magnitude: {result['magnitude']}  Specificity: {result['specificity']}")
    print(f"  Elasticity signal: {result['elasticity_signal']} "
          f"(price/quantity moved opposite directions: {result['opposite_direction_movement']})")
    if "discount_signal" in result:
        print(f"  Discount signal: {result['discount_signal']} "
              f"(this week avg: {result['this_week_avg_discount']:.1%}, "
              f"historical avg: {result['historical_avg_discount']:.1%})")
    print(f"  Analyzer score: {result['analyzer_score']}")
    print()