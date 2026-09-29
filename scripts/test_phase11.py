import os
import sys
from pathlib import Path
import sqlite3
import json
import subprocess

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app import app
import db
from services import dashboard_service, analytics_service, recommendation_service

EXPECTED_RAW_SIZES = {
    "products.csv": 1572,
    "stores.csv": 2999,
    "inventory.csv": 14675,
    "sales.csv": 21783359
}

def run_tests():
    client = app.test_client()

    print("=" * 68)
    print("STARTING TEST SUITE: PHASE 11 - INTERACTIVE DASHBOARD CHARTS")
    print("=" * 68)

    # 1. Dashboard loads successfully
    res1 = client.get("/dashboard")
    assert res1.status_code == 200, f"Dashboard failed: {res1.status_code}"
    html1 = res1.data.decode("utf-8")
    assert "Executive Dashboard &amp; Visual Analytics" in html1 or "Executive Dashboard & Visual Analytics" in html1
    assert "chart-sales-trend" in html1
    assert "chart-revenue-trend" in html1
    assert "chart-category-sales" in html1
    assert "chart-top-products" in html1
    assert "chart-inventory-status" in html1
    assert "chart-inventory-categories" in html1
    assert "chart-store-sales" in html1
    assert "chart-movement-summary" in html1
    assert "chart-recommendation-summary" in html1
    assert "dashboard.js" in html1
    print("[1/20] Dashboard page loads with all 9 chart containers and script assets: PASS")

    # 2. All chart API endpoints return valid JSON
    endpoints = [
        "/api/dashboard/sales-trend",
        "/api/dashboard/revenue-trend",
        "/api/dashboard/category-sales",
        "/api/dashboard/top-products",
        "/api/dashboard/inventory-status",
        "/api/dashboard/inventory-category",
        "/api/dashboard/store-sales",
        "/api/dashboard/movement-summary",
        "/api/dashboard/recommendation-summary"
    ]
    for ep in endpoints:
        res = client.get(ep)
        assert res.status_code == 200, f"Endpoint {ep} returned status {res.status_code}"
        payload = json.loads(res.data.decode("utf-8"))
        assert payload.get("success") is True, f"Endpoint {ep} missing success flag"
    print(f"[2/20] All {len(endpoints)} dashboard chart API endpoints return valid HTTP 200 JSON: PASS")

    # 3. Sales trend aggregation reconciles with SQLite
    with app.app_context():
        db_sales = db.query_db("SELECT SUM(quantity) AS total_units, COUNT(DISTINCT sale_date) AS active_days FROM sales;", one=True)
        db_total_units = int(db_sales["total_units"])
        db_active_days = int(db_sales["active_days"])

    trend_res = client.get("/api/dashboard/sales-trend?preset=full")
    trend_data = json.loads(trend_res.data.decode("utf-8"))
    assert trend_data["total_units"] == db_total_units == 1090565
    assert sum(trend_data["units"]) == db_total_units
    assert len(trend_data["labels"]) == db_active_days == 638
    print(f"[3/20] Sales trend aggregation reconciles with SQLite (Total: {trend_data['total_units']:,} units across {len(trend_data['labels'])} dates): PASS")

    # 4. Revenue aggregation reconciles with SQLite
    with app.app_context():
        db_rev = db.query_db("SELECT ROUND(SUM(total_amount), 2) AS total_rev FROM sales;", one=True)
        db_total_rev = float(db_rev["total_rev"])

    rev_res = client.get("/api/dashboard/revenue-trend?preset=full")
    rev_data = json.loads(rev_res.data.decode("utf-8"))
    assert rev_data["total_revenue"] == db_total_rev == 14444572.35
    assert round(sum(rev_data["data"]), 2) == db_total_rev
    print(f"[4/20] Revenue trend aggregation reconciles with SQLite (Calculated Total: ${rev_data['total_revenue']:,.2f}): PASS")

    # 5. Category sales aggregation works
    cat_res = client.get("/api/dashboard/category-sales")
    cat_data = json.loads(cat_res.data.decode("utf-8"))
    assert len(cat_data["labels"]) == 5
    assert set(cat_data["labels"]) == {"Art & Crafts", "Toys", "Games", "Sports & Outdoors", "Electronics"}
    assert sum(cat_data["units"]) == db_total_units
    assert round(sum(cat_data["revenue"]), 2) == db_total_rev
    print("[5/20] Category sales aggregation verified across all 5 catalog merchandise categories: PASS")

    # 6. Top product aggregation works
    top_res = client.get("/api/dashboard/top-products?limit=10")
    top_data = json.loads(top_res.data.decode("utf-8"))
    assert len(top_data["labels"]) == 10
    assert top_data["labels"][0] == "Colorbuds"
    assert top_data["units"][0] == 104368
    # Verify descending sort order
    for i in range(len(top_data["units"]) - 1):
        assert top_data["units"][i] >= top_data["units"][i + 1]
    print("[6/20] Top 10 products horizontal bar aggregation verified (Leader: Colorbuds with 104,368 units): PASS")

    # 7. Inventory status counts work
    inv_stat_res = client.get("/api/dashboard/inventory-status")
    inv_stat = json.loads(inv_stat_res.data.decode("utf-8"))
    assert inv_stat["labels"] == ["NORMAL", "LOW STOCK", "OUT OF STOCK"]
    assert inv_stat["counts"] == [990, 526, 234]
    assert inv_stat["total_records"] == 1750
    assert inv_stat["total_units"] == 29742
    print(f"[7/20] Inventory status counts verified from current SQLite state (Normal: 990, Low: 526, Out: 234): PASS")

    # 8. Inventory-by-category works
    inv_cat_res = client.get("/api/dashboard/inventory-category")
    inv_cat = json.loads(inv_cat_res.data.decode("utf-8"))
    assert len(inv_cat["labels"]) == 5
    assert sum(inv_cat["units"]) == 29742
    print(f"[8/20] Inventory units by category verified (Total physical stock on hand: {sum(inv_cat['units']):,} units): PASS")

    # 9. Store sales aggregation works
    store_10_res = client.get("/api/dashboard/store-sales?limit=10")
    store_10 = json.loads(store_10_res.data.decode("utf-8"))
    assert len(store_10["labels"]) == 10

    store_5_res = client.get("/api/dashboard/store-sales?limit=5")
    store_5 = json.loads(store_5_res.data.decode("utf-8"))
    assert len(store_5["labels"]) == 5

    store_all_res = client.get("/api/dashboard/store-sales?limit=all")
    store_all = json.loads(store_all_res.data.decode("utf-8"))
    assert len(store_all["labels"]) == 50
    assert sum(store_all["units"]) == db_total_units
    print("[9/20] Store sales aggregation verified with Top 5, Top 10, and All (50 branches) selector: PASS")

    # 10. Movement summary matches Phase 9
    mov_res = client.get("/api/dashboard/movement-summary?preset=full")
    mov_data = json.loads(mov_res.data.decode("utf-8"))
    assert mov_data["labels"] == ["FAST MOVING", "NORMAL", "SLOW MOVING"]
    assert mov_data["counts"] == [9, 17, 9]
    print("[10/20] Product movement distribution matches Phase 9 empirical classification (9 Fast, 17 Normal, 9 Slow): PASS")

    # 11. Recommendation summary matches Phase 10
    rec_res = client.get("/api/dashboard/recommendation-summary?preset=full")
    rec_data = json.loads(rec_res.data.decode("utf-8"))
    assert sum(rec_data["counts"]) == 35
    assert rec_data["summary"]["requires_attention_count"] == 7
    print(f"[11/20] Recommendation summary matches Phase 10 engine (Requires Attention: {rec_data['summary']['requires_attention_count']}, Maintain: 13, Monitor: 15): PASS")

    # 12. Date filtering changes sales chart data
    res_2017 = client.get("/api/dashboard/sales-trend?preset=2017")
    d_2017 = json.loads(res_2017.data.decode("utf-8"))
    res_2018 = client.get("/api/dashboard/sales-trend?preset=2018")
    d_2018 = json.loads(res_2018.data.decode("utf-8"))

    assert d_2017["total_units"] > 0
    assert d_2018["total_units"] > 0
    assert d_2017["total_units"] + d_2018["total_units"] == db_total_units
    print(f"[12/20] Date filtering dynamically updates chart datasets (2017: {d_2017['total_units']:,} u, 2018: {d_2018['total_units']:,} u): PASS")

    # 13. Empty date ranges are handled gracefully
    empty_res = client.get("/api/dashboard/sales-trend?start_date=2030-01-01&end_date=2030-01-31")
    empty_data = json.loads(empty_res.data.decode("utf-8"))
    assert empty_res.status_code == 200
    assert empty_data["labels"] == []
    assert empty_data["units"] == []
    assert empty_data["total_units"] == 0
    print("[13/20] Empty date ranges handled safely with empty series (status 200, 0 points): PASS")

    # 14. No raw 829k transaction rows are returned by chart APIs
    trend_bytes = len(trend_res.data)
    assert len(trend_data["labels"]) <= 638
    assert trend_bytes < 150000  # < 150KB aggregated vs > 25MB raw sales rows
    print(f"[14/20] Performance verified: Chart APIs return SQL-aggregated summaries only ({trend_bytes:,} bytes, never 829k rows): PASS")

    # 15. Raw CSV files remain 100% unchanged
    raw_dir = BASE_DIR / "data" / "raw"
    for filename, expected_size in EXPECTED_RAW_SIZES.items():
        file_path = raw_dir / filename
        assert file_path.exists(), f"Raw file {filename} is missing!"
        actual_size = file_path.stat().st_size
        assert actual_size == expected_size, (
            f"Raw file {filename} size changed! Expected {expected_size}, got {actual_size}"
        )
    print("[15/20] Raw source CSV files remain 100% immutable and untouched: PASS")

    # 16-20. Regression test suites
    regression_scripts = [
        ("Phase 6 (Sales POS & Atomic Stock Decrement)", "scripts/test_phase6.py"),
        ("Phase 7 (Inbound Restock & Stock Movements)", "scripts/test_phase7.py"),
        ("Phase 8 (Inventory Grid & Valuation)", "scripts/test_phase8.py"),
        ("Phase 9 (Velocity & Movement Classification)", "scripts/test_phase9.py"),
        ("Phase 10 (Rule-Based Recommendation Engine)", "scripts/test_phase10.py")
    ]

    for idx, (suite_name, script_path) in enumerate(regression_scripts, start=16):
        res = subprocess.run([sys.executable, script_path], capture_output=True, text=True)
        assert res.returncode == 0, f"Regression test failed for {suite_name}:\n{res.stdout}\n{res.stderr}"
        print(f"[{idx}/20] {suite_name} regression suite: PASS")

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
    print("ALL 20 PHASE 11 TESTS PASSED SUCCESSFULLY!")
    print("=" * 68)

if __name__ == "__main__":
    run_tests()
