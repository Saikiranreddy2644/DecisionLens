# preprocessing/feature_engineering.py

import numpy as np
import pandas as pd


def add_profit(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensures a Profit column exists. If the dataset already has one natively
    (e.g. Superstore), it's left untouched. Otherwise derives it from
    Revenue - Cost (only possible if Cost survived column_mapper's fallback
    or was present natively).
    """
    df = df.copy()
    if "Profit" not in df.columns:
        if "Revenue" in df.columns and "Cost" in df.columns:
            df["Profit"] = df["Revenue"] - df["Cost"]
    return df


def add_profit_margin(df: pd.DataFrame) -> pd.DataFrame:
    """
    Profit Margin = Profit / Revenue. Rows with zero or missing Revenue get
    NaN rather than inf/crash.
    """
    df = df.copy()
    if "Profit" in df.columns and "Revenue" in df.columns:
        df["Profit Margin"] = np.where(
            df["Revenue"] != 0,
            df["Profit"] / df["Revenue"],
            np.nan,
        )
    return df


def add_time_features(df: pd.DataFrame, date_col: str = "Date") -> pd.DataFrame:
    """
    Adds Month and Week columns derived from Date.
    Week uses ISO calendar week (same convention validator.py already uses
    for Historical/Seasonality sufficiency checks), so downstream analyzers
    stay consistent about what "a week" means.
    """
    df = df.copy()
    if date_col in df.columns:
        dates = pd.to_datetime(df[date_col], errors="coerce")
        df["Month"] = dates.dt.month
        df["Week"] = dates.dt.isocalendar().week
    return df


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Runs the full feature engineering sequence: Profit -> Profit Margin ->
    Month/Week. Order matters — Profit Margin needs Profit to exist first.
    """
    df = add_profit(df)
    df = add_profit_margin(df)
    df = add_time_features(df)
    return df