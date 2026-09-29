import os
import sys
from pathlib import Path
import sqlite3
import re

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app import app

def run_tests():
    client = app.test_client()

    print("=" * 65)
    print("STARTING TEST SUITE: PHASE 8 - INVENTORY MANAGEMENT & STOCK STATUS")
    print("=" * 65)

    # 1. Inventory page loads
    res1 = client.get("/inventory")
    assert res1.status_code == 200, f"Failed on /inventory: {res1.status_code}"
    html1 = res1.data.decode("utf-8")
    assert "Store Inventory Management" in html1, "Header title missing"
    assert "Calculated Inventory Value" in html1, "Calculated Inventory Value missing"
    assert "Inventory Valuation at Catalog Selling Price" in html1, "Semantic valuation notice missing"
    print("[1/14] Inventory page loads successfully (HTTP 200): PASS")

    # 2. Inventory records display
    assert "Current Stock" in html1, "Current Stock column header missing"
    assert "Reorder Level" in html1, "Reorder Level column header missing"
    assert "Stock Value" in html1, "Stock Value column header missing"
    assert "Stock Status" in html1, "Stock Status column header missing"
    assert "Action Figure" in html1, "Sample product Action Figure missing from table"
    assert "Maven Toys" in html1, "Sample store Maven Toys missing from table"
    print("[2/14] Inventory records display with all required columns: PASS")

    # 3. Product filter works
    res3_name = client.get("/inventory?search=Action+Figure")
    assert res3_name.status_code == 200
    html3_name = res3_name.data.decode("utf-8")
    assert "Action Figure" in html3_name
    assert "50</strong> inventory records" in html3_name, "Expected 50 records for Action Figure across 50 stores"

    res3_id = client.get("/inventory?product_id=1")
    assert res3_id.status_code == 200
    html3_id = res3_id.data.decode("utf-8")
    assert "Action Figure" in html3_id
    assert "50</strong> inventory records" in html3_id
    print("[3/14] Product filter works (by name and ID): PASS")

    # 4. Store filter works
    res4 = client.get("/inventory?store_id=1")
    assert res4.status_code == 200
    html4 = res4.data.decode("utf-8")
    assert "Guadalajara 1" in html4
    assert "35</strong> inventory records" in html4, "Expected 35 product inventory records at Store 1"
    print("[4/14] Store filter works (shows exactly 35 records for store 1): PASS")

    # 5. Category filter works
    # Category 'Electronics' has 3 products (Colorbuds, Plug & Play Controllers, Dash Drone) -> 150 rows across 50 stores
    res5 = client.get("/inventory?category=Electronics&per_page=100")
    assert res5.status_code == 200
    html5 = res5.data.decode("utf-8")
    assert "150</strong> inventory records" in html5, "Expected 150 records for Electronics category"
    assert "Electronics" in html5
    print("[5/14] Category filter works (Electronics shows 150 store-SKU rows): PASS")

    # 6. Low-stock filter works
    res6 = client.get("/inventory?stock_status=low")
    assert res6.status_code == 200
    html6 = res6.data.decode("utf-8")
    assert "526</strong> inventory records" in html6, "Expected exactly 526 Low Stock records"
    assert "LOW STOCK" in html6
    print("[6/14] Low-stock filter works (returns exactly 526 low-stock items): PASS")

    # 7. Out-of-stock filter works
    res7 = client.get("/inventory?stock_status=out")
    assert res7.status_code == 200
    html7 = res7.data.decode("utf-8")
    assert "234</strong> inventory records" in html7, "Expected exactly 234 Out of Stock records"
    assert "OUT OF STOCK" in html7
    print("[7/14] Out-of-stock filter works (returns exactly 234 zero-stock items): PASS")

    # 8. Pagination works
    res8_p1 = client.get("/inventory?per_page=25&page=1")
    assert res8_p1.status_code == 200
    html8_p1 = res8_p1.data.decode("utf-8")
    assert "Showing <strong>1 &ndash; 25</strong> of <strong>1,750</strong>" in html8_p1, "Page 1 range mismatch"
    assert "Page <strong>1</strong> of <strong>70</strong>" in html8_p1

    res8_p2 = client.get("/inventory?per_page=25&page=2")
    assert res8_p2.status_code == 200
    html8_p2 = res8_p2.data.decode("utf-8")
    assert "Showing <strong>26 &ndash; 50</strong> of <strong>1,750</strong>" in html8_p2, "Page 2 range mismatch"
    assert "Page <strong>2</strong> of <strong>70</strong>" in html8_p2

    res8_p100 = client.get("/inventory?per_page=100&page=1")
    assert res8_p100.status_code == 200
    html8_p100 = res8_p100.data.decode("utf-8")
    assert "Showing <strong>1 &ndash; 100</strong> of <strong>1,750</strong>" in html8_p100, "100 per page range mismatch"
    print("[8/14] Server-side pagination works (25, 50, 100 per page & navigation): PASS")

    # 9. Inventory summary values are dynamic (queried from SQLite)
    conn = sqlite3.connect("database/inventory.db")
    c = conn.cursor()
    c.execute("""
        SELECT 
            COALESCE(SUM(i.stock_on_hand), 0) AS total_units,
            COUNT(CASE WHEN i.stock_on_hand = 0 THEN 1 END) AS out_of_stock,
            COUNT(CASE WHEN i.stock_on_hand > 0 AND i.stock_on_hand < i.reorder_level THEN 1 END) AS low_stock,
            COUNT(CASE WHEN i.stock_on_hand >= i.reorder_level THEN 1 END) AS normal_stock,
            COUNT(*) AS total_records,
            ROUND(COALESCE(SUM(i.stock_on_hand * p.selling_price), 0.0), 2) AS total_inventory_value
        FROM inventory i
        JOIN products p ON i.product_id = p.product_id;
    """)
    db_summary = c.fetchone()
    total_units_db, out_db, low_db, norm_db, recs_db, val_db = db_summary

    assert total_units_db == 29742
    assert out_db == 234
    assert low_db == 526
    assert norm_db == 990
    assert recs_db == 1750
    assert val_db == 410240.58

    # Verify these values appear on the page
    assert f"{total_units_db:,}" in html1, f"Expected {total_units_db:,} units in HTML"
    assert f"{out_db:,}" in html1, f"Expected {out_db:,} out of stock in HTML"
    assert f"{low_db:,}" in html1, f"Expected {low_db:,} low stock in HTML"
    assert f"{norm_db:,}" in html1, f"Expected {norm_db:,} normal stock in HTML"
    assert f"{recs_db:,}" in html1, f"Expected {recs_db:,} total records in HTML"
    print(f"[9/14] Dynamic summary values verified against SQLite ({total_units_db:,} units, {val_db:,.2f} value): PASS")

    # 10. Inventory value is calculated correctly
    assert "$410,240.58" in html1, "Calculated inventory value $410,240.58 missing from HTML"
    print("[10/14] Inventory value calculated correctly ($410,240.58 at catalog price): PASS")

    # 11. Product links work
    assert '/products/1' in html1, "Link to /products/1 missing from table"
    res11 = client.get("/products/1")
    assert res11.status_code == 200
    html11 = res11.data.decode("utf-8")
    assert "Action Figure" in html11
    print("[11/14] Product detail links work (/products/1 loads details): PASS")

    # 12. Restock links work with pre-selection
    res12 = client.get("/restock/add?product_id=1&store_id=1")
    assert res12.status_code == 200
    html12 = res12.data.decode("utf-8")
    assert 'value="1" ' in html12 and "selected" in html12
    assert "Record Inbound Restock" in html12
    print("[12/14] Restock link works with pre-selected product & store (/restock/add?product_id=1&store_id=1): PASS")

    # 13. Raw CSV files remain unchanged
    raw_inventory_size = Path("data/raw/inventory.csv").stat().st_size
    raw_products_size = Path("data/raw/products.csv").stat().st_size
    raw_sales_size = Path("data/raw/sales.csv").stat().st_size
    raw_stores_size = Path("data/raw/stores.csv").stat().st_size

    assert raw_inventory_size == 14675, f"raw inventory.csv modified! Size: {raw_inventory_size}"
    assert raw_products_size == 1572, f"raw products.csv modified! Size: {raw_products_size}"
    assert raw_sales_size == 21783359, f"raw sales.csv modified! Size: {raw_sales_size}"
    assert raw_stores_size == 2999, f"raw stores.csv modified! Size: {raw_stores_size}"
    print("[13/14] Raw source CSV files remain immutable and untouched: PASS")

    # 14. Database row counts verification
    c.execute("SELECT COUNT(*) FROM products;")
    products_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM stores;")
    stores_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM inventory;")
    inventory_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM sales;")
    sales_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM restocks;")
    restocks_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM stock_movements;")
    movements_count = c.fetchone()[0]

    assert products_count == 35, f"Expected 35 products, got {products_count}"
    assert stores_count == 50, f"Expected 50 stores, got {stores_count}"
    assert inventory_count == 1750, f"Expected 1,750 inventory records, got {inventory_count}"
    assert sales_count == 829262, f"Expected 829,262 sales, got {sales_count}"
    assert restocks_count == 0, f"Expected 0 restocks, got {restocks_count}"
    assert movements_count == 1516, f"Expected 1,516 stock movements, got {movements_count}"

    print(f"[14/14] Final database row counts verified:")
    print(f"        - Products:        {products_count:,}")
    print(f"        - Stores:          {stores_count:,}")
    print(f"        - Inventory:       {inventory_count:,}")
    print(f"        - Sales:           {sales_count:,}")
    print(f"        - Restocks:        {restocks_count:,}")
    print(f"        - Stock Movements: {movements_count:,}")
    print("=" * 65)
    print("ALL 14 PHASE 8 TESTS PASSED SUCCESSFULLY!")
    print("=" * 65)

    conn.close()

if __name__ == "__main__":
    run_tests()
