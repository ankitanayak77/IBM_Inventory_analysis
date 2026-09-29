"""
Smart Inventory & Sales Analysis System - Route & Presentation Validator
-------------------------------------------------------------------------
Phase 14 Step 3: Validates all application routes, filters, forms, error pages,
and static assets against the active Flask application.
"""

import urllib.request
import urllib.error
import sys

BASE_URL = "http://127.0.0.1:5000"

ROUTES_TO_TEST = [
    ("/", 200, "Executive Dashboard"),
    ("/dashboard", 200, "Executive Dashboard"),
    ("/products", 200, "Product Catalog"),
    ("/inventory", 200, "Store Inventory Management"),
    ("/sales", 200, "Sales History"),
    ("/restock", 200, "Inventory Restocking History"),
    ("/analytics", 200, "Product Movement Analytics"),
    ("/recommendations", 200, "Rule-Based Inventory Recommendations"),
    ("/reports", 200, "Analytical Reports"),
    ("/products/1", 200, "Action Figure"),
    ("/sales/829262", 200, "Sale Transaction #829262"),
    # Forms
    ("/products/add", 200, "Add New Catalog Product"),
    ("/products/1/edit", 200, "Edit Product"),
    ("/sales/add", 200, "Record Sale Transaction"),
    ("/restock/add", 200, "Record Inbound Restock"),
    # Filters & Pagination
    ("/products?search=Action", 200, "Action Figure"),
    ("/inventory?status=LOW+STOCK", 200, "LOW STOCK"),
    ("/sales?page=2", 200, "Sales History"),
    ("/restock?page=1", 200, "Inventory Restocking History"),
    ("/analytics?preset=30d", 200, "Product Movement Analytics"),
    ("/recommendations?priority=MEDIUM", 200, "Colorbuds"),
    ("/reports?tab=sales", 200, "Daily Sales Summary Report"),
    # Static Assets
    ("/static/css/style.css", 200, ":root"),
    ("/static/js/main.js", 200, "DOMContentLoaded"),
    ("/static/js/dashboard.js", 200, "DOMContentLoaded"),
    ("/static/vendor/chart.umd.min.js", 200, "Chart"),
]

def run_route_tests():
    print("=" * 68)
    print("STARTING FULL APPLICATION ROUTE & PRESENTATION VALIDATION")
    print("=" * 68)

    passed = 0
    total = len(ROUTES_TO_TEST) + 1  # plus 404 test

    for path, exp_code, exp_text in ROUTES_TO_TEST:
        url = f"{BASE_URL}{path}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "RouteValidator/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                code = resp.status
                body = resp.read().decode("utf-8", errors="replace")
                assert code == exp_code, f"Status code mismatch for {path}: expected {exp_code}, got {code}"
                assert exp_text in body, f"Expected text '{exp_text}' missing in {path} (body len {len(body)})"
                passed += 1
                print(f"PASS [{code}] {path:<38} -> found '{exp_text}' ({len(body):,} bytes)")
        except Exception as e:
            print(f"FAIL {path}: {e}")
            sys.exit(1)

    # Test Custom 404 handler
    path_404 = "/nonexistent_page_for_404_test"
    try:
        req = urllib.request.Request(f"{BASE_URL}{path_404}", headers={"User-Agent": "RouteValidator/1.0"})
        urllib.request.urlopen(req, timeout=10)
        print("FAIL: 404 route unexpectedly returned 200")
        sys.exit(1)
    except urllib.error.HTTPError as err:
        assert err.code == 404, f"Expected 404, got {err.code}"
        body_404 = err.read().decode("utf-8", errors="replace")
        assert "404" in body_404 or "Page Not Found" in body_404 or "not found" in body_404.lower(), "404 page content missing expected text"
        passed += 1
        print(f"PASS [404] {path_404:<38} -> custom 404 page returned ({len(body_404):,} bytes)")

    print("=" * 68)
    print(f"ALL {passed}/{total} APPLICATION ROUTES & ASSETS VERIFIED SUCCESSFULLY!")
    print("=" * 68)

if __name__ == "__main__":
    run_route_tests()
