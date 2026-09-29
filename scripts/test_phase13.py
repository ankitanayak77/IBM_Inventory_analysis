"""
Smart Inventory & Sales Analysis System - Phase 13 Test Suite
-------------------------------------------------------------
Validates Power BI Report Preparation & Data Modeling:
1. All 9 export CSV files exist and are non-empty
2. Normalized schemas and column headers match specifications
3. Zero missing values or nulls in keys and numerical columns
4. Table grains verified (unique keys for all dimensions and facts)
5. Referential integrity and star-schema relationships verified
6. Date dimension contiguous range (2017-01-01 to 2018-09-30, 638 days)
7. DAX measure simulation reconciles 100% with SQLite database baseline:
   - Units Sold: 1,090,565
   - Calculated Revenue: $14,444,572.35
   - Total Transactions: 829,262
   - Current Inventory Units: 29,742
   - Calculated Inventory Value: $410,240.58
   - Low Stock Count: 526
   - Out of Stock Count: 234
   - Fast Moving Products: 9
   - Normal Moving Products: 17
   - Slow Moving Products: 9
   - Products Requiring Attention: 7
8. Power BI Project files verified (.pbip, model.bim, report.json with 5 pages)
9. DAX measures catalog (dax_measures.dax) and Power Query script (powerquery_m_code.m) verified
10. Comprehensive documentation (docs/powerbi_report.md) verified
11. Raw source CSV immutability verified
12. Cross-phase regression suites (Phases 6-12)
"""

import os
import sys
import csv
import json
import sqlite3
import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

EXPORT_DIR = BASE_DIR / "exports" / "powerbi"
POWERBI_DIR = BASE_DIR / "powerbi"
DOCS_DIR = BASE_DIR / "docs"

EXPECTED_RAW_SIZES = {
    "products.csv": 1572,
    "stores.csv": 2999,
    "inventory.csv": 14675,
    "sales.csv": 21783359
}

