import pandas as pd

df = pd.read_csv(r"C:\Users\hp 440 G7\OneDrive\Desktop\DecisionLens\dataset\Sample - Superstore.csv", encoding="latin1")  # this dataset often needs latin1 encoding, not utf-8
print(df.columns.tolist())
print(df.shape)
print(df.head())

df['Order Date'] = pd.to_datetime(df['Order Date'])
print(df['Order Date'].min(), "to", df['Order Date'].max())
print((df['Order Date'].max() - df['Order Date'].min()).days / 7, "weeks")


import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from preprocessing.column_mapper import map_columns

df_mapped = map_columns(df)
print(df_mapped.columns.tolist())
print(df_mapped[["Date", "Store", "Category", "Product", "Revenue", "Quantity", "Cost", "Region"]].head())

from preprocessing.cleaner import clean_dataset, print_cleaning_report

df_clean, report = clean_dataset(df_mapped)
print_cleaning_report(report)
print(df_clean.dtypes)
print(df_clean.head())

from preprocessing.feature_engineering import engineer_features

df_final = engineer_features(df_clean)
print(df_final[["Date", "Revenue", "Profit", "Profit Margin", "Month", "Week"]].head())

from preprocessing.preprocessing_engine import run_preprocessing, print_preprocessing_summary

result = run_preprocessing(df)  # raw df, straight from read_csv
print_preprocessing_summary(result)

if result["status"] == "OK":
    print(result["data"].head())

from kpi_engine.kpi_engine import compute_weekly_kpis, print_kpi_summary

weekly_kpis = compute_weekly_kpis(result["data"])
print_kpi_summary(weekly_kpis)
print(weekly_kpis.head(10))

from anomaly_detection.business_filter import apply_business_filter, print_filter_report

filtered_kpis, filter_report = apply_business_filter(weekly_kpis)
print_filter_report(filter_report)

from anomaly_detection.business_filter import compute_group_stats

stats = compute_group_stats(weekly_kpis)
print(stats["weeks_present"].describe())
print(stats["weeks_present"].value_counts().sort_index().head(15))

from anomaly_detection.isolation_forest_detector import detect_anomalies, print_anomaly_report

anomaly_results, anomaly_report = detect_anomalies(filtered_kpis)
print_anomaly_report(anomaly_report)
print(anomaly_results[anomaly_results["is_anomaly"]][["Store", "Category", "Year", "Week", "Revenue", "Profit Margin", "Quantity", "anomaly_score"]].sort_values("anomaly_score", ascending=False))

from anomaly_detection.correlation_analyzer import tag_correlations, print_correlation_summary
from anomaly_detection.business_event import build_business_events, print_business_event_summary

tagged = tag_correlations(anomaly_results)
print_correlation_summary(tagged)

events = build_business_events(tagged)
print_business_event_summary(events)

from anomaly_detection.business_event import build_business_events, print_events_table

events = build_business_events(tagged)
print_events_table(events, limit=20)  # first 20; drop limit to see all 169

from investigation_engine.product_analyzer import analyze_product, print_product_analysis

# Pick a real flagged event from your events table — e.g. one row from anomaly_results
row = anomaly_results[anomaly_results["is_anomaly"]].iloc[0]
result = analyze_product(result["data"], store=row["Store"], category=row["Category"], year=int(row["Year"]), week=int(row["Week"]))
print_product_analysis(result)