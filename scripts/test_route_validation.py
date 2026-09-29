"""
Smart Inventory & Sales Analysis System - Route & Presentation Validator
-------------------------------------------------------------------------
Phase 14 Step 3: Validates all application routes, filters, forms, error pages,
authentication flows, and static assets against the active Flask application.
"""

import urllib.request
import urllib.parse
import urllib.error
import http.cookiejar
import re
import os
import sys

BASE_URL = "http://127.0.0.1:5000"

# Routes accessible when unauthenticated
PUBLIC_ROUTES = [
    ("/login", 200, "Sign In"),
    ("/signup", 200, "Create Your Account"),
]

# Routes requiring authenticated session
AUTHENTICATED_ROUTES = [
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
    # Role Governance (Administrator)
    ("/admin/users", 200, "User & Role Governance"),
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
    total = len(PUBLIC_ROUTES) + 1 + len(AUTHENTICATED_ROUTES) + 1  # public + unauth check + auth + 404

    # Setup CookieJar for session handling
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    urllib.request.install_opener(opener)

    # 1. Test Public Routes (Unauthenticated)
    for path, exp_code, exp_text in PUBLIC_ROUTES:
        url = f"{BASE_URL}{path}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "RouteValidator/1.0"})
            with opener.open(req, timeout=30) as resp:
                code = resp.status
                body = resp.read().decode("utf-8", errors="replace")
                assert code == exp_code, f"Status code mismatch for {path}: expected {exp_code}, got {code}"
                assert exp_text in body, f"Expected text '{exp_text}' missing in {path} (body len {len(body)})"
                passed += 1
                print(f"PASS [{code}] {path:<38} -> found '{exp_text}' ({len(body):,} bytes)")
        except Exception as e:
            print(f"FAIL {path}: {e}")
            sys.exit(1)

    # 2. Verify Unauthenticated Request to Protected Route Redirects to /login
    class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
        def http_error_302(self, req, fp, code, msg, headers):
            return fp

    no_redirect_opener = urllib.request.build_opener(NoRedirectHandler)
    url_dash = f"{BASE_URL}/dashboard"
    req_dash = urllib.request.Request(url_dash, headers={"User-Agent": "RouteValidator/1.0"})
    res_dash = no_redirect_opener.open(req_dash, timeout=30)
    assert res_dash.code in (302, 303), f"Expected redirect 302, got {res_dash.code}"
    loc = res_dash.headers.get("Location", "")
    assert "/login" in loc, f"Expected redirect to /login, got {loc}"
    passed += 1
    print(f"PASS [302] /dashboard (unauthenticated)           -> redirects to /login safely")

    # 3. Authenticate via Login POST with CSRF Token
    login_url = f"{BASE_URL}/login"
    req_login_page = urllib.request.Request(login_url, headers={"User-Agent": "RouteValidator/1.0"})
    with opener.open(req_login_page, timeout=30) as resp:
        login_html = resp.read().decode("utf-8")

    csrf_match = re.search(r'name="csrf_token"\s+value="([^"]+)"', login_html)
    assert csrf_match, "Could not extract CSRF token from /login page!"
    csrf_token = csrf_match.group(1)

    admin_pw = os.environ.get("DEMO_ADMIN_PASSWORD", "AdminDev@2026")
    login_data = urllib.parse.urlencode({
        "csrf_token": csrf_token,
        "email": "admin@inventory.com",
        "password": admin_pw,
        "remember": "1"
    }).encode("utf-8")

    login_req = urllib.request.Request(
        login_url,
        data=login_data,
        headers={"User-Agent": "RouteValidator/1.0", "Content-Type": "application/x-www-form-urlencoded"}
    )
    with opener.open(login_req, timeout=30) as resp:
        assert resp.status == 200, f"Login POST failed with status {resp.status}"
        login_resp_body = resp.read().decode("utf-8", errors="replace")
        assert "Sign Out" in login_resp_body or "Administrator" in login_resp_body
        print("PASS [200] Authenticated successfully as System Administrator (session cookie saved)")

    # 4. Test Authenticated Routes
    for path, exp_code, exp_text in AUTHENTICATED_ROUTES:
        url = f"{BASE_URL}{path}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "RouteValidator/1.0"})
            with opener.open(req, timeout=30) as resp:
                code = resp.status
                body = resp.read().decode("utf-8", errors="replace")
                assert code == exp_code, f"Status code mismatch for {path}: expected {exp_code}, got {code}"
                assert exp_text in body or exp_text.replace("&", "&amp;") in body, f"Expected text '{exp_text}' missing in {path} (body len {len(body)})"
                passed += 1
                print(f"PASS [{code}] {path:<38} -> found '{exp_text}' ({len(body):,} bytes)")
        except Exception as e:
            print(f"FAIL {path}: {e}")
            sys.exit(1)

    # 5. Test Custom 404 handler
    path_404 = "/nonexistent_page_for_404_test"
    try:
        req = urllib.request.Request(f"{BASE_URL}{path_404}", headers={"User-Agent": "RouteValidator/1.0"})
        opener.open(req, timeout=10)
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