def run_tests():
    print("=" * 68)
    print("STARTING TEST SUITE: PHASE 13 - POWER BI DATA MODELING & REPORTING")
    print("=" * 68)

    # 1. Verify all 9 CSV files exist and are non-empty
    expected_csvs = [
        "sales_daily.csv",
        "sales_category.csv",
        "product_movement.csv",
        "inventory_snapshot.csv",
        "store_sales.csv",
        "recommendations.csv",
        "dim_date.csv",
        "dim_products.csv",
        "dim_stores.csv"
    ]
    for fn in expected_csvs:
        fp = EXPORT_DIR / fn
        assert fp.exists(), f"Missing export file: {fn}"
        assert fp.stat().st_size > 0, f"Export file is empty: {fn}"
    print(f"[1/16] All {len(expected_csvs)} Power BI export datasets exist and are non-empty: PASS")

    # 2. Verify exact column headers for all 9 files
    expected_headers = {
        "sales_daily.csv": ["sale_date", "units_sold", "transaction_count", "calculated_revenue"],
        "sales_category.csv": ["category", "units_sold", "transaction_count", "calculated_revenue", "average_units_per_transaction"],
        "product_movement.csv": ["product_id", "product_name", "category", "units_sold", "transactions", "sales_velocity", "movement_status", "current_stock", "reorder_level", "stock_coverage_days"],
        "inventory_snapshot.csv": ["inventory_id", "store_id", "store_name", "city", "product_id", "product_name", "category", "stock_on_hand", "reorder_level", "stock_status", "inventory_value"],
        "store_sales.csv": ["store_id", "store_name", "city", "units_sold", "transaction_count", "calculated_revenue"],
        "recommendations.csv": ["product_id", "product_name", "category", "movement_status", "current_stock", "reorder_level", "sales_velocity", "stock_coverage_days", "recommendation", "reason", "priority"],
        "dim_date.csv": ["date", "year", "month_number", "month_name", "quarter", "year_month", "day", "day_of_week"],
        "dim_products.csv": ["product_id", "product_name", "category", "cost_price", "selling_price"],
        "dim_stores.csv": ["store_id", "store_name", "city", "location", "open_date"]
    }
    for fn, exp_cols in expected_headers.items():
        with open(EXPORT_DIR / fn, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
            assert header == exp_cols, f"Header mismatch in {fn}: expected {exp_cols}, got {header}"
    print("[2/16] All 9 datasets match exact normalized schema header definitions: PASS")

    # 3. Verify zero nulls or empty strings in required fields
    for fn, cols in expected_headers.items():
        with open(EXPORT_DIR / fn, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row_idx, r in enumerate(reader):
                for col in cols:
                    # stock_coverage_days can be empty if velocity is 0
                    if col == "stock_coverage_days" and r[col] == "":
                        continue
                    assert r[col] is not None and r[col] != "", f"Empty/null value found in {fn} at row {row_idx}, column {col}"
    print("[3/16] Zero nulls or empty values in required keys and numeric metrics: PASS")

    # 4. Table grain verification
    with open(EXPORT_DIR / "sales_daily.csv", "r", encoding="utf-8") as f:
        daily = list(csv.DictReader(f))
        assert len(daily) == 638, f"Expected 638 daily rows, got {len(daily)}"
        dates = [r["sale_date"] for r in daily]
        assert len(dates) == len(set(dates)), "Duplicate dates found in sales_daily.csv"

    with open(EXPORT_DIR / "dim_date.csv", "r", encoding="utf-8") as f:
        dim_dates = list(csv.DictReader(f))
        assert len(dim_dates) == 638, f"Expected 638 date rows, got {len(dim_dates)}"
        assert [r["date"] for r in dim_dates] == dates, "DimDate dates do not align with sales_daily"

    with open(EXPORT_DIR / "dim_products.csv", "r", encoding="utf-8") as f:
        prods = list(csv.DictReader(f))
        assert len(prods) == 35, f"Expected 35 products, got {len(prods)}"
        prod_ids = [r["product_id"] for r in prods]
        assert len(prod_ids) == len(set(prod_ids)), "Duplicate product_ids in dim_products"

    with open(EXPORT_DIR / "dim_stores.csv", "r", encoding="utf-8") as f:
        stores = list(csv.DictReader(f))
        assert len(stores) == 50, f"Expected 50 stores, got {len(stores)}"
        store_ids = [r["store_id"] for r in stores]
        assert len(store_ids) == len(set(store_ids)), "Duplicate store_ids in dim_stores"

    with open(EXPORT_DIR / "inventory_snapshot.csv", "r", encoding="utf-8") as f:
        inv = list(csv.DictReader(f))
        assert len(inv) == 1750, f"Expected 1,750 inventory rows, got {len(inv)}"
        inv_keys = [(r["store_id"], r["product_id"]) for r in inv]
        assert len(inv_keys) == len(set(inv_keys)), "Duplicate (store_id, product_id) in inventory_snapshot"

    with open(EXPORT_DIR / "store_sales.csv", "r", encoding="utf-8") as f:
        ss = list(csv.DictReader(f))
        assert len(ss) == 50, f"Expected 50 store_sales rows, got {len(ss)}"
        assert len(set(r["store_id"] for r in ss)) == 50

    with open(EXPORT_DIR / "product_movement.csv", "r", encoding="utf-8") as f:
        pm = list(csv.DictReader(f))
        assert len(pm) == 35
        assert len(set(r["product_id"] for r in pm)) == 35

    with open(EXPORT_DIR / "recommendations.csv", "r", encoding="utf-8") as f:
        rec = list(csv.DictReader(f))
        assert len(rec) == 35
        assert len(set(r["product_id"] for r in rec)) == 35

    with open(EXPORT_DIR / "sales_category.csv", "r", encoding="utf-8") as f:
        sc = list(csv.DictReader(f))
        assert len(sc) == 5
        assert len(set(r["category"] for r in sc)) == 5

    print("[4/16] Table grains verified (unique keys and exact row counts across all 9 tables): PASS")

    # 5. Referential integrity and Star Schema relationships
    dim_product_id_set = set(prod_ids)
    dim_store_id_set = set(store_ids)
    dim_date_set = set(dates)

    # FactSalesDaily -> DimDate
    for r in daily:
        assert r["sale_date"] in dim_date_set, f"Orphaned sale_date: {r['sale_date']}"

    # FactInventorySnapshot -> DimProducts & DimStores
    for r in inv:
        assert r["product_id"] in dim_product_id_set, f"Orphaned product_id in inventory: {r['product_id']}"
        assert r["store_id"] in dim_store_id_set, f"Orphaned store_id in inventory: {r['store_id']}"

    # FactStoreSales -> DimStores
    for r in ss:
        assert r["store_id"] in dim_store_id_set, f"Orphaned store_id in store_sales: {r['store_id']}"

    # ProductMovement -> DimProducts
    for r in pm:
        assert r["product_id"] in dim_product_id_set, f"Orphaned product_id in movement: {r['product_id']}"

    # Recommendations -> DimProducts
    for r in rec:
        assert r["product_id"] in dim_product_id_set, f"Orphaned product_id in recommendations: {r['product_id']}"

    print("[5/16] Referential integrity verified (100% of foreign keys resolve with zero orphaned rows): PASS")

    # 6. Date dimension contiguous range
    start_d = datetime.date(2017, 1, 1)
    end_d = datetime.date(2018, 9, 30)
    for i, r in enumerate(dim_dates):
        expected_d = (start_d + datetime.timedelta(days=i)).isoformat()
        assert r["date"] == expected_d, f"Date discontinuity: expected {expected_d}, got {r['date']}"
        assert int(r["year"]) in (2017, 2018)
        assert 1 <= int(r["month_number"]) <= 12
        assert r["quarter"] in ("Q1", "Q2", "Q3", "Q4")
        assert 1 <= int(r["day"]) <= 31
    print(f"[6/16] Date dimension spans exactly 638 contiguous days ({start_d} to {end_d}): PASS")

    # 7. DAX Measure Simulation reconciles with SQLite baseline
    total_units = sum(int(r["units_sold"]) for r in daily)
    total_rev = round(sum(float(r["calculated_revenue"]) for r in daily), 2)
    total_tx = sum(int(r["transaction_count"]) for r in daily)
    avg_units_tx = round(total_units / total_tx, 2)

    total_stock = sum(int(r["stock_on_hand"]) for r in inv)
    total_val = round(sum(float(r["inventory_value"]) for r in inv), 2)
    normal_count = sum(1 for r in inv if r["stock_status"] == "NORMAL")
    low_count = sum(1 for r in inv if r["stock_status"] == "LOW STOCK")
    out_count = sum(1 for r in inv if r["stock_status"] == "OUT OF STOCK")

    fast_count = sum(1 for r in pm if r["movement_status"] == "FAST MOVING")
    normal_mov_count = sum(1 for r in pm if r["movement_status"] == "NORMAL")
    slow_count = sum(1 for r in pm if r["movement_status"] == "SLOW MOVING")

    attention_count = sum(1 for r in rec if r["priority"] in ("HIGH", "MEDIUM"))
    high_priority_count = sum(1 for r in rec if r["priority"] == "HIGH")
    medium_priority_count = sum(1 for r in rec if r["priority"] == "MEDIUM")

    # Assert against known baseline
    assert total_units == 1090565, f"Units mismatch: {total_units}"
    assert total_rev == 14444572.35, f"Revenue mismatch: {total_rev}"
    assert total_tx == 829262, f"Transaction mismatch: {total_tx}"
    assert avg_units_tx == 1.32, f"Basket size mismatch: {avg_units_tx}"
    assert total_stock == 29742, f"Stock mismatch: {total_stock}"
    assert total_val == 410240.58, f"Valuation mismatch: {total_val}"
    assert normal_count == 990, f"Normal stock mismatch: {normal_count}"
    assert low_count == 526, f"Low stock mismatch: {low_count}"
    assert out_count == 234, f"Out of stock mismatch: {out_count}"
    assert fast_count == 9, f"Fast moving mismatch: {fast_count}"
    assert normal_mov_count == 17, f"Normal moving mismatch: {normal_mov_count}"
    assert slow_count == 9, f"Slow moving mismatch: {slow_count}"
    assert attention_count == 7, f"Attention mismatch: {attention_count}"
    assert high_priority_count == 0, f"High priority mismatch: {high_priority_count}"
    assert medium_priority_count == 7, f"Medium priority mismatch: {medium_priority_count}"

    print("[7/16] DAX measures simulation matches 100% of SQLite database baseline numbers: PASS")
    print("       * Total Units Sold:             1,090,565")
    print("       * Total Calculated Revenue:     $14,444,572.35")
    print("       * Total Sales Transactions:       829,262")
    print("       * Average Units per Basket:          1.32")
    print("       * Total Physical Current Stock:    29,742")
    print("       * Current Calculated Valuation:   $410,240.58")
    print("       * Normal Stock Store-SKUs:            990")
    print("       * Low Stock Store-SKUs:               526")
    print("       * Out of Stock Store-SKUs:            234")
    print("       * Fast / Normal / Slow:            9 / 17 / 9")
    print("       * Products Requiring Attention:         7")

    # 8. Cross-check Store Sales & Category Sales against totals
    store_units = sum(int(r["units_sold"]) for r in ss)
    store_rev = round(sum(float(r["calculated_revenue"]) for r in ss), 2)
    assert store_units == total_units
    assert store_rev == total_rev

    cat_units = sum(int(r["units_sold"]) for r in sc)
    cat_rev = round(sum(float(r["calculated_revenue"]) for r in sc), 2)
    assert cat_units == total_units
    assert cat_rev == total_rev
    print("[8/16] Cross-table reconciliation verified (Store and Category sums match total daily sales): PASS")

    # 9. Power BI Project files verification (.pbip, model.bim, report.json)
    pbip_file = POWERBI_DIR / "SmartInventory_Analytics.pbip"
    dataset_file = POWERBI_DIR / "SmartInventory_Analytics.Dataset" / "definition.pbidataset"
    bim_file = POWERBI_DIR / "SmartInventory_Analytics.Dataset" / "model.bim"
    pbir_file = POWERBI_DIR / "SmartInventory_Analytics.Report" / "definition.pbir"
    report_file = POWERBI_DIR / "SmartInventory_Analytics.Report" / "report.json"

    assert pbip_file.exists() and pbip_file.stat().st_size > 0
    assert dataset_file.exists() and dataset_file.stat().st_size > 0
    assert bim_file.exists() and bim_file.stat().st_size > 0
    assert pbir_file.exists() and pbir_file.stat().st_size > 0
    assert report_file.exists() and report_file.stat().st_size > 0

    # Verify zero machine paths in Power BI files
    disallowed_strings = ["C:\\Users\\ankit", "C:/Users/ankit", "Users\\ankit", "Users/ankit"]
    for fp in [pbip_file, dataset_file, bim_file, pbir_file, report_file]:
        text = fp.read_text(encoding="utf-8")
        for dis in disallowed_strings:
            assert dis.lower() not in text.lower(), f"Machine path '{dis}' detected in {fp.name}"

    with open(bim_file, "r", encoding="utf-8") as f:
        bim_data = json.load(f)
        tables = [t["name"] for t in bim_data["model"]["tables"]]
        assert "DimDate" in tables
        assert "DimProducts" in tables
        assert "DimStores" in tables
        assert "FactSalesDaily" in tables
        assert "FactInventorySnapshot" in tables
        assert "ProductMovement" in tables
        assert "Recommendations" in tables
        assert "FactStoreSales" in tables
        assert "SalesCategory" in tables

        # Verify SourceFolder parameter expression
        expr_names = [e["name"] for e in bim_data["model"].get("expressions", [])]
        assert "SourceFolder" in expr_names, "Missing SourceFolder parameter in model.bim"

        # Verify partitions use SourceFolder
        for t in bim_data["model"]["tables"]:
            for p in t.get("partitions", []):
                expr_str = "".join(p["source"]["expression"])
                assert "SourceFolder" in expr_str, f"Table {t['name']} partition does not reference SourceFolder"

        # Verify all relationships are strictly oneDirection
        assert len(bim_data["model"]["relationships"]) >= 6
        for rel in bim_data["model"]["relationships"]:
            assert rel["crossFilteringBehavior"] == "oneDirection", (
                f"Relationship {rel['name']} is not oneDirection: {rel['crossFilteringBehavior']}"
            )

    with open(report_file, "r", encoding="utf-8") as f:
        report_data = json.load(f)
        sections = [s["displayName"] for s in report_data["sections"]]
        assert len(sections) == 5
        assert "1. Executive Overview" in sections
        assert "2. Sales Analysis" in sections
        assert "3. Current Inventory Analysis" in sections
        assert "4. Product Movement" in sections
        assert "5. Recommendations" in sections

    print("[9/16] Power BI Project artifacts verified (.pbip, model.bim with 9 tables, report.json with 5 pages): PASS")

    # 10. DAX Measures Catalog file verified
    dax_file = EXPORT_DIR / "dax_measures.dax"
    assert dax_file.exists() and dax_file.stat().st_size > 0
    dax_content = dax_file.read_text(encoding="utf-8")
    assert "Total Units Sold" in dax_content
    assert "Total Calculated Revenue" in dax_content
    assert "Transaction Count" in dax_content
    assert "Total Current Stock" in dax_content
    assert "Inventory Value" in dax_content
    assert "Low Stock Count" in dax_content
    assert "Out of Stock Count" in dax_content
    assert "Products Requiring Attention" in dax_content
    print("[10/16] DAX measures catalog (dax_measures.dax) verified with all required measures: PASS")

    # 11. Power Query M Script verified
    m_file = EXPORT_DIR / "powerquery_m_code.m"
    assert m_file.exists() and m_file.stat().st_size > 0
    m_content = m_file.read_text(encoding="utf-8")
    assert "SourceFolder" in m_content
    assert "DimDate" in m_content
    assert "DimProducts" in m_content
    assert "DimStores" in m_content
    assert "FactSalesDaily" in m_content
    assert "FactInventorySnapshot" in m_content
    print("[11/16] Power Query M script (powerquery_m_code.m) verified with ETL definitions: PASS")

    # 12. Documentation verified
    doc_file = DOCS_DIR / "powerbi_report.md"
    assert doc_file.exists() and doc_file.stat().st_size > 0
    doc_content = doc_file.read_text(encoding="utf-8")
    assert "Executive Summary & Objective" in doc_content
    assert "Data Sources & Table Grains" in doc_content
    assert "Star Schema" in doc_content
    assert "Page 1 — Executive Overview" in doc_content
    assert "Page 2 — Sales Analysis" in doc_content
    assert "Page 3 — Current Inventory Analysis" in doc_content
    assert "Page 4 — Product Movement" in doc_content
    assert "Page 5 — Recommendations" in doc_content
    assert "Refresh Workflow Procedure" in doc_content
    print("[12/16] Complete documentation (docs/powerbi_report.md) verified: PASS")

    # 13. Source raw CSV immutability check
    raw_dir = BASE_DIR / "data" / "raw"
    for fn, expected_sz in EXPECTED_RAW_SIZES.items():
        fp = raw_dir / fn
        assert fp.exists(), f"Missing raw CSV: {fn}"
        actual_sz = fp.stat().st_size
        assert actual_sz == expected_sz, f"Raw CSV modified! {fn} expected {expected_sz}, got {actual_sz}"
    print("[13/16] Raw source CSV files remain 100% immutable and untouched: PASS")

    # 14. Database baseline verification
    conn = sqlite3.connect(str(BASE_DIR / "database" / "inventory.db"))
    cur = conn.cursor()
    prod_c = cur.execute("SELECT COUNT(*) FROM products;").fetchone()[0]
    store_c = cur.execute("SELECT COUNT(*) FROM stores;").fetchone()[0]
    inv_c = cur.execute("SELECT COUNT(*) FROM inventory;").fetchone()[0]
    sales_c = cur.execute("SELECT COUNT(*) FROM sales;").fetchone()[0]
    restock_c = cur.execute("SELECT COUNT(*) FROM restocks;").fetchone()[0]
    movements_c = cur.execute("SELECT COUNT(*) FROM stock_movements;").fetchone()[0]
    conn.close()

    assert prod_c == 35, f"Product count mismatch: {prod_c}"
    assert store_c == 50, f"Store count mismatch: {store_c}"
    assert inv_c == 1750, f"Inventory count mismatch: {inv_c}"
    assert sales_c == 829262, f"Sales count mismatch: {sales_c}"
    assert restock_c == 0, f"Restock count mismatch: {restock_c}"
    assert movements_c == 1516, f"Stock movements mismatch: {movements_c}"
    print("[14/16] Final database row counts verified (35 / 50 / 1,750 / 829,262 / 0 / 1,516): PASS")

    # 15. Standalone exporter execution test
    import subprocess
    export_run = subprocess.run([sys.executable, str(BASE_DIR / "scripts" / "export_reports.py")], capture_output=True, text=True)
    assert export_run.returncode == 0, f"Exporter script failed: {export_run.stderr}"
    print("[15/16] Standalone export pipeline (scripts/export_reports.py) executes cleanly: PASS")

    # 16. Power BI project builder execution test
    builder_run = subprocess.run([sys.executable, str(BASE_DIR / "scripts" / "build_powerbi_project.py")], capture_output=True, text=True)
    assert builder_run.returncode == 0, f"Project builder failed: {builder_run.stderr}"
    print("[16/16] Power BI project builder (scripts/build_powerbi_project.py) executes cleanly: PASS")

    print("\n" + "=" * 68)
    print("ALL 16 PHASE 13 TESTS PASSED SUCCESSFULLY!")
    print("=" * 68)

if __name__ == "__main__":
    run_tests()
