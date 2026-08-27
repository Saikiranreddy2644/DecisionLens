# preprocessing/preprocessing_engine.py

import pandas as pd

from preprocessing.validator import validate_dataset, DatasetInsufficientError
from preprocessing.column_mapper import map_columns
from preprocessing.cleaner import clean_dataset
from preprocessing.feature_engineering import engineer_features


def run_preprocessing(df: pd.DataFrame) -> dict:
    """
    Runs the full Phase 1 preprocessing pipeline in the order fixed by the
    frozen architecture:

        map columns -> validate sufficiency -> clean -> engineer features

    Columns are mapped to the standardized schema BEFORE validation, since
    validate_dataset() checks for the standardized names (Date, Store,
    Category, Product, Revenue, Quantity) — not whatever the raw upload
    happened to call them.

    Returns a dict:
        {
            "status": "OK" | "INSUFFICIENT",
            "data": <final processed DataFrame>  (only present if OK),
            "sufficiency_report": <dict from validate_dataset>,
            "cleaning_report": <dict from clean_dataset>  (only present if OK),
        }

    Raises nothing — DatasetInsufficientError is caught here and converted
    into a status="INSUFFICIENT" result, since "can't proceed" is an
    expected, handleable outcome for an upload flow, not an exceptional one.
    """
    df_mapped = map_columns(df)

    try:
        sufficiency_report = validate_dataset(df_mapped)
    except DatasetInsufficientError as e:
        return {
            "status": "INSUFFICIENT",
            "sufficiency_report": {
                "status": "INSUFFICIENT",
                "missing_columns": e.missing_columns,
            },
        }

    df_clean, cleaning_report = clean_dataset(df_mapped)
    df_final = engineer_features(df_clean)

    return {
        "status": "OK",
        "data": df_final,
        "sufficiency_report": sufficiency_report,
        "cleaning_report": cleaning_report,
    }


def print_preprocessing_summary(result: dict):
    """Console banner combining sufficiency + cleaning reports in one place."""
    if result["status"] == "INSUFFICIENT":
        print("\nPreprocessing halted — Dataset Insufficient")
        print(f"  Missing required columns: {result['sufficiency_report']['missing_columns']}\n")
        return

    print("\nPreprocessing complete")
    report = result["sufficiency_report"]
    if report["warnings"]:
        for item, message in report["warnings"].items():
            print(f"  Warning [{item}]: {message}")
    else:
        print("  All required and optional columns present.")

    cr = result["cleaning_report"]
    print(f"  Rows dropped (missing critical fields): {cr['rows_dropped_missing_critical_fields']}")
    print(f"  Rows dropped (duplicates): {cr['rows_dropped_duplicates']}")
    print(f"  Rows remaining: {cr['rows_remaining']}\n")