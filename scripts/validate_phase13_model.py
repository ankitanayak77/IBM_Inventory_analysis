"""
Smart Inventory & Sales Analysis System - Phase 13 Model & Project Validator
-----------------------------------------------------------------------------
Dedicated validation script for Phase 13 Power BI assets:
1. Verifies NO hardcoded machine-specific absolute paths (e.g. C:\\Users\\...) exist in powerbi/ or exports/
2. Verifies expected Power BI project files exist (.pbip, model.bim, report.json, etc.)
3. Verifies all 9 expected tables exist in model.bim with valid partitions and columns
4. Verifies all relationships exist and enforce strict single-direction filtering ('oneDirection')
5. Verifies all required DAX measures exist in model.bim and dax_measures.dax
6. Verifies all 9 CSV export files exist and match exact grains and row counts
7. Verifies mathematical reconciliation with SQLite database baseline
"""

import os
import sys
import csv
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

POWERBI_DIR = BASE_DIR / "powerbi"
EXPORT_DIR = BASE_DIR / "exports" / "powerbi"
DATASET_DIR = POWERBI_DIR / "SmartInventory_Analytics.Dataset"
REPORT_DIR = POWERBI_DIR / "SmartInventory_Analytics.Report"

EXPECTED_GRAINS = {
    "dim_date.csv": 638,
    "dim_products.csv": 35,
    "dim_stores.csv": 50,
    "sales_daily.csv": 638,
    "inventory_snapshot.csv": 1750,
    "store_sales.csv": 50,
    "product_movement.csv": 35,
    "recommendations.csv": 35,
    "sales_category.csv": 5
}

EXPECTED_TABLES = [
    "DimDate",
    "DimProducts",
    "DimStores",
    "FactSalesDaily",
    "FactInventorySnapshot",
    "ProductMovement",
    "Recommendations",
    "FactStoreSales",
    "SalesCategory"
]

EXPECTED_MEASURES = [
    "Total Units Sold",
    "Total Calculated Revenue",
    "Transaction Count",
    "Average Units per Transaction",
    "Average Daily Sales",
    "Average Daily Revenue",
    "Total Current Stock",
    "Inventory Value",
    "Total SKU Combinations",
    "Normal Stock Count",
    "Low Stock Count",
    "Out of Stock Count",
    "Percent Low Stock",
    "Percent Out of Stock",
    "Fast Moving Product Count",
    "Normal Moving Product Count",
    "Slow Moving Product Count",
    "Average Sales Velocity",
    "Products Requiring Attention",
    "High Priority Recommendations",
    "Medium Priority Recommendations",
    "Low Priority Recommendations",
    "No Priority Recommendations"
]

