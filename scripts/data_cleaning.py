"""
Data Cleaning Pipeline
----------------------
Cleans raw Mexico Toy Sales CSV files:
- products.csv
- stores.csv
- inventory.csv
- sales.csv

Rules:
1. Raw CSV files in data/raw/ are NEVER modified.
2. Cleaned CSV files are saved in data/processed/.
3. Removes '$' and formats numeric currency columns.
4. Validates dates, types, and referential integrity.
5. Fills missing 157 store-product combinations with 0 stock to complete
   the full 50 stores x 35 products = 1,750 inventory grid.
6. Calculates unit_price and total_amount for all sales records.
"""

import os
from pathlib import Path
import pandas as pd
import numpy as np

# Use project-relative paths
BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

def ensure_directories():
    """Ensure raw and processed directories exist."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

def clean_products():
    """Clean products.csv"""
    print("\n[1/4] Cleaning products.csv...")
    raw_path = RAW_DIR / "products.csv"
    if not raw_path.exists():
        raise FileNotFoundError(f"Missing raw file: {raw_path}")

    df = pd.read_csv(raw_path)
    initial_rows = len(df)

    # Clean column names
    df = df.rename(columns={
        "Product_ID": "product_id",
        "Product_Name": "product_name",
        "Product_Category": "category",
        "Product_Cost": "cost_price",
        "Product_Price": "selling_price"
    })

    # Clean currency values: remove '$' and extra spaces
    df["cost_price"] = (
        df["cost_price"]
        .astype(str)
        .str.replace("$", "", regex=False)
        .str.strip()
        .astype(float)
        .round(2)
    )
    df["selling_price"] = (
        df["selling_price"]
        .astype(str)
        .str.replace("$", "", regex=False)
        .str.strip()
        .astype(float)
        .round(2)
    )

    # Validation
    assert (df["cost_price"] >= 0).all(), "Negative cost price found!"
    assert (df["selling_price"] >= 0).all(), "Negative selling price found!"
    assert df["product_id"].is_unique, "Duplicate product_id found!"

    # Active flag
    df["active"] = 1

    out_path = PROCESSED_DIR / "cleaned_products.csv"
    df.to_csv(out_path, index=False)
    print(f"  -> Cleaned {len(df)} products saved to {out_path.relative_to(BASE_DIR)}")
    return df

def clean_stores():
    """Clean stores.csv"""
    print("\n[2/4] Cleaning stores.csv...")
    raw_path = RAW_DIR / "stores.csv"
    if not raw_path.exists():
        raise FileNotFoundError(f"Missing raw file: {raw_path}")

    df = pd.read_csv(raw_path)

    # Clean column names
    df = df.rename(columns={
        "Store_ID": "store_id",
        "Store_Name": "store_name",
        "Store_City": "city",
        "Store_Location": "location",
        "Store_Open_Date": "open_date"
    })

    # Validate open_date format (YYYY-MM-DD)
    df["open_date"] = pd.to_datetime(df["open_date"]).dt.strftime("%Y-%m-%d")

    # Validation
    assert df["store_id"].is_unique, "Duplicate store_id found!"

    # Active flag
    df["active"] = 1

    out_path = PROCESSED_DIR / "cleaned_stores.csv"
    df.to_csv(out_path, index=False)
    print(f"  -> Cleaned {len(df)} stores saved to {out_path.relative_to(BASE_DIR)}")
    return df

def clean_inventory(products_df, stores_df, default_reorder_level=10):
    """Clean inventory.csv and fill missing store-product combinations with 0 stock."""
    print("\n[3/4] Cleaning inventory.csv...")
    raw_path = RAW_DIR / "inventory.csv"
    if not raw_path.exists():
        raise FileNotFoundError(f"Missing raw file: {raw_path}")

    raw_df = pd.read_csv(raw_path)
    raw_df = raw_df.rename(columns={
        "Store_ID": "store_id",
        "Product_ID": "product_id",
        "Stock_On_Hand": "stock_on_hand"
    })

    raw_count = len(raw_df)
    print(f"  Raw inventory records: {raw_count}")

    # Generate full Cartesian product of all stores (50) and products (35) = 1,750 pairs
    store_ids = sorted(stores_df["store_id"].unique())
    product_ids = sorted(products_df["product_id"].unique())
    full_grid = pd.MultiIndex.from_product(
        [store_ids, product_ids],
        names=["store_id", "product_id"]
    ).to_frame().reset_index(drop=True)

    total_expected = len(full_grid)
    missing_count = total_expected - raw_count
    print(f"  Target grid: {len(store_ids)} stores x {len(product_ids)} products = {total_expected} combinations.")
    print(f"  Found {missing_count} missing combinations; initializing them with stock_on_hand = 0.")

    # Merge raw inventory onto full grid
    merged_df = pd.merge(full_grid, raw_df, on=["store_id", "product_id"], how="left")
    merged_df["stock_on_hand"] = merged_df["stock_on_hand"].fillna(0).astype(int)

    # Set default reorder_level
    merged_df["reorder_level"] = default_reorder_level

    # Validation
    assert len(merged_df) == total_expected, "Inventory grid count mismatch!"
    assert (merged_df["stock_on_hand"] >= 0).all(), "Negative stock found!"
    assert not merged_df.duplicated(subset=["store_id", "product_id"]).any(), "Duplicate inventory pairs found!"

    out_path = PROCESSED_DIR / "cleaned_inventory.csv"
    merged_df.to_csv(out_path, index=False)
    print(f"  -> Cleaned {len(merged_df)} inventory records saved to {out_path.relative_to(BASE_DIR)}")
    return merged_df

def clean_sales(products_df, stores_df):
    """Clean sales.csv and compute unit_price and total_amount."""
    print("\n[4/4] Cleaning sales.csv (~829k records)...")
    raw_path = RAW_DIR / "sales.csv"
    if not raw_path.exists():
        raise FileNotFoundError(f"Missing raw file: {raw_path}")

    df = pd.read_csv(raw_path)
    df = df.rename(columns={
        "Sale_ID": "sale_id",
        "Date": "sale_date",
        "Store_ID": "store_id",
        "Product_ID": "product_id",
        "Units": "quantity"
    })

    # Validate dates
    df["sale_date"] = pd.to_datetime(df["sale_date"]).dt.strftime("%Y-%m-%d")

    # Map unit_price from products
    price_map = products_df.set_index("product_id")["selling_price"].to_dict()
    df["unit_price"] = df["product_id"].map(price_map).round(2)
    df["total_amount"] = (df["quantity"] * df["unit_price"]).round(2)
    df["notes"] = ""

    # Referential checks
    valid_stores = set(stores_df["store_id"])
    valid_products = set(products_df["product_id"])
    assert df["store_id"].isin(valid_stores).all(), "Unknown store_id found in sales!"
    assert df["product_id"].isin(valid_products).all(), "Unknown product_id found in sales!"
    assert (df["quantity"] > 0).all(), "Non-positive sales quantity found!"
    assert df["sale_id"].is_unique, "Duplicate sale_id found!"

    out_path = PROCESSED_DIR / "cleaned_sales.csv"
    df.to_csv(out_path, index=False)
    print(f"  -> Cleaned {len(df):,} sales records saved to {out_path.relative_to(BASE_DIR)}")
    print(f"     Total Revenue: ${df['total_amount'].sum():,.2f} | Total Units Sold: {df['quantity'].sum():,}")
    return df

def run_pipeline():
    """Execute complete data cleaning pipeline."""
    print("=" * 60)
    print("STARTING DATA CLEANING PIPELINE")
    print("=" * 60)
    print(f"Project root: {BASE_DIR}")
    ensure_directories()

    products_df = clean_products()
    stores_df = clean_stores()
    inventory_df = clean_inventory(products_df, stores_df, default_reorder_level=10)
    sales_df = clean_sales(products_df, stores_df)

    print("\n" + "=" * 60)
    print("DATA CLEANING PIPELINE COMPLETED SUCCESSFULLY")
    print("=" * 60)
    print(f"Cleaned products:   {len(products_df):>8} rows")
    print(f"Cleaned stores:     {len(stores_df):>8} rows")
    print(f"Cleaned inventory:  {len(inventory_df):>8} rows (1,593 raw + 157 zero-stock filled)")
    print(f"Cleaned sales:      {len(sales_df):>8,} rows")
    print(f"Output directory:   {PROCESSED_DIR.relative_to(BASE_DIR)}")

if __name__ == "__main__":
    run_pipeline()
