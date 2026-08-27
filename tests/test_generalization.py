# tests/test_generalization.py
"""
Test pipeline generalization against online_retail dataset.
Diagnostic script to identify what breaks with a new dataset.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from preprocessing.column_mapper import map_columns

print("="*80)
print("GENERALIZATION TEST — Online Retail Dataset")
print("="*80)

# Load raw data
print("\n[1/3] Loading raw dataset...")
try:
    # Try Excel first, then CSV
    if os.path.exists('dataset/online_retail.xlsx'):
        df = pd.read_excel('dataset/online_retail.xlsx')
        print(f"✓ Loaded .xlsx file: {len(df)} rows")
    elif os.path.exists('dataset/online_retail.csv'):
        df = pd.read_csv('dataset/online_retail.csv', encoding='latin1')
        print(f"✓ Loaded .csv file: {len(df)} rows")
    else:
        print("✗ ERROR: Neither online_retail.xlsx nor online_retail.csv found")
        print("  Download from: https://archive.ics.uci.edu/dataset/352/online+retail")
        sys.exit(1)
except Exception as e:
    print(f"✗ ERROR loading file: {e}")
    sys.exit(1)

# Show raw structure
print("\n[2/3] Raw dataset structure:")
print(f"\nColumns: {df.columns.tolist()}")
print(f"\nFirst row:")
print(df.head(1).to_string())
print(f"\nData types:")
print(df.dtypes)

# Try to map columns
print("\n[3/3] Attempting column mapping...")
try:
    df_mapped = map_columns(df)
    print("✓ Mapping successful!")
    print(f"\nMapped columns: {df_mapped.columns.tolist()}")
except Exception as e:
    print(f"✗ MAPPING FAILED: {e}")
    print("\nThis is expected! The Online Retail dataset has different column names.")
    print("Next step: we'll build a flexible column mapper to handle this.")

print("\n" + "="*80)