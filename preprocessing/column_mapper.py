# preprocessing/column_mapper.py

import pandas as pd


# ============================================================
# CANONICAL COLUMN MAPPING
# ============================================================
# Every supported retail dataset is converted into this
# internal schema before preprocessing/analysis.
#
# Required:
#   Date, Store, Category, Product, Revenue, Quantity
#
# Optional:
#   Cost, Region, Profit
# ============================================================

COLUMN_MAP = {

    "Date": [
        "Order Date",
        "Date",
        "Invoice_Date",
        "Invoice Date",
        "Transaction Date",
        "Purchase Date",
        "Sale Date",
        "Visit Date"
    ],

    "Store": [
        "Store",
        "Store_ID",
        "Store ID",
        "Store_Name",
        "Store Name",
        "Branch",
        "Branch Name",
        "Outlet",
        "Outlet Name",
        "Location",
        "State",
        "City"
    ],

    "Category": [
        "Category",
        "Product Category",
        "Product_Category",
        "Item Category",
        "Department",
        "Category of Goods"
    ],

    "Product": [
        "Product Name",
        "Product_Name",
        "Product",
        "Item Name",
        "Item_Name",
        "Item",
        "SKU"
    ],

    "Revenue": [
        "Sales",
        "Revenue",
        "Total Sales",
        "Total_Sales",
        "Net Sales",
        "Sale Amount",
        "Sale_Amount",
        "Amount",
        "Total Amount",
        "Total_Amount"
    ],

    "Quantity": [
        "Quantity",
        "Qty",
        "Units Sold",
        "Units_Sold",
        "Units",
        "Order Quantity",
        "Order_Quantity"
    ],

    "Region": [
        "Region",
        "Zone",
        "Territory",
        "Area"
    ],

    "Cost": [
        "Cost",
        "COGS",
        "Unit Cost",
        "Unit_Cost",
        "Cost Price",
        "Cost_Price"
    ],

    "Profit": [
        "Profit",
        "Net Profit",
        "Net_Profit",
        "Gross Profit",
        "Gross_Profit"
    ],
}


# ============================================================
# STORE FALLBACK
# ============================================================
# Used only when Store was not already mapped above.
#
# Priority:
# actual store → branch → outlet → location → state → city
# ============================================================

STORE_COLUMN_CANDIDATES = [
    "Store",
    "Store_ID",
    "Store ID",
    "Store_Name",
    "Store Name",
    "Branch",
    "Branch Name",
    "Outlet",
    "Outlet Name",
    "Location",
    "State",
    "City"
]


# ============================================================
# COLUMN NAME NORMALIZATION
# ============================================================

def normalize_column_name(column):
    """
    Normalizes a column name for comparison.

    Example:
        'Product_Name' -> 'product name'
        'ORDER-DATE'   -> 'order date'
        '  Sales  '    -> 'sales'
    """

    return (
        str(column)
        .strip()
        .lower()
        .replace("_", " ")
        .replace("-", " ")
    )


# ============================================================
# FIND ACTUAL COLUMN
# ============================================================

def find_column(df, candidates):
    """
    Finds a matching dataframe column using normalized names.

    Returns:
        Actual dataframe column name or None.
    """

    normalized_columns = {
        normalize_column_name(col): col
        for col in df.columns
    }

    for candidate in candidates:
        normalized_candidate = normalize_column_name(candidate)

        if normalized_candidate in normalized_columns:
            return normalized_columns[normalized_candidate]

    return None


# ============================================================
# DERIVE DATE
# ============================================================

def derive_date(df):
    """
    Creates Date from Year + Month when a direct Date column
    does not exist.

    This creates a monthly date using the first day of the month.
    """

    if "Date" in df.columns:
        return df

    year_col = find_column(df, ["Year"])
    month_col = find_column(df, ["Month"])

    if year_col is not None and month_col is not None:

        year = pd.to_numeric(df[year_col], errors="coerce")
        month = pd.to_numeric(df[month_col], errors="coerce")

        df["Date"] = pd.to_datetime(
            {
                "year": year,
                "month": month,
                "day": 1
            },
            errors="coerce"
        )

        print(
            f"Date derived from '{year_col}' + '{month_col}'"
        )

    return df


# ============================================================
# MAIN COLUMN MAPPING FUNCTION
# ============================================================

def map_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Converts an uploaded retail dataset into the canonical
    internal schema.

    Canonical schema:

        Date
        Store
        Category
        Product
        Revenue
        Quantity
        Cost (optional)
        Region (optional)
        Profit (optional)
    """

    df = df.copy()

    rename_map = {}

    # --------------------------------------------------------
    # 1. Standard column mapping
    # --------------------------------------------------------

    for standard_name, candidates in COLUMN_MAP.items():

        actual_column = find_column(df, candidates)

        if actual_column is not None:

            # Don't overwrite a column that is already mapped
            if actual_column != standard_name:

                rename_map[actual_column] = standard_name

    # Apply mappings
    df = df.rename(columns=rename_map)

    # --------------------------------------------------------
    # 2. Derive Date if necessary
    # --------------------------------------------------------

    df = derive_date(df)

    # --------------------------------------------------------
    # 3. Store fallback
    # --------------------------------------------------------

    if "Store" not in df.columns:

        actual_store_column = find_column(
            df,
            STORE_COLUMN_CANDIDATES
        )

        if actual_store_column is not None:

            df["Store"] = df[actual_store_column]

            print(
                f"Store mapped from '{actual_store_column}'"
            )

    # --------------------------------------------------------
    # 4. Derive Cost when possible
    # --------------------------------------------------------

    if "Cost" not in df.columns:

        if (
            "Revenue" in df.columns
            and "Profit" in df.columns
        ):

            df["Cost"] = (
                pd.to_numeric(
                    df["Revenue"],
                    errors="coerce"
                )
                -
                pd.to_numeric(
                    df["Profit"],
                    errors="coerce"
                )
            )

            print("Cost derived from Revenue - Profit")

    # --------------------------------------------------------
    # 5. Print mapping information
    # --------------------------------------------------------

    print("\n========== COLUMN MAPPING ==========")

    print("Original → Canonical")

    for original, canonical in rename_map.items():
        print(f"{original} → {canonical}")

    print("\nFinal columns:")
    print(list(df.columns))

    print("====================================\n")

    return df