# tests/test_evidence_aggregator.py
"""
Test Evidence Aggregator + Confidence Calculation against all 4 synthetic scenarios.
"""

import sys
import os
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from preprocessing.column_mapper import map_columns
from preprocessing.validator import validate_dataset
from investigation_engine.evidence_aggregator import run_all_analyzers_and_aggregate


if __name__ == "__main__":
    if len(sys.argv) < 2:
        csv_path = "dataset/superstore.csv"
    else:
        csv_path = sys.argv[1]
    
    print(f"Loading: {csv_path}")
    try:
        df = pd.read_csv(csv_path, encoding="latin1")
    except FileNotFoundError:
        print(f"ERROR: {csv_path} not found")
        sys.exit(1)
    
    # Map & validate
    df = map_columns(df)
    try:
        report = validate_dataset(df)
    except Exception as e:
        print(f"Validation failed: {e}")
        sys.exit(1)
    
    # Run aggregator on Week 26, 2017, Store A, Electronics
    print("\nGenerating unified Investigation Report...")
    investigation = run_all_analyzers_and_aggregate(
        df,
        store="Store A",
        category="Electronics",
        year=2017,
        week=26,
        business_event_anomaly_score=0.91,  # from Anomaly Detection Engine
        kpi_correlation_strong=True  # revenue, profit, units moved together
    )
    
    # Print the report
    investigation.print_report()
    