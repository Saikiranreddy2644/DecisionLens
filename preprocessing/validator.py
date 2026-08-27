# preprocessing/validator.py

import pandas as pd
from utils.constants import (
    HARD_REQUIRED_COLUMNS,
    SOFT_REQUIRED_COLUMNS,
    MIN_WEEKS_FOR_HISTORY,
    MIN_WEEKS_FOR_SEASONALITY,
)


class DatasetInsufficientError(Exception):
    """Raised when the dataset is missing hard-required columns."""
    def __init__(self, missing_columns):
        self.missing_columns = missing_columns
        message = (
            "Dataset Insufficient — Missing Required Columns\n"
            f"Missing: {missing_columns}\n"
            f"This dataset cannot be processed. Required columns: {HARD_REQUIRED_COLUMNS}"
        )
        super().__init__(message)


def check_hard_required(df: pd.DataFrame) -> list:
    """Returns a list of missing hard-required columns. Empty list = OK."""
    return [col for col in HARD_REQUIRED_COLUMNS if col not in df.columns]


def check_soft_required(df: pd.DataFrame) -> dict:
    """
    Returns a dict of {column_name: impact_message} for each
    soft-required column that is missing.
    """
    warnings = {}
    for col, impact in SOFT_REQUIRED_COLUMNS.items():
        if col not in df.columns:
            warnings[col] = impact
    return warnings


def check_history_sufficiency(df: pd.DataFrame, date_col: str = "Date") -> dict:
    """
    Checks whether there's enough date range for Historical/Seasonality analyzers.
    Returns a dict describing what will be skipped, if anything.
    """
    warnings = {}

    if date_col not in df.columns:
        # Already caught by hard-required check if Date is missing entirely,
        # but guard here in case this function is called independently.
        return warnings

    dates = pd.to_datetime(df[date_col], errors="coerce")
    distinct_weeks = dates.dt.isocalendar().week.nunique()

    if distinct_weeks < MIN_WEEKS_FOR_HISTORY:
        warnings["Historical"] = (
            f"Only {distinct_weeks} week(s) of data found "
            f"(need {MIN_WEEKS_FOR_HISTORY}+). Historical Analyzer will be skipped."
        )

    if distinct_weeks < MIN_WEEKS_FOR_SEASONALITY:
        warnings["Seasonality"] = (
            f"Only {distinct_weeks} week(s) of data found "
            f"(need ~{MIN_WEEKS_FOR_SEASONALITY} for year-over-year comparison). "
            f"Seasonality Analyzer will be skipped."
        )

    return warnings


def validate_dataset(df: pd.DataFrame) -> dict:
    """
    Runs the full sufficiency check on an uploaded dataset.

    Returns a Data Sufficiency Report (dict) if the dataset can proceed.
    Raises DatasetInsufficientError if it cannot.
    """
    missing_hard = check_hard_required(df)
    if missing_hard:
        raise DatasetInsufficientError(missing_hard, actual_columns=df.columns.tolist())

    soft_warnings = check_soft_required(df)
    history_warnings = check_history_sufficiency(df)

    report = {
        "status": "OK",
        "hard_required_ok": True,
        "warnings": {**soft_warnings, **history_warnings},
    }

    return report


class DatasetInsufficientError(Exception):
    """Raised when the dataset is missing hard-required columns."""
    def __init__(self, missing_columns, actual_columns=None):
        self.missing_columns = missing_columns
        
        required_str = ", ".join(HARD_REQUIRED_COLUMNS)
        missing_str = ", ".join(missing_columns)
        
        message = f"""
================================================================================
Dataset Not Supported
================================================================================

Decision Lens V1 requires the following columns:
{required_str}.

Missing:
{missing_str}...

Your dataset columns:
{", ".join(actual_columns) if actual_columns else "Unknown"}

This dataset cannot be processed by Decision Lens V1.
================================================================================
"""
        super().__init__(message)