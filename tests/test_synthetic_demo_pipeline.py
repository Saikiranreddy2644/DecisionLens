# tests/test_synthetic_demo_pipeline.py
"""
Verify the Synthetic Demo dataset passes through the full pipeline
correctly before wiring it into the Phase 8 dashboard.

Checks:
1. Validator accepts it (8 required columns present)
2. Column mapping works
3. Cleaner removes messy rows correctly
4. KPI Engine produces weekly KPIs
5. Anomaly Detection finds anomalies (including our 3 injected ones)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from preprocessing.preprocessing_engine import run_preprocessing
from kpi_engine.kpi_engine import compute_weekly_kpis
from anomaly_detection.business_filter import apply_business_filter
from anomaly_detection.isolation_forest_detector import detect_anomalies
from anomaly_detection.correlation_analyzer import tag_correlations
from anomaly_detection.business_event import build_business_events

DEMO_CSV = "dashboard/demo_data/sample_dataset.csv"

print("="*80)
print("SYNTHETIC DEMO DATASET — PIPELINE VERIFICATION")
print("="*80)

# Step 1: Load
print("\n[Step 1] Loading dataset...")
df_raw = pd.read_csv(DEMO_CSV, encoding="latin1")
print(f"  Raw rows:    {len(df_raw)}")
print(f"  Columns:     {df_raw.columns.tolist()}")

# Step 2: Preprocessing
print("\n[Step 2] Preprocessing (map → validate → clean → engineer)...")
result = run_preprocessing(df_raw)

if result["status"] != "OK":
    print(f"  ✗ FAILED: {result}")
    sys.exit(1)

df = result["data"]
print(f"  ✓ Status:          {result['status']}")
print(f"  Rows after clean:  {len(df)} (removed {len(df_raw) - len(df)} messy rows)")
print(f"  Columns:           {df.columns.tolist()}")

# Step 3: KPI Engine
print("\n[Step 3] KPI Engine...")
weekly_kpis = compute_weekly_kpis(df)
print(f"  ✓ Weekly KPI rows: {len(weekly_kpis)}")
print(f"  Stores found:      {sorted(df['Store'].unique().tolist())}")
print(f"  Categories found:  {sorted(df['Category'].unique().tolist())}")

# Step 4: Anomaly Detection
print("\n[Step 4] Anomaly Detection...")
filtered_kpis, _ = apply_business_filter(weekly_kpis, group_cols=["Store", "Category"])
anomaly_df, _ = detect_anomalies(filtered_kpis, group_cols=["Store", "Category"])
tagged_df = tag_correlations(anomaly_df)
events = build_business_events(tagged_df)
print(f"  ✓ Business Events found: {len(events)}")

# Step 5: Check injected anomalies were detected
print("\n[Step 5] Checking injected anomalies were detected...")
anomalous_groups = set()
for event in events:
    for store, category in event["affected_groups"]:
        anomalous_groups.add((store, category, event["year"], event["week"]))

checks = [
    ("Store A", "Electronics", 2023, 20, "Product-driven: Laptop crash"),
    ("Store B", "Electronics", 2023, 35, "Store-wide decline"),
    ("Store B", "Furniture",   2023, 35, "Store-wide decline"),
    ("Store C", "Electronics", 2023, 48, "Price-driven spike"),
]

all_found = True
for store, category, year, week, label in checks:
    found = (store, category, year, week) in anomalous_groups
    status = "✓ FOUND" if found else "✗ MISSED"
    print(f"  {status}: {label} ({store}/{category} Week {year}-W{week:02d})")
    if not found:
        all_found = False

print("\n" + "="*80)
if all_found:
    print("✓ ALL CHECKS PASSED — Synthetic Demo dataset is pipeline-ready")
else:
    print("⚠ SOME INJECTED ANOMALIES NOT DETECTED — may need anomaly threshold adjustment")
print("="*80 + "\n")