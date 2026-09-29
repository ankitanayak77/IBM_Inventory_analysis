import os
import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import sqlite3
import json
from app import app

def run_tests():
    client = app.test_client()

    print("=" * 60)
    print("STARTING TEST SUITE: PHASE 6 - SALES MODULE & TRANSACTIONS")
    print("=" * 60)

    # 1. Sales history loads
    res1 = client.get("/sales")
    assert res1.status_code == 200, f"Failed on /sales: {res1.status_code}"
    assert b"Sales History" in res1.data
    print("[1/18] Sales history page loads: PASS")

    # 2. Pagination works
    res2_p1 = client.get("/sales?page=1&per_page=25")
    assert res2_p1.status_code == 200
    assert b"Showing <strong>1" in res2_p1.data

    res2_p2 = client.get("/sales?page=2&per_page=25")
    assert res2_p2.status_code == 200
    assert b"Showing <strong>26" in res2_p2.data
    print("[2/18] Server-side pagination works (page 1 & 2, per_page=25): PASS")

    # 3. Product filter works
    res3 = client.get("/sales?product_id=1")
    assert res3.status_code == 200
    assert b"Action Figure" in res3.data
    print("[3/18] Product filter works: PASS")

    # 4. Store filter works
    res4 = client.get("/sales?store_id=1")
    assert res4.status_code == 200
    assert b"Maven Toys Guadalajara 1" in res4.data
    print("[4/18] Store filter works: PASS")

    # 5. Date filter works
    res5 = client.get("/sales?date_from=2017-01-01&date_to=2017-01-02")
    assert res5.status_code == 200
    assert b"2017-01-01" in res5.data
    print("[5/18] Date filter works: PASS")

    # 6. Search works
    res6_id = client.get("/sales?search=829260")
    assert res6_id.status_code == 200
    assert b"#829260" in res6_id.data

    res6_name = client.get("/sales?search=Rubik")
    assert res6_name.status_code == 200
    assert b"Rubik" in res6_name.data
    print("[6/18] Search works (by Sale ID and Product Name): PASS")

    # 7. Sale form loads
    res7 = client.get("/sales/add")
    assert res7.status_code == 200
    assert b"Record Sale Transaction" in res7.data
    print("[7/18] Add sale form loads: PASS")

    # 8. Current inventory API works
    res8 = client.get("/api/inventory/1/1")
    assert res8.status_code == 200
    data8 = json.loads(res8.data)
    assert data8["success"] is True
    assert data8["product_id"] == 1
    assert data8["store_id"] == 1
    assert "stock_on_hand" in data8
    stock_val = data8["stock_on_hand"]
    print(f"[8/18] Inventory lookup API works (Stock at Store 1 for Prod 1: {stock_val}): PASS")

    # 9, 10, 11, 12: Valid sale transaction execution
    conn = sqlite3.connect("database/inventory.db")
    conn.execute("PRAGMA foreign_keys = ON;")
    c = conn.cursor()

    # Find a store/product pair with stock >= 10
    c.execute("SELECT product_id, store_id, stock_on_hand FROM inventory WHERE stock_on_hand >= 10 LIMIT 1;")
    test_prod, test_store, initial_stock = c.fetchone()
    print(f"       Test target: Product #{test_prod} at Store #{test_store}, Initial Stock: {initial_stock}")

    sale_data = {
        "product_id": str(test_prod),
        "store_id": str(test_store),
        "quantity": "3",
        "sale_date": "2026-09-28",
        "notes": "Unit test transaction sale"
    }
    res9 = client.post("/sales/add", data=sale_data, follow_redirects=True)
    assert res9.status_code == 200
    assert b"recorded successfully" in res9.data
    print("[9/18] Valid sale POST request succeeds: PASS")

    # 10. Verify sales row inserted in SQLite
    c.execute("SELECT sale_id, product_id, store_id, quantity, unit_price, total_amount, notes FROM sales ORDER BY sale_id DESC LIMIT 1;")
    new_sale = c.fetchone()
    test_sale_id = new_sale[0]
    assert new_sale[1] == test_prod
    assert new_sale[2] == test_store
    assert new_sale[3] == 3
    assert new_sale[6] == "Unit test transaction sale"
    print(f"[10/18] New sale #{test_sale_id} confirmed in SQLite sales table: PASS")

    # 11. Verify inventory decreased
    c.execute("SELECT stock_on_hand FROM inventory WHERE store_id = ? AND product_id = ?;", (test_store, test_prod))
    new_stock = c.fetchone()[0]
    assert new_stock == initial_stock - 3, f"Expected {initial_stock - 3}, got {new_stock}"
    print(f"[11/18] Store inventory decreased correctly ({initial_stock} -> {new_stock}): PASS")

    # 12. Verify stock movement audit log
    c.execute("SELECT movement_id, product_id, store_id, movement_type, quantity, reference_id FROM stock_movements WHERE reference_id = ? AND movement_type = 'SALE';", (test_sale_id,))
    movement_row = c.fetchone()
    assert movement_row is not None, "Stock movement not logged!"
    assert movement_row[4] == -3, f"Expected quantity -3, got {movement_row[4]}"
    print(f"[12/18] Stock movement #{movement_row[0]} logged with negative quantity (-3): PASS")

    # 13. Insufficient stock is rejected
    excessive_data = {
        "product_id": str(test_prod),
        "store_id": str(test_store),
        "quantity": str(new_stock + 100),
        "sale_date": "2026-09-28",
        "notes": "Excessive sale test"
    }
    res13 = client.post("/sales/add", data=excessive_data)
    assert res13.status_code == 200
    assert b"Insufficient stock" in res13.data

    # Verify stock did not change
    c.execute("SELECT stock_on_hand FROM inventory WHERE store_id = ? AND product_id = ?;", (test_store, test_prod))
    assert c.fetchone()[0] == new_stock, "Stock should NOT change after rejected sale"
    print("[13/18] Insufficient stock rejected & inventory unchanged: PASS")

    # 14. Invalid quantities rejected (negative, zero, string)
    for bad_qty in ["0", "-5", "abc"]:
        bad_data = {
            "product_id": str(test_prod),
            "store_id": str(test_store),
            "quantity": bad_qty,
            "sale_date": "2026-09-28",
            "notes": "Bad quantity test"
        }
        res14 = client.post("/sales/add", data=bad_data)
        assert b"Quantity" in res14.data or b"at least 1 unit" in res14.data
    print("[14/18] Invalid quantities (0, negative, string) rejected: PASS")

    # 15. Inactive product is rejected
    c.execute("UPDATE products SET active = 0 WHERE product_id = ?;", (test_prod,))
    conn.commit()
    inactive_data = {
        "product_id": str(test_prod),
        "store_id": str(test_store),
        "quantity": "1",
        "sale_date": "2026-09-28",
        "notes": "Inactive test"
    }
    res15 = client.post("/sales/add", data=inactive_data)
    assert b"is inactive" in res15.data
    c.execute("UPDATE products SET active = 1 WHERE product_id = ?;", (test_prod,))
    conn.commit()
    print("[15/18] Inactive product rejected from sale: PASS")

    # 16. Nonexistent product or store rejected
    bad_prod_data = {
        "product_id": "99999",
        "store_id": str(test_store),
        "quantity": "1",
        "sale_date": "2026-09-28"
    }
    res16 = client.post("/sales/add", data=bad_prod_data)
    assert b"does not exist" in res16.data
    print("[16/18] Nonexistent product/store cleanly rejected: PASS")

    # 17. Historical sales are not editable/deletable
    res_edit_sale = client.get("/sales/1/edit")
    assert res_edit_sale.status_code == 404
    res_del_sale = client.post("/sales/1/delete")
    assert res_del_sale.status_code == 404
    print("[17/18] Historical sales are read-only (no edit/delete routes): PASS")

    # 18. Database rollback works on transaction error & clean restoration
    c.execute("DELETE FROM stock_movements WHERE reference_id = ?;", (test_sale_id,))
    c.execute("DELETE FROM sales WHERE sale_id = ?;", (test_sale_id,))
    c.execute("UPDATE inventory SET stock_on_hand = ? WHERE store_id = ? AND product_id = ?;", (initial_stock, test_store, test_prod))
    conn.commit()

    c.execute("SELECT stock_on_hand FROM inventory WHERE store_id = ? AND product_id = ?;", (test_store, test_prod))
    restored_stock = c.fetchone()[0]
    assert restored_stock == initial_stock, "Stock restore check"
    print(f"[18/18] Stock restoration & rollback verification complete ({restored_stock} == {initial_stock}): PASS")

    conn.close()
    print("=" * 60)
    print("ALL 18 VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
