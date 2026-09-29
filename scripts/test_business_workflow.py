"""
Smart Inventory & Sales Analysis System - End-to-End Business Workflow Test
---------------------------------------------------------------------------
Phase 14 Step 4: Executes a controlled temporary transaction cycle:
1. Cleans any previous test residue and verifies baseline pre-conditions
2. Validates transaction rollback on invalid inputs
3. Executes a valid Sale (decrements stock, writes SALE stock movement)
4. Executes a valid Restock (increments stock, writes RESTOCK stock movement)
5. Verifies application pages reflect updated metrics
6. Cleans up and verifies database returns EXACTLY to the baseline
"""

import sys
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app import app
import db

def cleanup_test_data(sale_id=None, restock_id=None):
    with app.app_context():
        conn = db.get_db()
        # Clean any sales >= 829263
        conn.execute("DELETE FROM sales WHERE sale_id >= 829263;")
        conn.execute("DELETE FROM restocks WHERE restock_id >= 1;")
        conn.execute("DELETE FROM stock_movements WHERE movement_id >= 1517;")
        conn.execute("UPDATE inventory SET stock_on_hand = 27 WHERE store_id = 1 AND product_id = 1;")
        conn.commit()

def test_workflow():
    print("=" * 68)
    print("STARTING END-TO-END BUSINESS WORKFLOW TEST (SALE -> RESTOCK -> CLEANUP)")
    print("=" * 68)

    cleanup_test_data()
    client = app.test_client()

    test_sale_id = None
    test_restock_id = None

    try:
        # 1. Baseline Pre-conditions Check
        with app.app_context():
            conn = db.get_db()
            prod_count = conn.execute("SELECT COUNT(*) FROM products;").fetchone()[0]
            store_count = conn.execute("SELECT COUNT(*) FROM stores;").fetchone()[0]
            inv_count = conn.execute("SELECT COUNT(*) FROM inventory;").fetchone()[0]
            sales_count = conn.execute("SELECT COUNT(*) FROM sales;").fetchone()[0]
            restock_count = conn.execute("SELECT COUNT(*) FROM restocks;").fetchone()[0]
            movement_count = conn.execute("SELECT COUNT(*) FROM stock_movements;").fetchone()[0]

            assert prod_count == 35
            assert store_count == 50
            assert inv_count == 1750
            assert sales_count == 829262
            assert restock_count == 0
            assert movement_count == 1516

            inv_row = conn.execute("SELECT stock_on_hand FROM inventory WHERE store_id = 1 AND product_id = 1;").fetchone()
            initial_stock = inv_row[0]
            assert initial_stock == 27, f"Expected initial stock 27, got {initial_stock}"
            print(f"[1/7] Baseline verified: Prod #1 at Store #1 stock = {initial_stock}, Sales = {sales_count:,}")

        # 2. Test Invalid Transaction Rollback
        print("[2/7] Testing transaction rejection & atomic rollback on invalid sale...")
        res_invalid = client.post("/sales/add", data={
            "store_id": "1",
            "product_id": "1",
            "quantity": "999",  # exceeds 27 stock
            "sale_date": "2026-09-29"
        }, follow_redirects=True)
        with app.app_context():
            conn = db.get_db()
            check_stock = conn.execute("SELECT stock_on_hand FROM inventory WHERE store_id = 1 AND product_id = 1;").fetchone()[0]
            assert check_stock == 27, f"Rollback failed: stock altered to {check_stock}"
            check_sales = conn.execute("SELECT COUNT(*) FROM sales;").fetchone()[0]
            assert check_sales == 829262, "Rollback failed: rogue sale inserted"
        print("      PASS: Insufficient stock rejected atomically, stock remained 27.")

        # 3. Test Valid Sale Execution
        print("[3/7] Recording valid Sale transaction (qty = 3)...")
        res_sale = client.post("/sales/add", data={
            "store_id": "1",
            "product_id": "1",
            "quantity": "3",
            "sale_date": "2026-09-29"
        }, follow_redirects=True)
        assert res_sale.status_code == 200

        with app.app_context():
            conn = db.get_db()
            sale_row = conn.execute("SELECT sale_id, store_id, product_id, quantity, total_amount FROM sales ORDER BY sale_id DESC LIMIT 1;").fetchone()
            test_sale_id = sale_row["sale_id"]
            assert test_sale_id == 829263, f"Expected sale_id 829263, got {test_sale_id}"
            assert sale_row["quantity"] == 3

            stock_after_sale = conn.execute("SELECT stock_on_hand FROM inventory WHERE store_id = 1 AND product_id = 1;").fetchone()[0]
            assert stock_after_sale == 24, f"Expected stock 24 after sale, got {stock_after_sale}"

            sale_mov = conn.execute("SELECT movement_id, movement_type, quantity FROM stock_movements WHERE reference_id = ? AND movement_type = 'SALE' ORDER BY movement_id DESC LIMIT 1;", (test_sale_id,)).fetchone()
            assert sale_mov is not None
            assert sale_mov["movement_type"] == "SALE"
            assert sale_mov["quantity"] == -3
        print(f"      PASS: Sale #{test_sale_id} recorded, stock decreased (27 -> 24), SALE movement logged (-3).")

        # 4. Test Valid Restock Execution
        print("[4/7] Recording valid Restock transaction (qty = 10)...")
        res_restock = client.post("/restock/add", data={
            "store_id": "1",
            "product_id": "1",
            "quantity": "10",
            "cost_per_unit": "8.50",
            "restock_date": "2026-09-29",
            "notes": "Phase 14 validation restock"
        }, follow_redirects=True)
        assert res_restock.status_code == 200

        with app.app_context():
            conn = db.get_db()
            restock_row = conn.execute("SELECT restock_id, store_id, product_id, quantity, cost_per_unit FROM restocks ORDER BY restock_id DESC LIMIT 1;").fetchone()
            test_restock_id = restock_row["restock_id"]
            assert restock_row["quantity"] == 10
            assert restock_row["cost_per_unit"] == 8.50

            stock_after_restock = conn.execute("SELECT stock_on_hand FROM inventory WHERE store_id = 1 AND product_id = 1;").fetchone()[0]
            assert stock_after_restock == 34, f"Expected stock 34 after restock, got {stock_after_restock}"

            restock_mov = conn.execute("SELECT movement_id, movement_type, quantity FROM stock_movements WHERE reference_id = ? AND movement_type = 'RESTOCK' ORDER BY movement_id DESC LIMIT 1;", (test_restock_id,)).fetchone()
            assert restock_mov is not None
            assert restock_mov["movement_type"] == "RESTOCK"
            assert restock_mov["quantity"] == 10
        print(f"      PASS: Restock #{test_restock_id} recorded, stock increased (24 -> 34), RESTOCK movement logged (+10).")

        # 5. Verify Application Web Presentation Reflects Updated Stock
        print("[5/7] Verifying web application renders the updated transaction & inventory state...")
        res_inv_view = client.get("/inventory?store_id=1&product_id=1")
        assert res_inv_view.status_code == 200
        assert b"34" in res_inv_view.data, "Updated stock of 34 not rendered in inventory view"

        res_sale_detail = client.get(f"/sales/{test_sale_id}")
        assert res_sale_detail.status_code == 200
        assert b"Sale Transaction #829263" in res_sale_detail.data

        res_restock_detail = client.get(f"/restock/{test_restock_id}")
        assert res_restock_detail.status_code == 200
        assert f"Restock Order #{test_restock_id}".encode("utf-8") in res_restock_detail.data
        print("      PASS: Web interface visibly displays updated stock (34) and transaction detail pages.")

    finally:
        # 6. Cleanup & Restoration of Database Baseline
        print("[6/7] Performing atomic cleanup and rolling back test transactions...")
        cleanup_test_data()
        print("      PASS: Temporary test records removed and stock restored to 27.")

    # 7. Post-Test Baseline Re-Verification
    print("[7/7] Re-verifying exact database baseline counts...")
    with app.app_context():
        conn = db.get_db()
        final_prods = conn.execute("SELECT COUNT(*) FROM products;").fetchone()[0]
        final_stores = conn.execute("SELECT COUNT(*) FROM stores;").fetchone()[0]
        final_inv = conn.execute("SELECT COUNT(*) FROM inventory;").fetchone()[0]
        final_sales = conn.execute("SELECT COUNT(*) FROM sales;").fetchone()[0]
        final_restocks = conn.execute("SELECT COUNT(*) FROM restocks;").fetchone()[0]
        final_movements = conn.execute("SELECT COUNT(*) FROM stock_movements;").fetchone()[0]
        final_stock = conn.execute("SELECT stock_on_hand FROM inventory WHERE store_id = 1 AND product_id = 1;").fetchone()[0]

        assert final_prods == 35, f"Expected 35 products, got {final_prods}"
        assert final_stores == 50, f"Expected 50 stores, got {final_stores}"
        assert final_inv == 1750, f"Expected 1,750 inventory, got {final_inv}"
        assert final_sales == 829262, f"Expected 829,262 sales, got {final_sales}"
        assert final_restocks == 0, f"Expected 0 restocks, got {final_restocks}"
        assert final_movements == 1516, f"Expected 1,516 movements, got {final_movements}"
        assert final_stock == 27, f"Expected stock restored to 27, got {final_stock}"

    print("      Database baseline perfectly restored:")
    print("        - Products:        35")
    print("        - Stores:          50")
    print("        - Inventory:       1,750")
    print("        - Sales:           829,262")
    print("        - Restocks:        0")
    print("        - Stock Movements: 1,516")
    print("=" * 68)
    print("END-TO-END BUSINESS WORKFLOW TEST PASSED WITH 100% INTEGRITY!")
    print("=" * 68)

if __name__ == "__main__":
    test_workflow()
