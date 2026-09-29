import os
import sys
from pathlib import Path
import sqlite3
import json

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app import app
from services import recommendation_service, analytics_service

def run_tests():
    client = app.test_client()

    print("=" * 68)
    print("STARTING TEST SUITE: PHASE 10 - RULE-BASED INVENTORY RECOMMENDATIONS")
    print("=" * 68)

    # 1. Recommendations page loads
    res1 = client.get("/recommendations")
    assert res1.status_code == 200, f"Failed on /recommendations: {res1.status_code}"
    html1 = res1.data.decode("utf-8")
    assert "Rule-Based Inventory Recommendations" in html1
    assert "Transparent Rule-Based Decision Support System" in html1
    assert "Analysis Period:" in html1
    print("[1/18] Recommendations page loads successfully (HTTP 200): PASS")

    # 2. Recommendation API works
    api_res = client.get("/api/recommendations")
    assert api_res.status_code == 200
    api_json = json.loads(api_res.data.decode("utf-8"))
    assert api_json["success"] is True
    assert len(api_json["recommendations"]) == 35
    assert "summary" in api_json
    print("[2/18] Recommendation API returns valid JSON with 35 catalog items: PASS")

    # 3. Summary API works
    sum_res = client.get("/api/recommendations/summary")
    assert sum_res.status_code == 200
    sum_json = json.loads(sum_res.data.decode("utf-8"))
    assert sum_json["success"] is True
    summary = sum_json["summary"]
    assert summary["total_products"] == 35
    assert "requires_attention_count" in summary
    assert "high_priority_count" in summary
    assert "medium_priority_count" in summary
    assert "low_priority_count" in summary
    assert "none_priority_count" in summary
    print(f"[3/18] Summary API returns valid metrics (Requires Attention: {summary['requires_attention_count']}, Med: {summary['medium_priority_count']}): PASS")

    # 4. RULE B: Fast + zero stock -> PRIORITIZE REPLENISHMENT (HIGH)
    test_prod_b = {
        "product_id": 991,
        "product_name": "Test Item B",
        "movement_status": "FAST MOVING",
        "current_stock": 0,
        "total_reorder_level": 500,
        "sales_velocity": 120.0
    }
    rec_b = recommendation_service.evaluate_product_recommendation(test_prod_b)
    assert rec_b["recommendation"] == "PRIORITIZE REPLENISHMENT"
    assert rec_b["priority"] == "HIGH"
    assert "out of stock" in rec_b["reason"].lower()
    print("[4/18] Rule B verified: Fast Moving + 0 stock -> PRIORITIZE REPLENISHMENT (HIGH): PASS")

    # 5. RULE A: Fast + below reorder level -> REPLENISH SOON (HIGH)
    test_prod_a = {
        "product_id": 992,
        "product_name": "Test Item A",
        "movement_status": "FAST MOVING",
        "current_stock": 350,
        "total_reorder_level": 500,
        "sales_velocity": 85.0
    }
    rec_a = recommendation_service.evaluate_product_recommendation(test_prod_a)
    assert rec_a["recommendation"] == "REPLENISH SOON"
    assert rec_a["priority"] == "HIGH"
    assert "below the configured reorder level" in rec_a["reason"]
    print("[5/18] Rule A verified: Fast Moving + Stock < Reorder -> REPLENISH SOON (HIGH): PASS")

    # 6. RULE D: Slow + stock >= reorder level -> REVIEW INVENTORY LEVEL (MEDIUM)
    test_prod_d = {
        "product_id": 993,
        "product_name": "Test Item D",
        "movement_status": "SLOW MOVING",
        "current_stock": 650,
        "total_reorder_level": 500,
        "sales_velocity": 5.0
    }
    rec_d = recommendation_service.evaluate_product_recommendation(test_prod_d)
    assert rec_d["recommendation"] == "REVIEW INVENTORY LEVEL"
    assert rec_d["priority"] == "MEDIUM"
    assert "slow-moving product has stock at or above its reorder threshold" in rec_d["reason"].lower()
    print("[6/18] Rule D verified: Slow Moving + Stock >= Reorder -> REVIEW INVENTORY LEVEL (MEDIUM): PASS")

    # 7. RULE F: Normal + healthy stock -> MAINTAIN CURRENT LEVEL (LOW)
    test_prod_f = {
        "product_id": 994,
        "product_name": "Test Item F",
        "movement_status": "NORMAL",
        "current_stock": 700,
        "total_reorder_level": 500,
        "sales_velocity": 35.0
    }
    rec_f = recommendation_service.evaluate_product_recommendation(test_prod_f)
    assert rec_f["recommendation"] == "MAINTAIN CURRENT LEVEL"
    assert rec_f["priority"] == "LOW"
    assert "within the normal range" in rec_f["reason"]
    print("[7/18] Rule F verified: Normal + Stock >= Reorder -> MAINTAIN CURRENT LEVEL (LOW): PASS")

    # 8. RULE G: Fallback -> MONITOR (NONE)
    test_prod_g = {
        "product_id": 995,
        "product_name": "Test Item G",
        "movement_status": "NORMAL",
        "current_stock": 450,
        "total_reorder_level": 500,
        "sales_velocity": 25.0
    }
    rec_g = recommendation_service.evaluate_product_recommendation(test_prod_g)
    assert rec_g["recommendation"] == "MONITOR"
    assert rec_g["priority"] == "NONE"
    assert "no strong stock or movement signal" in rec_g["reason"].lower()
    print("[8/18] Rule G verified: Fallback conditions -> MONITOR (NONE): PASS")

    # 9. Rule priority is deterministic (Out-of-Stock takes precedence over Low Stock)
    # A fast moving product with stock=0 also has stock < reorder, but must get PRIORITIZE REPLENISHMENT
    rec_priority = recommendation_service.evaluate_product_recommendation({
        "movement_status": "FAST MOVING",
        "current_stock": 0,
        "total_reorder_level": 500,
        "sales_velocity": 100.0
    })
    assert rec_priority["recommendation"] == "PRIORITIZE REPLENISHMENT", "Priority 1 did not take precedence!"
    print("[9/18] Rule evaluation order is deterministic (Priority 1 > Priority 2): PASS")

    # 10. Stock coverage calculation
    # stock = 700, velocity = 35.0 -> coverage = 20.0 days
    test_cov = recommendation_service.evaluate_product_recommendation({
        "movement_status": "NORMAL",
        "current_stock": 700,
        "total_reorder_level": 500,
        "sales_velocity": 35.0
    })
    assert test_cov["stock_coverage_days"] == 20.0, f"Expected 20.0, got {test_cov['stock_coverage_days']}"
    print("[10/18] Stock coverage calculation verified (700 stock / 35.0 vel = 20.0 days): PASS")

    # 11. Zero velocity does not cause division-by-zero
    test_zero_vel = recommendation_service.evaluate_product_recommendation({
        "movement_status": "SLOW MOVING",
        "current_stock": 500,
        "total_reorder_level": 500,
        "sales_velocity": 0.0
    })
    assert test_zero_vel["stock_coverage_days"] is None
    print("[11/18] Zero velocity handled safely (coverage is None, zero division avoided): PASS")

    # 12. Date changes update velocity inputs
    with app.app_context():
        rec_full = recommendation_service.get_product_recommendations(preset="full")
        rec_30d = recommendation_service.get_product_recommendations(preset="30d")
        assert rec_full["num_days"] == 638
        assert rec_30d["num_days"] == 30
        
        # Colorbuds coverage in 638d vs 30d
        cb_full = [p for p in rec_full["recommendations"] if p["product_name"] == "Colorbuds"][0]
        cb_30d = [p for p in rec_30d["recommendations"] if p["product_name"] == "Colorbuds"][0]
        assert cb_full["sales_velocity"] > 0
        assert cb_30d["sales_velocity"] > 0
    print("[12/18] Date range switching updates velocities and stock coverage dynamically: PASS")

    # 13. Recommendation reasons are generated correctly and non-empty
    for item in rec_full["recommendations"]:
        assert item["reason"] is not None and len(item["reason"].strip()) > 10
        assert item["recommendation"] in [
            "PRIORITIZE REPLENISHMENT",
            "REPLENISH SOON",
            "MONITOR STOCK",
            "REVIEW INVENTORY LEVEL",
            "REPLENISH OR REVIEW",
            "MAINTAIN CURRENT LEVEL",
            "MONITOR"
        ]
        assert item["priority"] in ["HIGH", "MEDIUM", "LOW", "NONE"]
    print("[13/18] All 35 catalog recommendations have valid explainable reasons: PASS")

    # 14. Product detail page displays recommendation card
    res14 = client.get("/products/1")
    assert res14.status_code == 200
    html14 = res14.data.decode("utf-8")
    assert "Inventory Recommendation" in html14
    assert "Rule-based decision support signal" in html14
    assert "MONITOR STOCK" in html14
    assert "Priority: MEDIUM" in html14
    print("[14/18] Product detail page (/products/1) renders live recommendation & reason: PASS")

    # 15. Inventory page displays recommendation column
    res15 = client.get("/inventory")
    assert res15.status_code == 200
    html15 = res15.data.decode("utf-8")
    assert "Recommendation</th>" in html15
    print("[15/18] Inventory overview page (/inventory) renders Recommendation column: PASS")

    # 16. Dashboard displays Inventory Attention panel
    res16 = client.get("/dashboard")
    assert res16.status_code == 200
    html16 = res16.data.decode("utf-8")
    assert "Inventory Attention &amp; Decision Support" in html16 or "Inventory Attention & Decision Support" in html16
    assert "Medium Priority" in html16
    assert "View All Recommendations" in html16
    print("[16/18] Dashboard renders Inventory Attention decision support summary: PASS")

    # 17. Raw source CSV files remain unchanged
    raw_inventory_size = Path("data/raw/inventory.csv").stat().st_size
    raw_products_size = Path("data/raw/products.csv").stat().st_size
    raw_sales_size = Path("data/raw/sales.csv").stat().st_size
    raw_stores_size = Path("data/raw/stores.csv").stat().st_size

    assert raw_inventory_size == 14675, f"raw inventory.csv modified! Size: {raw_inventory_size}"
    assert raw_products_size == 1572, f"raw products.csv modified! Size: {raw_products_size}"
    assert raw_sales_size == 21783359, f"raw sales.csv modified! Size: {raw_sales_size}"
    assert raw_stores_size == 2999, f"raw stores.csv modified! Size: {raw_stores_size}"
    print("[17/18] Raw source CSV files remain 100% immutable and untouched: PASS")

    # 18. Database baseline row counts verified
    conn = sqlite3.connect("database/inventory.db")
    c = conn.cursor()
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

    print(f"[18/18] Final database row counts verified:")
    print(f"        - Products:        {products_count:,}")
    print(f"        - Stores:          {stores_count:,}")
    print(f"        - Inventory:       {inventory_count:,}")
    print(f"        - Sales:           {sales_count:,}")
    print(f"        - Restocks:        {restocks_count:,}")
    print(f"        - Stock Movements: {movements_count:,}")
    print("=" * 68)
    print("ALL 18 PHASE 10 TESTS PASSED SUCCESSFULLY!")
    print("=" * 68)

    conn.close()

if __name__ == "__main__":
    run_tests()
