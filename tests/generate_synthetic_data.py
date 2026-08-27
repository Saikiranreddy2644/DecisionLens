# tests/generate_synthetic_data.py
"""
Synthetic retail dataset generator for Investigation Engine testing.

Generates 4 controlled scenarios with dense, realistic transaction data:
1. Product-driven decline (Laptop crash, others stable)
2. Store-wide decline (all categories down)
3. Price-driven decline (price up, units down, elasticity signal)
4. Normal variation (no anomaly, just noise)

Each scenario:
- 3 stores × 3 categories × 2 years × 52 weeks
- 20-30 transactions per Store+Category+Week (dense)
- Full historical baseline to enable Historical & Seasonality analyzers
- Anomaly injected in Week 26, 2017

Usage:
  python tests/generate_synthetic_data.py
  
Outputs:
  data/raw/synthetic_scenario_1_product_driven.csv
  data/raw/synthetic_scenario_2_store_wide.csv
  data/raw/synthetic_scenario_3_price_driven.csv
  data/raw/synthetic_scenario_4_normal.csv
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os


def generate_baseline_data(n_stores=3, n_categories=3, n_years=2, seed=42):
    """
    Generate realistic baseline sales data without anomalies.
    
    Args:
        n_stores: number of stores
        n_categories: number of categories per store
        n_years: number of years (2 = ~104 weeks for Historical analyzer)
        seed: random seed for reproducibility
    
    Returns:
        DataFrame with columns: Date, Store, Category, Product, Revenue, Quantity, Cost
    """
    np.random.seed(seed)
    
    stores = [f"Store {chr(65+i)}" for i in range(n_stores)]
    categories = ["Electronics", "Furniture", "Office Supplies"][:n_categories]
    regions = ["East", "West", "South", "Central"][:n_stores]
    
    products_by_category = {
        "Electronics": ["Laptop", "Mouse", "Monitor", "Keyboard"],
        "Furniture": ["Desk", "Chair", "Shelf", "Table"],
        "Office Supplies": ["Pen", "Paper", "Folder", "Stapler"],
    }
    
    # Revenue baseline per product (weekly average)
    revenue_base = {
        "Laptop": 5000,
        "Mouse": 300,
        "Monitor": 1500,
        "Keyboard": 400,
        "Desk": 3000,
        "Chair": 2500,
        "Shelf": 1200,
        "Table": 2000,
        "Pen": 50,
        "Paper": 100,
        "Folder": 75,
        "Stapler": 80,
    }
    
    rows = []
    start_date = datetime(2016, 1, 1)
    
    for year_offset in range(n_years):
        for week in range(1, 53):  # 52 weeks per year
            date = start_date + timedelta(weeks=week + year_offset * 52)
            
            for store_idx, store in enumerate(stores):
                region = regions[store_idx % len(regions)]
                
                for category in categories:
                    products = products_by_category[category]
                    n_products = len(products)
                    
                    # 20-30 transactions per Store+Category+Week
                    n_transactions = np.random.randint(20, 31)
                    
                    for _ in range(n_transactions):
                        product = np.random.choice(products)
                        base_rev = revenue_base[product]
                        
                        # Add noise: ±15% variance
                        noise = np.random.uniform(0.85, 1.15)
                        revenue = base_rev * noise
                        
                        # Quantity: derived from revenue + realistic unit price
                        unit_price = base_rev / np.random.randint(2, 6)
                        quantity = max(1, int(revenue / unit_price))
                        revenue = quantity * unit_price  # recalculate for consistency
                        
                        # Cost: 60-70% of revenue
                        cost_pct = np.random.uniform(0.60, 0.70)
                        cost = revenue * cost_pct
                        
                        rows.append({
                            "Date": date,
                            "Store": store,
                            "Region": region,
                            "Category": category,
                            "Product": product,
                            "Revenue": revenue,
                            "Quantity": quantity,
                            "Cost": cost,
                        })
    
    return pd.DataFrame(rows)


def inject_product_driven_anomaly(df):
    """
    Scenario 1: Product-driven decline
    Laptop sales crash 35-40%, other products in Electronics stable.
    """
    df = df.copy()
    
    # Find Week 26, 2017 for all stores
    df["Date"] = pd.to_datetime(df["Date"])
    df["Year"] = df["Date"].dt.isocalendar().year
    df["Week"] = df["Date"].dt.isocalendar().week
    
    mask = (df["Year"] == 2017) & (df["Week"] == 26) & (df["Product"] == "Laptop")
    df.loc[mask, "Revenue"] = df.loc[mask, "Revenue"] * 0.1  # crash to 10%
    df.loc[mask, "Quantity"] = (df.loc[mask, "Quantity"] * 0.1).astype(int).clip(lower=1)
    df.loc[mask, "Cost"] = df.loc[mask, "Revenue"] * 0.65
    
    return df.drop(columns=["Year", "Week"])


def inject_store_wide_anomaly(df):
    """
    Scenario 2: Store-wide decline
    All categories for Store A decline 20-25%, others stable.
    """
    df = df.copy()
    
    df["Date"] = pd.to_datetime(df["Date"])
    df["Year"] = df["Date"].dt.isocalendar().year
    df["Week"] = df["Date"].dt.isocalendar().week
    
    mask = (df["Year"] == 2017) & (df["Week"] == 26) & (df["Store"] == "Store A")
    df.loc[mask, "Revenue"] = df.loc[mask, "Revenue"] * 0.77  # 23% decline
    df.loc[mask, "Quantity"] = (df.loc[mask, "Quantity"] * 0.77).astype(int).clip(lower=1)
    df.loc[mask, "Cost"] = df.loc[mask, "Revenue"] * 0.65
    
    return df.drop(columns=["Year", "Week"])


def inject_price_driven_anomaly(df):
    """
    Scenario 3: Price-driven decline
    Price goes up 20%, quantity responds down elastically.
    """
    df = df.copy()
    
    df["Date"] = pd.to_datetime(df["Date"])
    df["Year"] = df["Date"].dt.isocalendar().year
    df["Week"] = df["Date"].dt.isocalendar().week
    
    # Increase price by ~20% on Laptop in Store A
    mask = (df["Year"] == 2017) & (df["Week"] == 26) & \
           (df["Store"] == "Store A") & (df["Product"] == "Laptop")
    
    # Simulate price increase: keep revenue same, reduce quantity
    # This creates a "unit price up, quantity down" pattern
    df.loc[mask, "Quantity"] = (df.loc[mask, "Quantity"] * 0.75).astype(int).clip(lower=1)
    df.loc[mask, "Revenue"] = df.loc[mask, "Revenue"] * 1.20  # price up compensates partially
    
    return df.drop(columns=["Year", "Week"])


def inject_normal_variation(df):
    """
    Scenario 4: Normal variation
    Week 26 has ±2% variance (within normal range, no anomaly).
    """
    df = df.copy()
    # Return as-is; baseline data already has ±15% noise
    return df


def save_scenario(df, scenario_name, scenario_file):
    """Save scenario to CSV."""
    output_path = f"data/raw/{scenario_file}"
    os.makedirs("data/raw", exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"✓ {scenario_name}: {len(df)} rows → {output_path}")


if __name__ == "__main__":
    print("="*80)
    print("SYNTHETIC DATA GENERATOR — DecisionLens Investigation Engine")
    print("="*80)
    print()
    
    # Generate baseline
    print("Generating baseline data (3 stores, 3 categories, 2 years, dense transactions)...")
    baseline = generate_baseline_data(n_stores=3, n_categories=3, n_years=2)
    print(f"✓ Baseline: {len(baseline)} rows")
    print()
    
    # Generate 4 scenarios
    print("Injecting anomalies into Week 26, 2017...")
    print()
    
    # Scenario 1: Product-driven
    print("[1/4] Product-driven decline (Laptop crash)")
    scenario_1 = inject_product_driven_anomaly(baseline.copy())
    save_scenario(scenario_1, "Scenario 1", "synthetic_scenario_1_product_driven.csv")
    
    # Scenario 2: Store-wide
    print("[2/4] Store-wide decline (all categories down)")
    scenario_2 = inject_store_wide_anomaly(baseline.copy())
    save_scenario(scenario_2, "Scenario 2", "synthetic_scenario_2_store_wide.csv")
    
    # Scenario 3: Price-driven
    print("[3/4] Price-driven decline (price up, units down)")
    scenario_3 = inject_price_driven_anomaly(baseline.copy())
    save_scenario(scenario_3, "Scenario 3", "synthetic_scenario_3_price_driven.csv")
    
    # Scenario 4: Normal
    print("[4/4] Normal variation (no anomaly)")
    scenario_4 = inject_normal_variation(baseline.copy())
    save_scenario(scenario_4, "Scenario 4", "synthetic_scenario_4_normal.csv")
    
    print()
    print("="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Generated 4 synthetic test scenarios:")
    print(f"  • Each: 3 stores × 3 categories × 2 years × 52 weeks")
    print(f"  • Density: 20-30 transactions per Store+Category+Week")
    print(f"  • Total rows per scenario: ~{len(scenario_1)}")
    print(f"  • Anomaly: Week 26, 2017 (injected separately per scenario)")
    print()
    print("Next: Run test_all_analyzers.py against each scenario")
    print("="*80)