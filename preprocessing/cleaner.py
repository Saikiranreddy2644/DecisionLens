# preprocessing/cleaner.py

import pandas as pd
from utils.constants import HARD_REQUIRED_COLUMNS

# Fields whose absence makes a row unusable downstream — KPI Engine can't
# aggregate a row with no Revenue/Quantity, and the Investigation Engine
# can't attribute a row with no Date/Store/Category/Product. Soft-required
# fields (Cost, Region) are allowed to be missing at the row level; that's
# exactly what SOFT_REQUIRED_COLUMNS / the Data Sufficiency Report already
# communicates upstream.
CRITICAL_ROW_FIELDS = HARD_REQUIRED_COLUMNS  # Date, Store, Category, Product, Revenue, Quantity

# What counts as "the same transaction" for duplicate detection.
DUPLICATE_SUBSET = ["Date", "Store", "Product", "Revenue", "Quantity"]


def remove_duplicates(df: pd.DataFrame) -> tuple:
    """
    Drops rows that match on DUPLICATE_SUBSET (likely the same transaction).
    Keeps the first occurrence. Returns (deduped_df, num_removed).
    """
    before = len(df)
    df = df.drop_duplicates(subset=DUPLICATE_SUBSET, keep="first")
    removed = before - len(df)
    return df, removed


def handle_missing_values(df: pd.DataFrame) -> tuple:
    """
    Drops rows missing any critical field (hard-required columns — Date,
    Store, Category, Product, Revenue, Quantity). Rows missing only soft
    fields (Cost, Region) are kept as-is; the KPI/Investigation engines
    already know to degrade gracefully for those via the Data Sufficiency
    Report.

    Returns (cleaned_df, num_removed).
    """
    before = len(df)
    present_critical = [col for col in CRITICAL_ROW_FIELDS if col in df.columns]
    df = df.dropna(subset=present_critical)
    removed = before - len(df)
    return df, removed


def standardize_types(df: pd.DataFrame) -> pd.DataFrame:
    """
    Coerces columns to consistent dtypes:
      - Date -> datetime
      - Revenue, Quantity, Cost -> numeric
      - Store, Category, Product, Region -> stripped strings

    Values that fail coercion become NaN (caller should run
    handle_missing_values again afterward if strict cleanliness is required —
    see clean_dataset()).
    """
    df = df.copy()

    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    for col in ["Revenue", "Quantity", "Cost"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in ["Store", "Category", "Product", "Region"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    return df


def clean_dataset(df: pd.DataFrame) -> tuple:
    """
    Runs the full cleaning sequence: standardize types first (so numeric/date
    coercion failures surface as NaN), then drop missing-critical-field rows,
    then remove duplicates.

    Returns (cleaned_df, cleaning_report). cleaning_report mirrors the
    Data Sufficiency Report style used in validator.py, so both can be
    surfaced together at upload time.
    """
    df = standardize_types(df)
    df, missing_removed = handle_missing_values(df)
    df, duplicates_removed = remove_duplicates(df)

    report = {
        "status": "OK",
        "rows_remaining": len(df),
        "rows_dropped_missing_critical_fields": missing_removed,
        "rows_dropped_duplicates": duplicates_removed,
    }

    return df, report


def print_cleaning_report(report: dict):
    """Human-readable console version — companion to print_sufficiency_report()."""
    print("\nCleaning Report")
    print(f"  Rows dropped (missing critical fields): {report['rows_dropped_missing_critical_fields']}")
    print(f"  Rows dropped (duplicates): {report['rows_dropped_duplicates']}")
    print(f"  Rows remaining: {report['rows_remaining']}\n")