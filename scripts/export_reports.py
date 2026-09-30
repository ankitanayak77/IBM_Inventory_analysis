"""
Smart Inventory & Sales Analysis System - Standalone Report Exporter
--------------------------------------------------------------------
Phase 12: Reusable Export Pipeline for Normalized Power BI Datasets

Generates 6 clean, normalized CSV files in exports/powerbi/:
1. sales_daily.csv         (Grain: 1 row per date, 638 rows)
2. sales_category.csv      (Grain: 1 row per product category, 5 rows)
3. product_movement.csv    (Grain: 1 row per catalog product, 35 rows)
4. inventory_snapshot.csv  (Grain: 1 row per store-SKU, 1,750 rows)
5. store_sales.csv         (Grain: 1 row per retail store, 50 rows)
6. recommendations.csv     (Grain: 1 row per active catalog product, 35 rows)

Usage:
    python scripts/export_reports.py
"""

import os
import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app import create_app
import db
from services import report_service

EXPORT_DIR = BASE_DIR / "exports" / "powerbi"

def safe_write(path, content):
    import time
    for attempt in range(5):
        try:
            path.write_text(content, encoding="utf-8")
            return
        except OSError:
            time.sleep(0.15)
    path.write_text(content, encoding="utf-8")

def export_all():
    print("=" * 68)
    print("STARTING ANALYTICAL DATASET EXPORT: NORMALIZED POWER BI CSV PIPELINE")
    print("=" * 68)

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Target Export Directory: {EXPORT_DIR}")

    app = create_app()
    with app.app_context():
        # 1. sales_daily.csv
        print("\n[1/6] Exporting Daily Sales Summary (sales_daily.csv)...")
        sales_rows = report_service.get_sales_daily_report()
        sales_fields = ["sale_date", "units_sold", "transaction_count", "calculated_revenue"]
        sales_csv = report_service.format_csv(sales_rows, sales_fields)
        sales_path = EXPORT_DIR / "sales_daily.csv"
        safe_write(sales_path, sales_csv)
        print(f"      Rows Exported: {len(sales_rows):,} | Path: {sales_path.name}")

        # 2. sales_category.csv
        print("[2/6] Exporting Category Sales Summary (sales_category.csv)...")
        cat_rows = report_service.get_sales_category_report()
        cat_fields = ["category", "units_sold", "transaction_count", "calculated_revenue", "average_units_per_transaction"]
        cat_csv = report_service.format_csv(cat_rows, cat_fields)
        cat_path = EXPORT_DIR / "sales_category.csv"
        safe_write(cat_path, cat_csv)
        print(f"      Rows Exported: {len(cat_rows):,} | Path: {cat_path.name}")

        # 3. product_movement.csv
        print("[3/6] Exporting Product Movement Classification (product_movement.csv)...")
        mov_rows = report_service.get_product_movement_report()
        mov_fields = [
            "product_id", "product_name", "category", "units_sold", "transactions",
            "sales_velocity", "movement_status", "current_stock", "reorder_level", "stock_coverage_days"
        ]
        mov_csv = report_service.format_csv(mov_rows, mov_fields)
        mov_path = EXPORT_DIR / "product_movement.csv"
        safe_write(mov_path, mov_csv)
        print(f"      Rows Exported: {len(mov_rows):,} | Path: {mov_path.name}")

        # 4. inventory_snapshot.csv
        print("[4/6] Exporting Current Store Inventory Snapshot (inventory_snapshot.csv)...")
        inv_rows = report_service.get_inventory_snapshot_report()
        inv_fields = [
            "inventory_id", "store_id", "store_name", "city", "product_id", "product_name",
            "category", "stock_on_hand", "reorder_level", "stock_status", "inventory_value"
        ]
        inv_csv = report_service.format_csv(inv_rows, inv_fields)
        inv_path = EXPORT_DIR / "inventory_snapshot.csv"
        safe_write(inv_path, inv_csv)
        print(f"      Rows Exported: {len(inv_rows):,} | Path: {inv_path.name}")

        # 5. store_sales.csv
        print("[5/6] Exporting Store Sales Performance (store_sales.csv)...")
        store_rows = report_service.get_store_sales_report()
        store_fields = ["store_id", "store_name", "city", "units_sold", "transaction_count", "calculated_revenue"]
        store_csv = report_service.format_csv(store_rows, store_fields)
        store_path = EXPORT_DIR / "store_sales.csv"
        safe_write(store_path, store_csv)
        print(f"      Rows Exported: {len(store_rows):,} | Path: {store_path.name}")

        # 6. recommendations.csv
        print("[6/6] Exporting Decision-Support Recommendations (recommendations.csv)...")
        rec_rows = report_service.get_recommendation_report()
        rec_fields = [
            "product_id", "product_name", "category", "movement_status", "current_stock",
            "reorder_level", "sales_velocity", "stock_coverage_days", "recommendation", "reason", "priority"
        ]
        rec_csv = report_service.format_csv(rec_rows, rec_fields)
        rec_path = EXPORT_DIR / "recommendations.csv"
        safe_write(rec_path, rec_csv)
        print(f"      Rows Exported: {len(rec_rows):,} | Path: {rec_path.name}")

        # 7. dim_date.csv (Star Schema Date Dimension)
        print("\n[7/9] Exporting Star Schema Date Dimension (dim_date.csv)...")
        import datetime
        start_date = datetime.date(2017, 1, 1)
        end_date = datetime.date(2018, 9, 30)
        delta = (end_date - start_date).days + 1
        date_rows = []
        for i in range(delta):
            d = start_date + datetime.timedelta(days=i)
            quarter = f"Q{(d.month - 1) // 3 + 1}"
            date_rows.append({
                "date": d.isoformat(),
                "year": d.year,
                "month_number": d.month,
                "month_name": d.strftime("%B"),
                "quarter": quarter,
                "year_month": d.strftime("%Y-%m"),
                "day": d.day,
                "day_of_week": d.strftime("%A")
            })
        date_fields = ["date", "year", "month_number", "month_name", "quarter", "year_month", "day", "day_of_week"]
        date_csv = report_service.format_csv(date_rows, date_fields)
        date_path = EXPORT_DIR / "dim_date.csv"
        safe_write(date_path, date_csv)
        print(f"      Rows Exported: {len(date_rows):,} | Path: {date_path.name}")

        # 8. dim_products.csv (Star Schema Product Dimension)
        print("[8/9] Exporting Star Schema Product Dimension (dim_products.csv)...")
        raw_prod = db.query_db("SELECT product_id, product_name, category, cost_price, selling_price FROM products ORDER BY product_id ASC;")
        prod_rows = [dict(r) for r in raw_prod]
        prod_fields = ["product_id", "product_name", "category", "cost_price", "selling_price"]
        prod_csv = report_service.format_csv(prod_rows, prod_fields)
        prod_path = EXPORT_DIR / "dim_products.csv"
        safe_write(prod_path, prod_csv)
        print(f"      Rows Exported: {len(prod_rows):,} | Path: {prod_path.name}")

        # 9. dim_stores.csv (Star Schema Store Dimension)
        print("[9/9] Exporting Star Schema Store Dimension (dim_stores.csv)...")
        raw_stores = db.query_db("SELECT store_id, store_name, city, location, open_date FROM stores ORDER BY store_id ASC;")
        store_dim_rows = [dict(r) for r in raw_stores]
        store_dim_fields = ["store_id", "store_name", "city", "location", "open_date"]
        store_dim_csv = report_service.format_csv(store_dim_rows, store_dim_fields)
        store_dim_path = EXPORT_DIR / "dim_stores.csv"
        safe_write(store_dim_path, store_dim_csv)
        print(f"      Rows Exported: {len(store_dim_rows):,} | Path: {store_dim_path.name}")

    print("\n" + "=" * 68)
    print("ALL POWER BI DATASETS EXPORTED SUCCESSFULLY!")
    print("=" * 68)
    print("Summary of Generated Datasets:")
    print(f"  * sales_daily.csv:        {len(sales_rows):>6,} rows | Size: {sales_path.stat().st_size:>8,} bytes")
    print(f"  * sales_category.csv:     {len(cat_rows):>6,} rows | Size: {cat_path.stat().st_size:>8,} bytes")
    print(f"  * product_movement.csv:   {len(mov_rows):>6,} rows | Size: {mov_path.stat().st_size:>8,} bytes")
    print(f"  * inventory_snapshot.csv: {len(inv_rows):>6,} rows | Size: {inv_path.stat().st_size:>8,} bytes")
    print(f"  * store_sales.csv:        {len(store_rows):>6,} rows | Size: {store_path.stat().st_size:>8,} bytes")
    print(f"  * recommendations.csv:    {len(rec_rows):>6,} rows | Size: {rec_path.stat().st_size:>8,} bytes")
    print(f"  * dim_date.csv:           {len(date_rows):>6,} rows | Size: {date_path.stat().st_size:>8,} bytes")
    print(f"  * dim_products.csv:       {len(prod_rows):>6,} rows | Size: {prod_path.stat().st_size:>8,} bytes")
    print(f"  * dim_stores.csv:         {len(store_dim_rows):>6,} rows | Size: {store_dim_path.stat().st_size:>8,} bytes")
    print("=" * 68)

if __name__ == "__main__":
    export_all()
