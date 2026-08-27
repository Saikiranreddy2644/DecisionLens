# kpi_engine/kpi_engine.py

import pandas as pd

# The grain the Investigation Engine's heaviest analyzers (Product, Category,
# Store) are built to consume — see README architecture. Product-level KPIs
# are computed separately if needed; this module handles the Store+Category
# weekly slice that anomaly detection scans over.
GROUP_COLS = ["Store", "Category"]


def _add_year_week(df: pd.DataFrame, date_col: str = "Date") -> pd.DataFrame:
    """
    Adds ISO Year + Week columns. feature_engineering.py already adds Week,
    but not Year — and Week alone (1-53) collides across different years,
    so weekly grouping needs both. Computed fresh here from Date rather than
    relying on the upstream Week column, to keep this module self-contained.
    """
    df = df.copy()
    dates = pd.to_datetime(df[date_col], errors="coerce")
    iso = dates.dt.isocalendar()
    df["Year"] = iso["year"]
    df["Week"] = iso["week"]
    return df


def compute_weekly_kpis(df: pd.DataFrame, group_cols: list = None) -> pd.DataFrame:
    """
    Aggregates the cleaned/featured dataset into weekly KPIs at the given
    grain (default: Store + Category, matching the Investigation Engine's
    top-weighted analyzers).

    KPIs computed:
      - Revenue (sum)
      - Quantity (sum)
      - Profit (sum) — only if the column is present (soft-required)
      - Cost (sum) — only if the column is present (soft-required)
      - Profit Margin — computed as sum(Profit)/sum(Revenue) per group
        (weighted margin, NOT an average of row-level margins — averaging
        row-level margins would overweight low-revenue rows)

    Returns one row per (Year, Week, *group_cols) combination.
    """
    if group_cols is None:
        group_cols = GROUP_COLS

    df = _add_year_week(df)

    agg_spec = {"Revenue": "sum", "Quantity": "sum"}
    has_profit = "Profit" in df.columns
    has_cost = "Cost" in df.columns
    if has_profit:
        agg_spec["Profit"] = "sum"
    if has_cost:
        agg_spec["Cost"] = "sum"

    grouped = (
        df.groupby(["Year", "Week"] + group_cols, dropna=False)
        .agg(agg_spec)
        .reset_index()
    )

    if has_profit:
        grouped["Profit Margin"] = grouped.apply(
            lambda row: row["Profit"] / row["Revenue"] if row["Revenue"] else None,
            axis=1,
        )

    return grouped.sort_values(["Year", "Week"] + group_cols).reset_index(drop=True)

def compute_company_weekly_kpis(df: pd.DataFrame) -> pd.DataFrame:
    """
    Same weekly aggregation as compute_weekly_kpis(), but with NO Store/Category
    split — one row per week, company-wide.

    This is the baseline the Investigation Engine can check a Store+Category
    anomaly against: "was this store/category having a bad week, or was
    everyone?" A company-wide dip during an anomalous Store+Category week is
    evidence pointing away from a store- or category-specific cause (e.g. a
    seasonal or economy-wide effect) rather than something local.
    """
    return compute_weekly_kpis(df, group_cols=[])


def compute_kpi_availability(df: pd.DataFrame) -> dict:
    """
    Reports which KPIs could actually be computed, given which soft-required
    columns survived preprocessing. Mirrors the Data Sufficiency Report style
    so the dashboard can show "Profit Margin unavailable" etc. consistently
    with the upload-time warnings, instead of just silently omitting columns.
    """
    return {
        "Revenue": True,
        "Quantity": True,
        "Profit": "Profit" in df.columns,
        "Cost": "Cost" in df.columns,
        "Profit Margin": "Profit" in df.columns and "Revenue" in df.columns,
    }


def print_kpi_summary(weekly_kpis: pd.DataFrame):
    """Human-readable console banner, companion to the preprocessing reports."""
    n_weeks = weekly_kpis[["Year", "Week"]].drop_duplicates().shape[0]
    n_groups = weekly_kpis[GROUP_COLS].drop_duplicates().shape[0] if all(c in weekly_kpis.columns for c in GROUP_COLS) else None
    print("\nKPI Engine Summary")
    print(f"  Weekly KPI rows: {len(weekly_kpis)}")
    print(f"  Distinct weeks: {n_weeks}")
    if n_groups is not None:
        print(f"  Distinct Store x Category groups: {n_groups}")
    print()