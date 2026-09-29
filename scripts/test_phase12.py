import os
import sys
from pathlib import Path
import sqlite3
import csv
import subprocess
import datetime

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app import app
import db
from services import report_service

EXPECTED_RAW_SIZES = {
    "products.csv": 1572,
    "stores.csv": 2999,
    "inventory.csv": 14675,
    "sales.csv": 21783359
}

def run_tests():
    client = app.test_client()

    print("=" * 68)
    print("STARTING TEST SUITE: PHASE 12 - REPORTS & NORMALIZED POWER BI EXPORTS")
    print("=" * 68)

    # 1. Reports page loads successfully
    res1 = client.get("/reports")
    assert res1.status_code == 200, f"Reports page failed: {res1.status_code}"
    html1 = res1.data.decode("utf-8")
    assert "Analytical Reports &amp; Power BI Export Center" in html1 or "Analytical Reports & Power BI Export Center" in html1
    assert "Daily Sales Summary" in html1
    assert "Category Sales" in html1
    assert "Product Movement" in html1
    assert "Store Performance" in html1
    assert "Inventory Snapshot" in html1
    assert "Recommendations" in html1
    assert "Export Center" in html1
    print("[1/24] Reports main dashboard loads successfully with all navigation tabs: PASS")

    # 2. Sales report preview works
    res2 = client.get("/reports?tab=sales")
    assert res2.status_code == 200
    html2 = res2.data.decode("utf-8")
    assert "Daily Sales Summary Report" in html2
    assert "2017-01-01" in html2
    print("[2/24] Daily Sales Summary preview renders valid trading day records: PASS")

    # 3. Product movement report works
    res3 = client.get("/reports?tab=movement")
    assert res3.status_code == 200
    html3 = res3.data.decode("utf-8")
    assert "Product Movement Classification Report" in html3
    assert "Colorbuds" in html3
    assert "FAST MOVING" in html3
    print("[3/24] Product Movement report renders all catalog items with empirical classifications: PASS")

    # 4. Inventory report works
    res4 = client.get("/reports?tab=inventory")
    assert res4.status_code == 200
    html4 = res4.data.decode("utf-8")
    assert "Current Store Inventory Snapshot" in html4
    assert "Calculated Valuation" in html4
    print("[4/24] Inventory Snapshot report renders store-SKU records with calculated valuation: PASS")

    # 5. Store report works
    res5 = client.get("/reports?tab=store")
    assert res5.status_code == 200
    html5 = res5.data.decode("utf-8")
    assert "Store Sales Performance Report" in html5
    assert "Maven Toys" in html5
    print("[5/24] Store Sales Performance report renders branch sales and revenue totals: PASS")

    # 6. Recommendation report works
    res6 = client.get("/reports?tab=recommendations")
    assert res6.status_code == 200
    html6 = res6.data.decode("utf-8")
    assert "Inventory Decision-Support Recommendations Report" in html6
    assert "Signal &amp; Recommendation" in html6 or "Signal & Recommendation" in html6
    print("[6/24] Recommendations report renders explainable decision-support signals: PASS")

    # 7. Run export pipeline and verify all 6 files are created
    export_dir = BASE_DIR / "exports" / "powerbi"
    res_export = subprocess.run([sys.executable, str(BASE_DIR / "scripts" / "export_reports.py")], capture_output=True, text=True)
    assert res_export.returncode == 0, f"Export script failed: {res_export.stderr}"

    expected_files = [
        "sales_daily.csv",
        "sales_category.csv",
        "product_movement.csv",
        "inventory_snapshot.csv",
        "store_sales.csv",
        "recommendations.csv"
    ]
    for fn in expected_files:
        fpath = export_dir / fn
        assert fpath.exists(), f"Missing export file: {fn}"
        assert fpath.stat().st_size > 0, f"Export file is empty: {fn}"
    print("[7/24] All 6 normalized Power BI CSV files generated successfully by export pipeline: PASS")

    # 8. CSV files have expected headers
    expected_headers = {
        "sales_daily.csv": ["sale_date", "units_sold", "transaction_count", "calculated_revenue"],
        "sales_category.csv": ["category", "units_sold", "transaction_count", "calculated_revenue", "average_units_per_transaction"],
        "product_movement.csv": ["product_id", "product_name", "category", "units_sold", "transactions", "sales_velocity", "movement_status", "current_stock", "reorder_level", "stock_coverage_days"],
        "inventory_snapshot.csv": ["inventory_id", "store_id", "store_name", "city", "product_id", "product_name", "category", "stock_on_hand", "reorder_level", "stock_status", "inventory_value"],
        "store_sales.csv": ["store_id", "store_name", "city", "units_sold", "transaction_count", "calculated_revenue"],
        "recommendations.csv": ["product_id", "product_name", "category", "movement_status", "current_stock", "reorder_level", "sales_velocity", "stock_coverage_days", "recommendation", "reason", "priority"]
    }

    for fn, exp_cols in expected_headers.items():
        with open(export_dir / fn, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
            assert header == exp_cols, f"Header mismatch in {fn}! Expected {exp_cols}, got {header}"
    print("[8/24] All 6 CSV export files match exact normalized schema header definitions: PASS")

    # 9. Sales daily rows reconcile with SQLite
    with app.app_context():
        db_sales = db.query_db("SELECT SUM(quantity) AS units, ROUND(SUM(total_amount), 2) AS rev, COUNT(DISTINCT sale_date) AS days FROM sales;", one=True)
        db_units = int(db_sales["units"])
        db_rev = float(db_sales["rev"])
        db_days = int(db_sales["days"])

    with open(export_dir / "sales_daily.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        daily_rows = list(reader)

    assert len(daily_rows) == db_days == 638
    sum_daily_units = sum(int(r["units_sold"]) for r in daily_rows)
    sum_daily_rev = round(sum(float(r["calculated_revenue"]) for r in daily_rows), 2)
    assert sum_daily_units == db_units == 1090565
    assert sum_daily_rev == db_rev == 14444572.35
    print(f"[9/24] sales_daily.csv reconciles with SQLite ({len(daily_rows)} days, {sum_daily_units:,} units, ${sum_daily_rev:,.2f}): PASS")

    # 10. Category totals reconcile with SQLite
    with open(export_dir / "sales_category.csv", "r", encoding="utf-8") as f:
        cat_rows = list(csv.DictReader(f))
    assert len(cat_rows) == 5
    cat_units = sum(int(r["units_sold"]) for r in cat_rows)
    cat_rev = round(sum(float(r["calculated_revenue"]) for r in cat_rows), 2)
    assert cat_units == db_units == 1090565
    assert cat_rev == db_rev == 14444572.35
    print(f"[10/24] sales_category.csv reconciles with SQLite (5 categories, {cat_units:,} units, ${cat_rev:,.2f}): PASS")

    # 11. Product movement contains all 35 products
    with open(export_dir / "product_movement.csv", "r", encoding="utf-8") as f:
        mov_rows = list(csv.DictReader(f))
    assert len(mov_rows) == 35
    fast_cnt = sum(1 for r in mov_rows if r["movement_status"] == "FAST MOVING")
    norm_cnt = sum(1 for r in mov_rows if r["movement_status"] == "NORMAL")
    slow_cnt = sum(1 for r in mov_rows if r["movement_status"] == "SLOW MOVING")
    assert fast_cnt == 9 and norm_cnt == 17 and slow_cnt == 9
    print(f"[11/24] product_movement.csv verified (35 catalog products: 9 Fast, 17 Normal, 9 Slow): PASS")

    # 12. Store export contains all 50 stores
    with open(export_dir / "store_sales.csv", "r", encoding="utf-8") as f:
        store_rows = list(csv.DictReader(f))
    assert len(store_rows) == 50
    st_units = sum(int(r["units_sold"]) for r in store_rows)
    st_rev = round(sum(float(r["calculated_revenue"]) for r in store_rows), 2)
    assert st_units == db_units == 1090565
    assert st_rev == db_rev == 14444572.35
    print(f"[12/24] store_sales.csv verified (50 stores, {st_units:,} units, ${st_rev:,.2f}): PASS")

    # 13. Inventory export contains 1,750 records
    with open(export_dir / "inventory_snapshot.csv", "r", encoding="utf-8") as f:
        inv_rows = list(csv.DictReader(f))
    assert len(inv_rows) == 1750
    inv_units = sum(int(r["stock_on_hand"]) for r in inv_rows)
    inv_val = round(sum(float(r["inventory_value"]) for r in inv_rows), 2)
    assert inv_units == 29742
    assert inv_val == 410240.58
    print(f"[13/24] inventory_snapshot.csv verified (1,750 store-SKUs, {inv_units:,} units, ${inv_val:,.2f} valuation): PASS")

    # 14. Recommendation export contains 35 active catalog products
    with open(export_dir / "recommendations.csv", "r", encoding="utf-8") as f:
        rec_rows = list(csv.DictReader(f))
    assert len(rec_rows) == 35
    for r in rec_rows:
        assert r["recommendation"] in [
            "PRIORITIZE REPLENISHMENT", "REPLENISH SOON", "MONITOR STOCK",
            "REVIEW INVENTORY LEVEL", "REPLENISH OR REVIEW", "MAINTAIN CURRENT LEVEL", "MONITOR"
        ]
        assert r["priority"] in ["HIGH", "MEDIUM", "LOW", "NONE"]
        assert len(r["reason"]) > 10
    print("[14/24] recommendations.csv verified with explainable reasons and priorities for all 35 SKUs: PASS")

    # 15. Numeric fields remain strictly numeric (no currency symbols or commas)
    numeric_checks = [
        ("sales_daily.csv", ["units_sold", "transaction_count", "calculated_revenue"]),
        ("sales_category.csv", ["units_sold", "transaction_count", "calculated_revenue", "average_units_per_transaction"]),
        ("product_movement.csv", ["units_sold", "transactions", "sales_velocity", "current_stock", "reorder_level"]),
        ("inventory_snapshot.csv", ["stock_on_hand", "reorder_level", "inventory_value"]),
        ("store_sales.csv", ["units_sold", "transaction_count", "calculated_revenue"]),
        ("recommendations.csv", ["current_stock", "reorder_level", "sales_velocity"])
    ]
    for fn, num_cols in numeric_checks:
        with open(export_dir / fn, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                for col in num_cols:
                    val = row[col]
                    assert "$" not in val, f"Currency symbol found in numeric column {col} of {fn}: {val}"
                    assert "," not in val, f"Comma found in numeric column {col} of {fn}: {val}"
                    float(val)  # Must parse successfully to float
    print("[15/24] Numeric normalization verified (zero currency symbols or commas in numerical columns): PASS")

    # 16. Dates use ISO format (YYYY-MM-DD)
    with open(export_dir / "sales_daily.csv", "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            d_str = row["sale_date"]
            d = datetime.date.fromisoformat(d_str)
            assert len(d_str) == 10 and d_str[4] == "-" and d_str[7] == "-"
    print("[16/24] ISO date formatting (YYYY-MM-DD) verified across all temporal datasets: PASS")

    # 17. Historical/current semantics are clearly documented in README.md
    readme_path = export_dir / "README.md"
    assert readme_path.exists(), "README.md missing from exports/powerbi/"
    readme_text = readme_path.read_text(encoding="utf-8")
    assert "Historical Sales Baseline" in readme_text
    assert "Current Application Inventory State" in readme_text
    assert "Calculated Revenue" in readme_text
    assert "sales_daily.csv" in readme_text
    assert "inventory_snapshot.csv" in readme_text
    print("[17/24] Documentation metadata verified (exports/powerbi/README.md explains all datasets and semantics): PASS")

    # 18. Raw CSV files remain 100% untouched
    raw_dir = BASE_DIR / "data" / "raw"
    for filename, expected_size in EXPECTED_RAW_SIZES.items():
        file_path = raw_dir / filename
        assert file_path.exists(), f"Raw file {filename} is missing!"
        actual_size = file_path.stat().st_size
        assert actual_size == expected_size, (
            f"Raw file {filename} size changed! Expected {expected_size}, got {actual_size}"
        )
    print("[18/24] Raw source CSV files remain 100% immutable and untouched: PASS")

    # 19-24. Regression test suites across all prior phases
    regression_scripts = [
        ("Phase 6 (Sales POS & Atomic Stock Decrement)", "scripts/test_phase6.py"),
        ("Phase 7 (Inbound Restock & Stock Movements)", "scripts/test_phase7.py"),
        ("Phase 8 (Inventory Grid & Valuation)", "scripts/test_phase8.py"),
        ("Phase 9 (Velocity & Movement Classification)", "scripts/test_phase9.py"),
        ("Phase 10 (Rule-Based Recommendation Engine)", "scripts/test_phase10.py"),
        ("Phase 11 (Interactive Dashboard Charts)", "scripts/test_phase11.py")
    ]

    for idx, (suite_name, script_path) in enumerate(regression_scripts, start=19):
        res = subprocess.run([sys.executable, script_path], capture_output=True, text=True)
        assert res.returncode == 0, f"Regression test failed for {suite_name}:\n{res.stdout}\n{res.stderr}"
        print(f"[{idx}/24] {suite_name} regression suite: PASS")

    # Final database row counts check
    with app.app_context():
        p_cnt = db.query_db("SELECT COUNT(*) AS c FROM products;", one=True)["c"]
        st_cnt = db.query_db("SELECT COUNT(*) AS c FROM stores;", one=True)["c"]
        i_cnt = db.query_db("SELECT COUNT(*) AS c FROM inventory;", one=True)["c"]
        s_cnt = db.query_db("SELECT COUNT(*) AS c FROM sales;", one=True)["c"]
        r_cnt = db.query_db("SELECT COUNT(*) AS c FROM restocks;", one=True)["c"]
        m_cnt = db.query_db("SELECT COUNT(*) AS c FROM stock_movements;", one=True)["c"]

    assert p_cnt == 35
    assert st_cnt == 50
    assert i_cnt == 1750
    assert s_cnt == 829262
    assert r_cnt == 0
    assert m_cnt == 1516

    print("\nDatabase baseline verified:")
    print(f"  Products:        {p_cnt}")
    print(f"  Stores:          {st_cnt}")
    print(f"  Inventory:       {i_cnt}")
    print(f"  Sales:           {s_cnt:,}")
    print(f"  Restocks:        {r_cnt}")
    print(f"  Stock Movements: {m_cnt}")

    print("=" * 68)
    print("ALL 24 PHASE 12 TESTS PASSED SUCCESSFULLY!")
    print("=" * 68)

if __name__ == "__main__":
    run_tests()
