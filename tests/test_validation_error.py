

# tests/test_validation_error.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from preprocessing.column_mapper import map_columns
from preprocessing.validator import validate_dataset

print("="*80)
print("VALIDATOR TEST")
print("="*80)

# Test 1: Superstore
print("\n[Test 1] Superstore Dataset")
print("-"*80)
try:
    df = pd.read_csv("dataset/Sample - Superstore.csv", encoding="latin1")
    print(f"Loaded: {len(df)} rows")
    print(f"Raw columns: {df.columns.tolist()}\n")
    
    # STEP 1: Map columns
    df_mapped = map_columns(df)
    print(f"Mapped columns: {df_mapped.columns.tolist()}\n")
    
    # STEP 2: Validate
    report = validate_dataset(df_mapped)
    print("✓ VALIDATION PASSED")
    print(f"Status: {report['status']}")
except Exception as e:
    print(f"✗ VALIDATION FAILED:\n{e}")

# Test 2: Online Retail
print("\n[Test 2] Online Retail Dataset")
print("-"*80)
try:
    df = pd.read_excel("dataset/online_retail.xlsx")
    print(f"Loaded: {len(df)} rows")
    print(f"Raw columns: {df.columns.tolist()}\n")
    
    # STEP 1: Try to map columns
    df_mapped = map_columns(df)
    print(f"Mapped columns: {df_mapped.columns.tolist()}\n")
    
    # STEP 2: Validate
    report = validate_dataset(df_mapped)
    print("✓ VALIDATION PASSED")
except Exception as e:
    print(str(e))

print("\n" + "="*80)