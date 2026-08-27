# investigation_engine/batch_pipeline.py
"""
Batch Investigation Pipeline — orchestrates Phases 1 through 5 across
EVERY detected anomaly in a dataset, and persists the results to SQLite.
"""

import pandas as pd

from preprocessing.preprocessing_engine import run_preprocessing
from kpi_engine.kpi_engine import compute_weekly_kpis
from anomaly_detection.business_filter import apply_business_filter
from anomaly_detection.isolation_forest_detector import detect_anomalies
from anomaly_detection.correlation_analyzer import tag_correlations
from anomaly_detection.business_event import build_business_events
from investigation_engine.evidence_aggregator import run_all_analyzers_and_aggregate
from database.db_manager import initialize_schema, get_connection, insert_investigation_report


def run_batch_investigation(
    csv_path: str,
    db_path: str = "data/decisionlens.db"
) -> dict:
    """
    Run the DecisionLens batch investigation pipeline.

    Input:
        csv_path - path to the input retail CSV dataset
        db_path  - path where the SQLite database is stored

    Output:
        {
            "status": "OK" | "FAILED",
            "total_events_found": int,
            "total_investigations_created": int,
            "database_path": str,
            "errors": list
        }
    """
    errors = []

    print("[Phase 1] Preprocessing...")
    df_raw = pd.read_csv(r"C:\Users\hp 440 G7\OneDrive\Desktop\DecisionLens\dataset\Sample - Superstore.csv", encoding="latin1")
    prep_result = run_preprocessing(df_raw)

    if prep_result["status"] != "OK":
        return {
            "status": "FAILED",
            "total_events_found": 0,
            "total_investigations_created": 0,
            "database_path": db_path,
            "errors": [f"Preprocessing failed: {prep_result['sufficiency_report']}"],
        }

    df_processed = prep_result["data"]
    print(f"  Processed {len(df_processed)} rows")

    print("[Phase 2] Computing weekly KPIs...")
    weekly_kpis = compute_weekly_kpis(df_processed)
    print(f"  {len(weekly_kpis)} Store+Category+Week KPI rows")

    print("[Phase 3] Detecting anomalies...")
    filtered_kpis, filter_report = apply_business_filter(weekly_kpis, group_cols=["Store", "Category"])
    anomaly_df, anomaly_report = detect_anomalies(filtered_kpis, group_cols=["Store", "Category"])
    tagged_df = tag_correlations(anomaly_df)

    events = build_business_events(tagged_df)
    print(f"  {len(events)} Business Events found")

    initialize_schema(db_path)
    conn = get_connection(db_path)

    print("[Phase 4-5] Running Investigation Engine on each anomaly...")
    total_investigations = 0
    processed_groups = set()

    for i, event in enumerate(events, start=1):
        year = event["year"]
        week = event["week"]

        score_lookup = {
            (row["Store"], row["Category"]): row.get("anomaly_score", 0.5)
            for row in event["anomaly_rows"]
        }

        for store, category in event["affected_groups"]:
            key = (store, category, year, week)
            if key in processed_groups:
                continue
            processed_groups.add(key)

            real_anomaly_score = score_lookup.get((store, category), 0.5)
            normalized_score = max(0.0, min(1.0, 0.5 + real_anomaly_score))

            try:
                report = run_all_analyzers_and_aggregate(
                    df_processed,
                    store=store,
                    category=category,
                    year=year,
                    week=week,
                    business_event_anomaly_score=normalized_score,
                    kpi_correlation_strong=True,
                )
                insert_investigation_report(conn, report)
                total_investigations += 1
            except Exception as e:
                errors.append(f"Event {event['event_id']} ({store}/{category}/{year}-W{week}): {e}")

        if i % 20 == 0:
            print(f"  ...processed {i}/{len(events)} events")

    conn.close()

    print(f"\n✓ Batch investigation complete: {total_investigations} investigations stored")
    if errors:
        print(f"  {len(errors)} errors encountered (see result['errors'])")

    return {
        "status": "OK",
        "total_events_found": len(events),
        "total_investigations_created": total_investigations,
        "database_path": db_path,
        "errors": errors,
    }


def print_batch_summary(result: dict):
    """Human-readable console summary."""
    print("\n" + "=" * 80)
    print("BATCH INVESTIGATION PIPELINE — SUMMARY")
    print("=" * 80)
    print(f"Status:                    {result['status']}")
    print(f"Business Events Found:     {result['total_events_found']}")
    print(f"Investigations Created:    {result['total_investigations_created']}")
    print(f"Database:                 {result['database_path']}")
    print(f"Errors:                    {len(result['errors'])}")
    if result["errors"]:
        print("\nFirst 5 errors:")
        for err in result["errors"][:5]:
            print(f"  - {err}")
    print("=" * 80 + "\n")