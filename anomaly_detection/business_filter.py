# anomaly_detection/business_filter.py

import pandas as pd
from utils.constants import MIN_WEEKS_FOR_GROUP, MIN_VOLUME_PERCENTILE

GROUP_COLS = ["Store", "Category"]


def compute_group_stats(weekly_kpis: pd.DataFrame, group_cols: list = None) -> pd.DataFrame:
    """
    One row per group with weeks_present and avg_weekly_revenue —
    the two numbers the business filter decides on.
    """
    if group_cols is None:
        group_cols = GROUP_COLS

    stats = (
        weekly_kpis.groupby(group_cols)
        .agg(weeks_present=("Revenue", "count"), avg_weekly_revenue=("Revenue", "mean"))
        .reset_index()
    )
    return stats


def apply_business_filter(weekly_kpis: pd.DataFrame, group_cols: list = None) -> tuple:
    """
    Screens out Store x Category groups that are too small or too new to be
    checked for anomalies at all — avoids false alarms from noisy, low-volume
    groups before they ever reach Isolation Forest.

    A group must clear BOTH:
      - weeks_present >= MIN_WEEKS_FOR_GROUP (enough history to have a "normal")
      - avg_weekly_revenue >= the MIN_VOLUME_PERCENTILE-th percentile of
        avg_weekly_revenue across ALL groups (not a fixed dollar amount, so
        this adapts to whatever dataset is uploaded instead of hardcoding a
        threshold that only makes sense for this Superstore data)

    Returns (filtered_weekly_kpis, filter_report).
    filter_report mirrors the sufficiency/cleaning report style used
    elsewhere, so it can be surfaced in the same upload-time summary.
    """
    if group_cols is None:
        group_cols = GROUP_COLS

    stats = compute_group_stats(weekly_kpis, group_cols)

    volume_threshold = stats["avg_weekly_revenue"].quantile(MIN_VOLUME_PERCENTILE / 100)

    stats["passes_history"] = stats["weeks_present"] >= MIN_WEEKS_FOR_GROUP
    stats["passes_volume"] = stats["avg_weekly_revenue"] >= volume_threshold
    stats["passes_filter"] = stats["passes_history"] & stats["passes_volume"]

    passing_groups = stats.loc[stats["passes_filter"], group_cols]
    filtered = weekly_kpis.merge(passing_groups, on=group_cols, how="inner")

    report = {
        "status": "OK",
        "total_groups": len(stats),
        "groups_passed": int(stats["passes_filter"].sum()),
        "groups_excluded_low_history": int((~stats["passes_history"]).sum()),
        "groups_excluded_low_volume": int((stats["passes_history"] & ~stats["passes_volume"]).sum()),
        "volume_threshold_used": round(float(volume_threshold), 2),
    }

    return filtered, report


def print_filter_report(report: dict):
    """Console banner, companion to the preprocessing/KPI reports."""
    print("\nBusiness Filter Summary")
    print(f"  Total Store x Category groups: {report['total_groups']}")
    print(f"  Groups passed (eligible for anomaly detection): {report['groups_passed']}")
    print(f"  Excluded — insufficient history: {report['groups_excluded_low_history']}")
    print(f"  Excluded — low volume (below ${report['volume_threshold_used']}/week avg): {report['groups_excluded_low_volume']}")
    print()