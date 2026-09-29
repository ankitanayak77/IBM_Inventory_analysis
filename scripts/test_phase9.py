import os
import sys
from pathlib import Path
import sqlite3
import json

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app import app
from services import analytics_service

def run_tests():
    client = app.test_client()

    print("=" * 65)
    print("STARTING TEST SUITE: PHASE 9 - FAST/SLOW PRODUCT ANALYTICS")
    print("=" * 65)

    # 1. Analytics page loads
    res1 = client.get("/analytics")
    assert res1.status_code == 200, f"Failed on /analytics: {res1.status_code}"
    html1 = res1.data.decode("utf-8")
    assert "Product Movement Analytics &amp; Sales Velocity" in html1 or "Product Movement Analytics & Sales Velocity" in html1
    assert "Relative Percentile-Based Classification Methodology" in html1
    assert "Historical sales baseline" in html1
    print("[1/15] Analytics page loads successfully (HTTP 200): PASS")

    # 2. Historical default period works
    assert "2017-01-01" in html1, "Default start date 2017-01-01 missing"
    assert "2018-09-30" in html1, "Default end date 2018-09-30 missing"
    assert "638 days" in html1, "638 day baseline count missing"
    assert "1,090,565" in html1, "Total baseline units 1,090,565 missing"
    print("[2/15] Historical default period (2017-01-01 to 2018-09-30, 638 days) works: PASS")

    # 3. Custom date range works
    res3 = client.get("/analytics?start_date=2018-01-01&end_date=2018-06-30&preset=custom")
    assert res3.status_code == 200
    html3 = res3.data.decode("utf-8")
    assert "181 days" in html3, "Custom 181-day period mismatch"
    assert "2018-01-01" in html3 and "2018-06-30" in html3
    print("[3/14] Custom date range (2018-01-01 to 2018-06-30, 181 days) works: PASS")

    # 4. Product velocity calculations are correct
    # In 638 days:
    # Colorbuds: 104,368 units -> 104368 / 638 = 163.59 units/day
    # PlayDoh Can: 103,128 units -> 103128 / 638 = 161.64 units/day
    # Mini Basketball Hoop: 2,647 units -> 2647 / 638 = 4.15 units/day
    with app.app_context():
        vel_data = analytics_service.get_product_velocity("2017-01-01", "2018-09-30")
        prods = {p["product_name"]: p for p in vel_data["products"]}
        
        assert "Colorbuds" in prods
        cb = prods["Colorbuds"]
        assert cb["total_units_sold"] == 104368
        assert cb["sales_velocity"] == 163.59
        assert cb["movement_status"] == "FAST MOVING"

        assert "PlayDoh Can" in prods
        pd = prods["PlayDoh Can"]
        assert pd["total_units_sold"] == 103128
        assert pd["sales_velocity"] == 161.64
        assert pd["movement_status"] == "FAST MOVING"

        assert "Mini Basketball Hoop" in prods
        mbh = prods["Mini Basketball Hoop"]
        assert mbh["total_units_sold"] == 2647
        assert mbh["sales_velocity"] == 4.15
        assert mbh["movement_status"] == "SLOW MOVING"

    print("[4/15] Product velocity calculations verified (Colorbuds: 163.59/d, PlayDoh: 161.64/d, Hoop: 4.15/d): PASS")

    # 5. Total units and revenue reconcile with SQL
    conn = sqlite3.connect("database/inventory.db")
    c = conn.cursor()
    c.execute("SELECT SUM(quantity), ROUND(SUM(total_amount), 2), COUNT(*) FROM sales;")
    sql_units, sql_rev, sql_txs = c.fetchone()
    
    assert vel_data["summary"]["total_units_sold"] == sql_units == 1090565
    assert vel_data["summary"]["total_revenue"] == sql_rev == 14444572.35
    assert vel_data["summary"]["total_transactions"] == sql_txs == 829262
    print(f"[5/15] Total units ({sql_units:,}) and revenue (${sql_rev:,.2f}) reconcile with SQLite: PASS")

    # 6. Product movement categories generated dynamically
    # With 35 products and 75th/25th percentiles: 9 Fast, 17 Normal, 9 Slow
    sum_data = vel_data["summary"]
    assert sum_data["fast_moving_count"] == 9, f"Expected 9 fast moving, got {sum_data['fast_moving_count']}"
    assert sum_data["normal_moving_count"] == 17, f"Expected 17 normal moving, got {sum_data['normal_moving_count']}"
    assert sum_data["slow_moving_count"] == 9, f"Expected 9 slow moving, got {sum_data['slow_moving_count']}"
    assert sum_data["total_products_analyzed"] == 35
    print(f"[6/15] Dynamic percentile movement counts verified (Fast: 9, Normal: 17, Slow: 9): PASS")

    # 7. Fast-moving filter works
    res7 = client.get("/analytics?movement=fast")
    assert res7.status_code == 200
    html7 = res7.data.decode("utf-8")
    assert "Showing <strong>9</strong> of <strong>35</strong> products" in html7
    assert "FAST MOVING" in html7
    print("[7/15] Fast-moving filter returns only top 9 high-velocity products: PASS")

    # 8. Slow-moving filter works
    res8 = client.get("/analytics?movement=slow")
    assert res8.status_code == 200
    html8 = res8.data.decode("utf-8")
    assert "Showing <strong>9</strong> of <strong>35</strong> products" in html8
    assert "SLOW MOVING" in html8
    print("[8/15] Slow-moving filter returns only bottom 9 low-velocity products: PASS")

    # 9. Category summary works
    with app.app_context():
        cats = analytics_service.get_category_analysis(vel_data["products"])
        assert len(cats) == 5, f"Expected 5 categories, got {len(cats)}"
        cat_units = sum(c["total_units_sold"] for c in cats)
        assert cat_units == 1090565, f"Expected 1,090,565 category units, got {cat_units}"
        
        cat_names = [c["category"] for c in cats]
        assert "Art & Crafts" in cat_names
        assert "Toys" in cat_names
        assert "Electronics" in cat_names
        assert "Games" in cat_names
        assert "Sports & Outdoors" in cat_names

    print("[9/15] Category summary verified (5 categories, units reconcile to 1,090,565): PASS")

    # 10. Store summary works
    with app.app_context():
        stores = analytics_service.get_store_sales_summary("2017-01-01", "2018-09-30", limit=10)
        assert len(stores) == 10
        top_store = stores[0]
        assert top_store["store_name"] == "Maven Toys Ciudad de Mexico 2"
        assert top_store["units_sold"] == 42757
    print("[10/15] Store sales summary verified (Top store: Maven Toys Ciudad de Mexico 2 with 42,757 units): PASS")

    # 11. Current inventory is joined correctly
    # Check that each product has positive or zero network stock
    for p in vel_data["products"]:
        assert "current_stock" in p
        assert p["current_stock"] >= 0
        assert p["stock_status"] in ["NORMAL", "LOW STOCK", "OUT OF STOCK"]
    print("[11/15] Current store inventory correctly joined with stock health indicators: PASS")

    # 12. Changing date range changes results
    with app.app_context():
        vel_30d = analytics_service.get_product_velocity(preset="30d")
        assert vel_30d["num_days"] == 30
        assert vel_30d["summary"]["total_units_sold"] < vel_data["summary"]["total_units_sold"]
        # Velocities are calculated over 30 days
        cb_30d = [p for p in vel_30d["products"] if p["product_name"] == "Colorbuds"][0]
        assert cb_30d["sales_velocity"] > 0
    print("[12/15] Dynamic recalculation across presets verified (30D vs 638D baseline): PASS")

    # 13. API endpoints return valid JSON
    api1 = client.get("/api/analytics/product-movement")
    assert api1.status_code == 200
    json1 = json.loads(api1.data.decode("utf-8"))
    assert json1["success"] is True
    assert len(json1["products"]) == 35
    assert json1["summary"]["total_units_sold"] == 1090565

    api2 = client.get("/api/analytics/category-summary")
    assert api2.status_code == 200
    json2 = json.loads(api2.data.decode("utf-8"))
    assert json2["success"] is True
    assert len(json2["categories"]) == 5

    api3 = client.get("/api/analytics/store-summary?limit=5")
    assert api3.status_code == 200
    json3 = json.loads(api3.data.decode("utf-8"))
    assert json3["success"] is True
    assert len(json3["stores"]) == 5

    print("[13/15] Analytical API endpoints return valid JSON (/product-movement, /category-summary, /store-summary): PASS")

    # 14. Raw source CSV files remain unchanged
    raw_inventory_size = Path("data/raw/inventory.csv").stat().st_size
    raw_products_size = Path("data/raw/products.csv").stat().st_size
    raw_sales_size = Path("data/raw/sales.csv").stat().st_size
    raw_stores_size = Path("data/raw/stores.csv").stat().st_size

    assert raw_inventory_size == 14675, f"raw inventory.csv modified! Size: {raw_inventory_size}"
    assert raw_products_size == 1572, f"raw products.csv modified! Size: {raw_products_size}"
    assert raw_sales_size == 21783359, f"raw sales.csv modified! Size: {raw_sales_size}"
    assert raw_stores_size == 2999, f"raw stores.csv modified! Size: {raw_stores_size}"
    print("[14/15] Raw source CSV files remain 100% immutable and untouched: PASS")

    # 15. Verify database counts remain in clean baseline
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

    print(f"[15/15] Final database row counts verified:")
    print(f"        - Products:        {products_count:,}")
    print(f"        - Stores:          {stores_count:,}")
    print(f"        - Inventory:       {inventory_count:,}")
    print(f"        - Sales:           {sales_count:,}")
    print(f"        - Restocks:        {restocks_count:,}")
    print(f"        - Stock Movements: {movements_count:,}")
    print("=" * 65)
    print("ALL 15 PHASE 9 TESTS PASSED SUCCESSFULLY!")
    print("=" * 65)

    conn.close()

if __name__ == "__main__":
    run_tests()
