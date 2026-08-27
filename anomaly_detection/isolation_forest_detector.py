# anomaly_detection/isolation_forest_detector.py

import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from utils.constants import ANOMALY_CONTAMINATION, ISOLATION_FOREST_RANDOM_STATE

GROUP_COLS = ["Store", "Category"]
FEATURES = ["Revenue", "Profit Margin", "Quantity"]


def compute_group_zscores(df: pd.DataFrame, group_cols: list = None, features: list = None) -> pd.DataFrame:
    """
    Z-scores each feature WITHIN its own Store x Category group (not
    globally) — a $10/week group and a $2,500/week group need to be judged
    against their own normal, not each other's raw dollar scale, or the
    small group would look permanently "flat" and the large group would
    dominate every anomaly.

    Groups with zero variance in a feature (every week identical) get z=0
    for that feature — there's no "unusual" relative to a constant.
    """
    if group_cols is None:
        group_cols = GROUP_COLS
    if features is None:
        features = FEATURES

    df = df.copy()
    for feat in features:
        if feat not in df.columns:
            continue
        group_mean = df.groupby(group_cols)[feat].transform("mean")
        group_std = df.groupby(group_cols)[feat].transform("std").replace(0, np.nan)
        z = (df[feat] - group_mean) / group_std
        df[f"{feat}_z"] = z.fillna(0)

    return df


def run_isolation_forest(
    zscored_df: pd.DataFrame,
    features: list = None,
    contamination: float = ANOMALY_CONTAMINATION,
) -> pd.DataFrame:
    """
    Fits ONE Isolation Forest across all groups' z-scored weeks pooled
    together (not one model per group — most groups only have a handful of
    weeks even after the business filter, too few to train a per-group
    model on). Because features are z-scored within-group first, pooling is
    fair: a z of +3 means "3 std devs above this group's own normal"
    regardless of which group it came from.

    Adds:
      - anomaly_score: higher = more anomalous (sign-flipped decision_function,
        so higher-is-worse matches intuition elsewhere in this project)
      - is_anomaly: bool, True for the `contamination` fraction flagged most
        anomalous by the model

    Returns the input df with these two columns added.
    """
    if features is None:
        features = FEATURES

    z_cols = [f"{f}_z" for f in features if f"{f}_z" in zscored_df.columns]
    if not z_cols:
        raise ValueError("No z-scored feature columns found — run compute_group_zscores first.")

    df = zscored_df.copy()
    X = df[z_cols].values

    model = IsolationForest(
        contamination=contamination,
        random_state=ISOLATION_FOREST_RANDOM_STATE,
    )
    model.fit(X)

    df["anomaly_score"] = -model.decision_function(X)  # higher = more anomalous
    df["is_anomaly"] = model.predict(X) == -1

    return df


def detect_anomalies(filtered_kpis: pd.DataFrame, group_cols: list = None, features: list = None,
                      contamination: float = ANOMALY_CONTAMINATION) -> tuple:
    """
    Orchestrates the Isolation Forest step: z-score within group -> fit
    pooled model -> flag anomalies. Input should already be business-filtered
    (anomaly_detection.business_filter.apply_business_filter output).

    Returns (df_with_anomaly_flags, report).
    """
    zscored = compute_group_zscores(filtered_kpis, group_cols, features)
    result = run_isolation_forest(zscored, features, contamination)

    report = {
        "status": "OK",
        "total_group_weeks_checked": len(result),
        "anomalies_flagged": int(result["is_anomaly"].sum()),
        "contamination_used": contamination,
    }

    return result, report


def print_anomaly_report(report: dict):
    print("\nIsolation Forest Summary")
    print(f"  Group-weeks checked: {report['total_group_weeks_checked']}")
    print(f"  Anomalies flagged: {report['anomalies_flagged']} (contamination={report['contamination_used']})")
    print()