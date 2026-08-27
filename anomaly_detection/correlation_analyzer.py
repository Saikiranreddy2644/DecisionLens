# anomaly_detection/correlation_analyzer.py

import pandas as pd
from utils.constants import MIN_CORRELATED_GROUPS


def tag_correlations(anomaly_df: pd.DataFrame) -> pd.DataFrame:
    """
    Checks each flagged anomaly against two patterns, in the same week:
      - category-wide: did MIN_CORRELATED_GROUPS+ different Stores also flag
        an anomaly in this same Category this week? (points at something
        affecting the category broadly — a pricing change, a supplier issue)
      - store-wide: did MIN_CORRELATED_GROUPS+ different Categories also flag
        an anomaly in this same Store this week? (points at something
        affecting the store broadly — a system outage, a local event)

    An anomaly can be both, one, or neither (isolated). Isolated anomalies
    aren't discarded — they're still real anomalies — this just tells the
    Business Event step whether to bundle them with related anomalies or
    treat them standalone.
    """
    df = anomaly_df.copy()

    df["category_anomaly_count"] = df.groupby(["Year", "Week", "Category"])["is_anomaly"].transform("sum")
    df["store_anomaly_count"] = df.groupby(["Year", "Week", "Store"])["is_anomaly"].transform("sum")

    df["is_category_correlated"] = df["is_anomaly"] & (df["category_anomaly_count"] >= MIN_CORRELATED_GROUPS)
    df["is_store_correlated"] = df["is_anomaly"] & (df["store_anomaly_count"] >= MIN_CORRELATED_GROUPS)

    return df


def print_correlation_summary(tagged_df: pd.DataFrame):
    anomalies = tagged_df[tagged_df["is_anomaly"]]
    both = (anomalies["is_category_correlated"] & anomalies["is_store_correlated"]).sum()
    cat_only = (anomalies["is_category_correlated"] & ~anomalies["is_store_correlated"]).sum()
    store_only = (~anomalies["is_category_correlated"] & anomalies["is_store_correlated"]).sum()
    isolated = (~anomalies["is_category_correlated"] & ~anomalies["is_store_correlated"]).sum()

    print("\nCorrelation Summary")
    print(f"  Total anomalies: {len(anomalies)}")
    print(f"  Category-wide only: {cat_only}")
    print(f"  Store-wide only: {store_only}")
    print(f"  Both patterns: {both}")
    print(f"  Isolated (neither): {isolated}")
    print()