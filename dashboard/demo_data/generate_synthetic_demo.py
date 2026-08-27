# dashboard/demo_data/generate_synthetic_demo.py
"""
Synthetic demo dataset generator for DecisionLens Phase 8.

Generates a realistic but deliberately messy retail dataset with:
- 8 required columns (Date, Store, Category, Product, Revenue, Quantity, Region, Cost)
- Deliberate inconsistencies the cleaner already handles:
  * Duplicate rows
  * Missing Cost values (soft-required)
  * Zero/negative Revenue rows
  * Mixed date formats
  * Extra whitespace in string columns
  * Zero Quantity rows
- 3 injected anomalies:
  * Product-driven: Laptop sales crash in Store A, Week 20
  * Store-wide: All categories decline in Store B, Week 35
  * Price-driven: Price spike in Store C Electronics, Week 48

Usage:
  python dashboard/demo_data/generate_synthetic_demo.py
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta

np.random.seed(99)

STORES = ["Store A", "Store B", "Store C", "Store D"]
REGIONS = ["East", "West", "South", "Central"]
STORE_REGION = dict(zip(STORES, REGIONS))

CATEGORIES = ["Electronics", "Furniture", "Office Supplies"]
PRODUCTS = {
    "Electronics": ["Laptop", "Monitor", "Mouse", "Keyboard"],
    "Furniture": ["Desk", "Chair", "Shelf", "Table"],
    "Office Supplies": ["Pen", "Paper", "Folder", "Stapler"],
}
REVENUE_BASE = {
    "Laptop": 5000, "Monitor": 1500, "Mouse": 300, "Keyboard": 400,
    "Desk": 3000, "Chair": 2500, "Shelf": 1200, "Table": 2000,
    "Pen": 50, "Paper": 100, "Folder": 75, "Stapler": 80,
}


def _generate_baseline(n_years=2, n_transactions_per_week=20):
    """Generate clean baseline data — messiness injected separately."""
    rows = []
    start_date = datetime(2022, 1, 3)  # Monday

    for week_offset in range(n_years * 52):
        week_date = start_date + timedelta(weeks=week_offset)

        for store in STORES:
            region = STORE_REGION[store]
            for category in CATEGORIES:
                products = PRODUCTS[category]

                n_tx = np.random.randint(n_transactions_per_week - 5,
                                         n_transactions_per_week + 5)
                for _ in range(n_tx):
                    product = np.random.choice(products)
                    base = REVENUE_BASE[product]
                    revenue = base * np.random.uniform(0.85, 1.15)
                    unit_price = base / np.random.randint(2, 6)
                    quantity = max(1, int(revenue / unit_price))
                    revenue = round(quantity * unit_price, 2)
                    cost = round(revenue * np.random.uniform(0.60, 0.70), 2)

                    rows.append({
                        "Date": week_date.strftime("%Y-%m-%d"),
                        "Store": store,
                        "Region": region,
                        "Category": category,
                        "Product": product,
                        "Revenue": revenue,
                        "Quantity": quantity,
                        "Cost": cost,
                    })

    return pd.DataFrame(rows)


def _inject_anomalies(df):
    """Inject 3 controlled anomalies into the dataset."""
    df = df.copy()
    df["_date"] = pd.to_datetime(df["Date"])
    df["_week"] = df["_date"].dt.isocalendar().week.astype(int)
    df["_year"] = df["_date"].dt.isocalendar().year.astype(int)

    # Anomaly 1: Product-driven — Laptop crashes in Store A, Week 20, 2023
    # Anomaly 1: Product-driven — Laptop completely absent (stockout) from Store A
    # Week 20, 2023. Also reduce other Electronics by 80% so the category-level
    # signal is strong enough for Isolation Forest to flag at Store+Category grain.
    mask1_laptop = ((df["Store"] == "Store A") & (df["Product"] == "Laptop") &
                    (df["_year"] == 2023) & (df["_week"] == 20))
    df = df[~mask1_laptop]  # remove Laptop entirely

    mask1_others = ((df["Store"] == "Store A") & (df["Category"] == "Electronics") &
                    (df["_year"] == 2023) & (df["_week"] == 20))
    df.loc[mask1_others, "Revenue"] = df.loc[mask1_others, "Revenue"] * 0.15
    df.loc[mask1_others, "Quantity"] = (df.loc[mask1_others, "Quantity"] * 0.15).clip(lower=1).astype(int)
    df.loc[mask1_others, "Cost"] = df.loc[mask1_others, "Revenue"] * 0.65
    
    

    # Anomaly 2: Store-wide — all categories decline in Store B, Week 35, 2023
    mask2 = ((df["Store"] == "Store B") &
             (df["_year"] == 2023) & (df["_week"] == 35))
    df.loc[mask2, "Revenue"] = df.loc[mask2, "Revenue"] * 0.25
    df.loc[mask2, "Quantity"] = (df.loc[mask2, "Quantity"] * 0.25).clip(lower=1).astype(int)
    df.loc[mask2, "Cost"] = df.loc[mask2, "Revenue"] * 0.65

    # Anomaly 3: Price-driven — price spike in Store C Electronics, Week 48, 2023
    mask3 = ((df["Store"] == "Store C") & (df["Category"] == "Electronics") &
             (df["_year"] == 2023) & (df["_week"] == 48))
    df.loc[mask3, "Revenue"] = df.loc[mask3, "Revenue"] * 1.45
    df.loc[mask3, "Quantity"] = (df.loc[mask3, "Quantity"] * 0.60).clip(lower=1).astype(int)

    df = df.drop(columns=["_date", "_week", "_year"])
    return df


def _inject_messiness(df):
    """Inject deliberate inconsistencies that the preprocessing pipeline handles."""
    df = df.copy()
    n = len(df)

    # 1. Duplicate rows (~2% of data)
    n_duplicates = int(n * 0.02)
    duplicate_rows = df.sample(n=n_duplicates, random_state=1)
    df = pd.concat([df, duplicate_rows], ignore_index=True)

    # 2. Mixed date formats for ~5% of rows
    mixed_date_idx = df.sample(frac=0.05, random_state=2).index
    df.loc[mixed_date_idx, "Date"] = pd.to_datetime(
        df.loc[mixed_date_idx, "Date"]
    ).dt.strftime("%d/%m/%Y")

    # 3. Extra whitespace in Store/Category/Product for ~3% of rows
    whitespace_idx = df.sample(frac=0.03, random_state=3).index
    df.loc[whitespace_idx, "Store"] = "  " + df.loc[whitespace_idx, "Store"] + "  "
    df.loc[whitespace_idx, "Category"] = df.loc[whitespace_idx, "Category"] + " "

    # 4. Missing Cost values (~8% of rows — soft-required, shouldn't block pipeline)
    missing_cost_idx = df.sample(frac=0.08, random_state=4).index
    df.loc[missing_cost_idx, "Cost"] = np.nan

    # 5. Zero Revenue rows (~1% — invalid, cleaner should drop these)
    zero_rev_idx = df.sample(frac=0.01, random_state=5).index
    df.loc[zero_rev_idx, "Revenue"] = 0

    # 6. Zero Quantity rows (~0.5%)
    zero_qty_idx = df.sample(frac=0.005, random_state=6).index
    df.loc[zero_qty_idx, "Quantity"] = 0

    # 7. Negative Revenue rows (~0.3%)
    neg_rev_idx = df.sample(frac=0.003, random_state=7).index
    df.loc[neg_rev_idx, "Revenue"] = -abs(df.loc[neg_rev_idx, "Revenue"])

    # Shuffle so messiness is distributed throughout, not at the end
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)

    return df


def generate_synthetic_demo(output_path: str = "dashboard/demo_data/sample_dataset.csv"):
    """Full pipeline: baseline → anomalies → messiness → save."""
    print("Generating baseline...")
    df = _generate_baseline(n_years=2)
    print(f"  Baseline rows: {len(df)}")

    print("Injecting anomalies...")
    df = _inject_anomalies(df)

    print("Injecting messiness...")
    df = _inject_messiness(df)
    print(f"  Final rows (after duplicates etc.): {len(df)}")

    # Summary of messiness injected
    print(f"\nMessiness summary:")
    print(f"  Duplicate rows injected:     ~{int(len(df)*0.02)}")
    print(f"  Mixed date formats:          ~{int(len(df)*0.05)}")
    print(f"  Missing Cost values:         ~{int(len(df)*0.08)}")
    print(f"  Zero Revenue rows:           ~{int(len(df)*0.01)}")
    print(f"  Zero Quantity rows:          ~{int(len(df)*0.005)}")
    print(f"  Negative Revenue rows:       ~{int(len(df)*0.003)}")
    print(f"  Whitespace in strings:       ~{int(len(df)*0.03)}")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"\n✓ Saved to: {output_path}")
    print(f"  Rows: {len(df)}")
    print(f"  Columns: {df.columns.tolist()}")
    return df


if __name__ == "__main__":
    generate_synthetic_demo()