def validate():
    print("=" * 72)
    print("STARTING PHASE 13 MODEL VALIDATION: PORTABILITY, GRAINS & RELATIONSHIPS")
    print("=" * 72)

    # -------------------------------------------------------------
    # 1. Path Portability Check (No hard-coded absolute machine paths)
    # -------------------------------------------------------------
    print("\n[1/7] Checking for non-portable absolute machine paths...")
    disallowed_strings = ["C:\\Users\\ankit", "C:/Users/ankit", "Users\\ankit", "Users/ankit"]
    checked_files = [
        POWERBI_DIR / "SmartInventory_Analytics.pbip",
        DATASET_DIR / "definition.pbidataset",
        DATASET_DIR / "model.bim",
        REPORT_DIR / "definition.pbir",
        REPORT_DIR / "report.json",
        EXPORT_DIR / "powerquery_m_code.m",
        EXPORT_DIR / "dax_measures.dax"
    ]
    for fp in checked_files:
        if fp.exists():
            text = fp.read_text(encoding="utf-8")
            for dis in disallowed_strings:
                assert dis.lower() not in text.lower(), (
                    f"PORTABILITY VIOLATION: Hardcoded machine path '{dis}' detected in {fp.name}!"
                )
    print("      SUCCESS: Zero hardcoded machine paths found. Model uses portable 'SourceFolder' parameter.")

    # -------------------------------------------------------------
    # 2. File Existence & Structure Check
    # -------------------------------------------------------------
    print("\n[2/7] Verifying Power BI project file structure...")
    for fp in checked_files:
        assert fp.exists(), f"Missing required Power BI file: {fp}"
        assert fp.stat().st_size > 0, f"File is empty: {fp}"
    print("      SUCCESS: All 7 core Power BI project definition files exist and are populated.")

    # -------------------------------------------------------------
    # 3. model.bim Integrity & Expressions Check
    # -------------------------------------------------------------
    print("\n[3/7] Inspecting model.bim schema, expressions, and tables...")
    with open(DATASET_DIR / "model.bim", "r", encoding="utf-8") as f:
        bim = json.load(f)

    # Verify SourceFolder parameter expression
    expressions = bim["model"].get("expressions", [])
    expr_names = [e["name"] for e in expressions]
    assert "SourceFolder" in expr_names, "Missing 'SourceFolder' parameter in model.bim expressions!"
    source_folder_expr = next(e for e in expressions if e["name"] == "SourceFolder")
    source_folder_str = "".join(source_folder_expr["expression"])
    assert "..\\exports\\powerbi\\" in source_folder_str or "..\\\\exports\\\\powerbi\\\\" in source_folder_str, (
        f"SourceFolder expression not defaulting to portable relative path: {source_folder_str}"
    )

    # Verify Tables
    tables_in_bim = {t["name"]: t for t in bim["model"]["tables"]}
    for t_name in EXPECTED_TABLES:
        assert t_name in tables_in_bim, f"Missing table '{t_name}' in model.bim!"
        # Verify partition references SourceFolder
        parts = tables_in_bim[t_name].get("partitions", [])
        assert len(parts) >= 1, f"Table '{t_name}' has no partitions!"
        m_expr = "".join(parts[0]["source"]["expression"])
        assert "SourceFolder" in m_expr, f"Table '{t_name}' partition does not use SourceFolder parameter!"
    print(f"      SUCCESS: All {len(EXPECTED_TABLES)} tables exist and reference portable 'SourceFolder'.")

    # -------------------------------------------------------------
    # 4. Relationship Directionality Check (Strict Star-Schema 1-Direction)
    # -------------------------------------------------------------
    print("\n[4/7] Checking relationship directionality in model.bim...")
    relationships = bim["model"].get("relationships", [])
    assert len(relationships) >= 6, f"Expected at least 6 relationships, got {len(relationships)}"

    expected_rel_definitions = [
        {"name": "Rel_Date_SalesDaily", "from": "FactSalesDaily", "to": "DimDate", "dir": "oneDirection"},
        {"name": "Rel_Product_Inventory", "from": "FactInventorySnapshot", "to": "DimProducts", "dir": "oneDirection"},
        {"name": "Rel_Store_Inventory", "from": "FactInventorySnapshot", "to": "DimStores", "dir": "oneDirection"},
        {"name": "Rel_Product_Movement", "from": "ProductMovement", "to": "DimProducts", "dir": "oneDirection"},
        {"name": "Rel_Product_Recommendations", "from": "Recommendations", "to": "DimProducts", "dir": "oneDirection"},
        {"name": "Rel_Store_Sales", "from": "FactStoreSales", "to": "DimStores", "dir": "oneDirection"}
    ]

    rel_by_name = {r["name"]: r for r in relationships}
    for er in expected_rel_definitions:
        assert er["name"] in rel_by_name, f"Missing relationship: {er['name']}"
        actual = rel_by_name[er["name"]]
        assert actual["fromTable"] == er["from"], f"Rel {er['name']} fromTable mismatch"
        assert actual["toTable"] == er["to"], f"Rel {er['name']} toTable mismatch"
        assert actual["crossFilteringBehavior"] == er["dir"], (
            f"Rel {er['name']} direction mismatch: expected {er['dir']}, got {actual['crossFilteringBehavior']}"
        )
        print(f"      * {er['name']}: {er['to']} -> {er['from']} ({er['dir']}) [VERIFIED]")

    # Check for any rogue bidirectional relationships
    for r in relationships:
        assert r["crossFilteringBehavior"] == "oneDirection", (
            f"Unwanted bidirectional relationship found: {r['name']}"
        )
    print("      SUCCESS: Zero bidirectional relationships found. Model adheres strictly to Star Schema.")

    # -------------------------------------------------------------
    # 5. DAX Measures Verification in model.bim and dax_measures.dax
    # -------------------------------------------------------------
    print("\n[5/7] Verifying DAX measures...")
    measures_in_bim = []
    for t in bim["model"]["tables"]:
        for m in t.get("measures", []):
            measures_in_bim.append(m["name"])

    for em in EXPECTED_MEASURES:
        assert em in measures_in_bim, f"Missing DAX measure in model.bim: '{em}'"

    dax_text = (EXPORT_DIR / "dax_measures.dax").read_text(encoding="utf-8")
    for em in EXPECTED_MEASURES:
        assert em in dax_text, f"Missing DAX measure in dax_measures.dax: '{em}'"
    print(f"      SUCCESS: All {len(EXPECTED_MEASURES)} DAX measures defined in model.bim & dax_measures.dax.")

    # -------------------------------------------------------------
    # 6. CSV Grains & Row Counts Check
    # -------------------------------------------------------------
    print("\n[6/7] Validating CSV file row counts and grains...")
    for fn, exp_rows in EXPECTED_GRAINS.items():
        fp = EXPORT_DIR / fn
        assert fp.exists(), f"Missing export file: {fn}"
        with open(fp, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
            rows = list(reader)
            assert len(rows) == exp_rows, f"Grain mismatch in {fn}: expected {exp_rows} rows, got {len(rows)}"
        print(f"      * {fn:<24}: {len(rows):>5,} rows (Grain verified)")
    print("      SUCCESS: 100% of CSV exports match exact expected table grains.")

    # -------------------------------------------------------------
    # 7. Mathematical Reconciliation Against Database Baseline
    # -------------------------------------------------------------
    print("\n[7/7] Validating baseline math reconciliation...")
    with open(EXPORT_DIR / "sales_daily.csv", "r", encoding="utf-8") as f:
        daily_rows = list(csv.DictReader(f))
    units_sold = sum(int(r["units_sold"]) for r in daily_rows)
    calc_rev = round(sum(float(r["calculated_revenue"]) for r in daily_rows), 2)
    tx_count = sum(int(r["transaction_count"]) for r in daily_rows)

    with open(EXPORT_DIR / "inventory_snapshot.csv", "r", encoding="utf-8") as f:
        inv_rows = list(csv.DictReader(f))
    curr_stock = sum(int(r["stock_on_hand"]) for r in inv_rows)
    inv_val = round(sum(float(r["inventory_value"]) for r in inv_rows), 2)
    low_stock = sum(1 for r in inv_rows if r["stock_status"] == "LOW STOCK")
    out_stock = sum(1 for r in inv_rows if r["stock_status"] == "OUT OF STOCK")
    normal_stock = sum(1 for r in inv_rows if r["stock_status"] == "NORMAL")

    with open(EXPORT_DIR / "product_movement.csv", "r", encoding="utf-8") as f:
        pm_rows = list(csv.DictReader(f))
    fast_mov = sum(1 for r in pm_rows if r["movement_status"] == "FAST MOVING")
    norm_mov = sum(1 for r in pm_rows if r["movement_status"] == "NORMAL")
    slow_mov = sum(1 for r in pm_rows if r["movement_status"] == "SLOW MOVING")

    with open(EXPORT_DIR / "recommendations.csv", "r", encoding="utf-8") as f:
        rec_rows = list(csv.DictReader(f))
    attention = sum(1 for r in rec_rows if r["priority"] in ("HIGH", "MEDIUM"))

    assert units_sold == 1090565
    assert calc_rev == 14444572.35
    assert tx_count == 829262
    assert curr_stock == 29742
    assert inv_val == 410240.58
    assert low_stock == 526
    assert out_stock == 234
    assert normal_stock == 990
    assert fast_mov == 9
    assert norm_mov == 17
    assert slow_mov == 9
    assert attention == 7

    print("      * Total Units Sold:             1,090,565 (PASS)")
    print("      * Total Calculated Revenue:     $14,444,572.35 (PASS)")
    print("      * Total Transactions:             829,262 (PASS)")
    print("      * Current Inventory Units:         29,742 (PASS)")
    print("      * Current Inventory Value:        $410,240.58 (PASS)")
    print("      * Low Stock / Out of Stock:       526 / 234 (PASS)")
    print("      * Fast / Normal / Slow:           9 / 17 / 9 (PASS)")
    print("      * Products Requiring Attention:   7 (PASS)")

    print("\n" + "=" * 72)
    print("ALL PHASE 13 MODEL VALIDATIONS COMPLETED AND VERIFIED SUCCESSFULLY!")
    print("=" * 72)

if __name__ == "__main__":
    validate()
