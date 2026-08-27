# tests/test_all_analyzers.py
"""
Comprehensive test of all 8 Investigation Engine analyzers
against real Superstore data.

Usage:
  python tests/test_all_analyzers.py path/to/superstore.csv
  
This script:
1. Loads and maps your Superstore dataset
2. Finds Store+Category+Week combinations with real anomalies
3. Runs all 8 analyzers on each
4. Prints results in a readable format
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sys
import pandas as pd
import numpy as np
from preprocessing.column_mapper import map_columns
from preprocessing.validator import validate_dataset, print_sufficiency_report
from investigation_engine.product_analyzer import analyze_product, print_product_analysis
from investigation_engine.category_analyzer import analyze_category, print_category_analysis
from investigation_engine.store_analyzer import analyze_store, print_store_analysis
from investigation_engine.region_analyzer import analyze_region, print_region_analysis
from investigation_engine.price_analyzer import analyze_price, print_price_analysis
from investigation_engine.historical_analyzer import analyze_historical, print_historical_analysis
from investigation_engine.top_contributor_analyzer import analyze_top_contributor, print_top_contributor_analysis
from investigation_engine.seasonality_analyzer import analyze_seasonality, print_seasonality_analysis


def run_all_analyzers(df, store, category, year, week):
    """Run all 8 analyzers on a single Store+Category+Week combination."""
    
    print("\n" + "="*80)
    print(f"TESTING ALL 8 ANALYZERS: {store} / {category} / {year}-W{week:02d}")
    print("="*80)
    
    results = {}
    
    # Run all 8 analyzers
    print("\n[1/8] Product Analyzer...")
    results['product'] = analyze_product(df, store, category, year, week)
    print_product_analysis(results['product'])
    
    print("[2/8] Category Analyzer...")
    results['category'] = analyze_category(df, store, category, year, week)
    print_category_analysis(results['category'])
    
    print("[3/8] Store Analyzer...")
    results['store'] = analyze_store(df, store, category, year, week)
    print_store_analysis(results['store'])
    
    print("[4/8] Region Analyzer...")
    results['region'] = analyze_region(df, store, category, year, week)
    print_region_analysis(results['region'])
    
    print("[5/8] Price Analyzer...")
    results['price'] = analyze_price(df, store, category, year, week)
    print_price_analysis(results['price'])
    
    print("[6/8] Historical Analyzer...")
    results['historical'] = analyze_historical(df, store, category, year, week)
    print_historical_analysis(results['historical'])
    
    print("[7/8] Top Contributor Analyzer...")
    results['top_contributor'] = analyze_top_contributor(df, store, category, year, week)
    print_top_contributor_analysis(results['top_contributor'])
    
    print("[8/8] Seasonality Analyzer...")
    results['seasonality'] = analyze_seasonality(df, store, category, year, week)
    print_seasonality_analysis(results['seasonality'])
    
    # --- Summary ---
    sufficient = sum(1 for r in results.values() if r.get('sufficient_data', False))
    coverage = f"{sufficient}/8 ({100*sufficient/8:.0f}%)"
    scores = [r.get('analyzer_score') for r in results.values() if r.get('analyzer_score') is not None]
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Evidence Coverage:  {coverage}")
    print(f"Analyzer Scores:    {[round(s, 3) for s in scores]}")
    print(f"Mean Score:         {round(np.mean(scores), 3) if scores else 'N/A'}")
    print(f"Max Score:          {round(max(scores), 3) if scores else 'N/A'}")
    print()
    
    return results


def find_anomalies(df, top_n=5):
    """Find the top N Store+Category+Week combinations with the largest
    week-over-week revenue declines (likely anomalies)."""
    
    df = df.copy()
    dates = pd.to_datetime(df["Date"], errors="coerce")
    df["Year"] = dates.dt.isocalendar().year
    df["Week"] = dates.dt.isocalendar().week
    
    weekly = df.groupby(["Store", "Category", "Year", "Week"])["Revenue"].sum().reset_index()
    weekly = weekly.sort_values("Year").sort_values(["Store", "Category", "Year", "Week"])
    
    # Compute week-over-week change
    weekly["prev_revenue"] = weekly.groupby(["Store", "Category"])["Revenue"].shift(1)
    weekly["pct_change"] = (weekly["Revenue"] - weekly["prev_revenue"]) / weekly["prev_revenue"]
    weekly = weekly.dropna(subset=["pct_change"])
    
    # Find largest declines
    anomalies = weekly[weekly["pct_change"] < -0.1].copy()  # at least -10%
    anomalies = anomalies.sort_values("pct_change").head(top_n)
    
    return anomalies[["Store", "Category", "Year", "Week", "Revenue", "pct_change"]]


if __name__ == "__main__":
    if len(sys.argv) < 2:
        csv_path = "dataset/superstore.csv"
        print(f"No CSV path provided. Using default: {csv_path}")
    else:
        csv_path = sys.argv[1]
    
    print(f"Loading dataset: {csv_path}")
    
    try:
        df = pd.read_csv(csv_path, encoding="latin1")
    except FileNotFoundError:
        print(f"ERROR: File not found at {csv_path}")
        sys.exit(1)
    
    print(f"Raw dataset: {df.shape[0]} rows, {len(df.columns)} columns")
    
    df = map_columns(df)
    print(f"Mapped columns: {df.columns.tolist()}")
    
    try:
        report = validate_dataset(df)
        print_sufficiency_report(report)
    except Exception as e:
        print(f"Validation failed: {e}")
        sys.exit(1)
    
    # Test the injected anomaly at Week 26, 2017
    print("\nTesting anomaly at Week 26, 2017, Store A, Electronics")
    print("(where synthetic anomaly was injected)\n")
    
    run_all_analyzers(
        df,
        store="Store A",
        category="Electronics",
        year=2017,
        week=26
    )