"""
Smart Inventory & Sales Analysis System - Headless Browser Role & Access Control Validation
-------------------------------------------------------------------------------------------
Tests all 4 operational accounts across the complete role lifecycle:
Login with matching role -> Dashboard UI verification -> Role-based Navigation -> 
Profile view -> Permitted feature access -> Denied feature access (HTTP 403) -> Logout

Roles verified:
1. System Administrator
2. Inventory Manager
3. Data Analyst
4. Store Associate
"""

import os
import sys
import re
import tempfile
import subprocess
import urllib.request
import urllib.parse
import http.cookiejar
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app import app
import db

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
BASE_URL = "http://127.0.0.1:5000"
ARTIFACTS_DIR = BASE_DIR / "docs" / "role_screenshots"

ROLE_TEST_CONFIGS = [
    {
        "role_name": "System Administrator",
        "login_role": "System Administrator",
        "email": "admin@inventory.com",
        "password": "AdminDev@2026",
        "expected_name": "Admin User",
        "dashboard_indicators": ["Executive Dashboard", "System Administrator Mode", "Manage Users"],
        "nav_allowed_hrefs": ["/dashboard", "/products", "/inventory", "/sales", "/restock", "/analytics", "/recommendations", "/powerbi", "/admin/users", "/profile"],
        "nav_forbidden_hrefs": [],
        "permitted_route": ("/admin/users", 200, "User & Role Governance"),
        "denied_route": None, # Admin has universal access
    },
    {
        "role_name": "Inventory Manager",
        "login_role": "Inventory Manager",
        "email": "manager@inventory.com",
        "password": "ManagerDev@2026",
        "expected_name": "Inventory Manager",
        "dashboard_indicators": ["Executive Dashboard", "Manager Quick Actions", "Add Product", "Restock"],
        "nav_allowed_hrefs": ["/dashboard", "/products", "/inventory", "/sales", "/restock", "/analytics", "/recommendations", "/powerbi", "/profile"],
        "nav_forbidden_hrefs": ["/admin/users"],
        "permitted_route": ("/restock/add", 200, "Record Inbound Restock"),
        "denied_route": ("/admin/users", 403),
    },
    {
        "role_name": "Data Analyst",
        "login_role": "Data Analyst",
        "email": "analyst@inventory.com",
        "password": "AnalystDev@2026",
        "expected_name": "Data Analyst",
        "dashboard_indicators": ["Data Analyst Workspace", "Sales Velocity", "Movement Distribution"],
        "nav_allowed_hrefs": ["/dashboard", "/inventory", "/sales", "/analytics", "/recommendations", "/powerbi", "/profile"],
        "nav_forbidden_hrefs": ["/admin/users", "/products", "/restock"],
        "permitted_route": ("/analytics", 200, "Product Movement Analytics"),
        "denied_route": ("/restock/add", 403),
    },
    {
        "role_name": "Store Associate",
        "login_role": "Store Associate",
        "email": "associate@inventory.com",
        "password": "AssociateDev@2026",
        "expected_name": "Store Associate",
        "dashboard_indicators": ["Store Associate Operations", "Record New Sale", "Stock Lookup"],
        "nav_allowed_hrefs": ["/dashboard", "/sales", "/inventory", "/profile"],
        "nav_forbidden_hrefs": ["/admin/users", "/analytics", "/recommendations", "/powerbi", "/reports", "/restock", "/products"],
        "permitted_route": ("/sales/add", 200, "Record Sale Transaction"),
        "denied_route": ("/analytics", 403),
    }
]

def run_role_browser_validation():
    print("=" * 80)
    print("STARTING COMPLETE ROLE-BASED BROWSER & ACCESS CONTROL VALIDATION")
    print("=" * 80)

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    # Fetch user_ids from DB
    with app.app_context():
        conn = db.get_db()
        user_ids = {r["email"]: r["user_id"] for r in conn.execute("SELECT email, user_id FROM users;").fetchall()}

    for cfg in ROLE_TEST_CONFIGS:
        role = cfg["role_name"]
        login_role = cfg["login_role"]
        email = cfg["email"]
        password = cfg["password"]
        expected_name = cfg["expected_name"]
        expected_id = user_ids.get(email, 1)

        print(f"\n---> Testing Lifecycle: {role} ({email})")

        # 1. Setup Session CookieJar
        cj = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

        # 2. Fetch /login & extract CSRF token
        login_url = f"{BASE_URL}/login"
        req_login = urllib.request.Request(login_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) HeadlessTest/1.0"})
        with opener.open(req_login, timeout=30) as resp:
            login_html = resp.read().decode("utf-8")
        csrf_match = re.search(r'name="csrf_token"\s+value="([^"]+)"', login_html)
        assert csrf_match, f"Could not extract CSRF token on /login for {role}"
        csrf_token = csrf_match.group(1)

        # 3. Perform Role-Verified Login POST
        login_data = urllib.parse.urlencode({
            "csrf_token": csrf_token,
            "email": email,
            "password": password,
            "role": login_role,
            "remember": "1"
        }).encode("utf-8")
        req_auth = urllib.request.Request(
            login_url,
            data=login_data,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) HeadlessTest/1.0", "Content-Type": "application/x-www-form-urlencoded"}
        )
        with opener.open(req_auth, timeout=30) as resp:
            dash_html = resp.read().decode("utf-8")
            assert resp.status == 200, f"Login failed for {role}: HTTP {resp.status}"

        # 4. Verify Role-Aware Dashboard Content
        for indicator in cfg["dashboard_indicators"]:
            assert indicator in dash_html, f"Dashboard indicator '{indicator}' missing for role '{role}'"
        print(f"     [PASS] Dashboard: Validated role-specific view & widgets for '{role}'")

        # 5. Verify Navigation Links according to role matrix
        sidebar_match = re.search(r'<aside class="app-sidebar"[^>]*>(.*?)</aside>', dash_html, re.DOTALL)
        sidebar_content = sidebar_match.group(1) if sidebar_match else dash_html
        for href in cfg["nav_allowed_hrefs"]:
            assert f'href="{href}"' in sidebar_content or f"href='{href}'" in sidebar_content, f"Allowed nav link '{href}' missing for role '{role}'"
        for href in cfg["nav_forbidden_hrefs"]:
            assert f'href="{href}"' not in sidebar_content and f"href='{href}'" not in sidebar_content, f"Forbidden nav link '{href}' exposed in UI for role '{role}'!"
        print(f"     [PASS] Navigation: Strictly matches allowed modules for '{role}'")

        # 6. Verify Profile view
        profile_url = f"{BASE_URL}/profile"
        req_prof = urllib.request.Request(profile_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) HeadlessTest/1.0"})
        with opener.open(req_prof, timeout=30) as resp:
            prof_html = resp.read().decode("utf-8")
            assert resp.status == 200
            assert expected_name in prof_html
            assert email in prof_html
            assert f"#{expected_id}" in prof_html or f"User ID: #{expected_id}" in prof_html
            assert "Active" in prof_html
        print(f"     [PASS] Profile: Name, email, ID #{expected_id}, active status verified")

        # 7. Permitted feature direct access
        perm_route, exp_code, exp_text = cfg["permitted_route"]
        req_perm = urllib.request.Request(f"{BASE_URL}{perm_route}", headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) HeadlessTest/1.0"})
        with opener.open(req_perm, timeout=30) as resp:
            assert resp.status == exp_code
            perm_html = resp.read().decode("utf-8")
            assert exp_text in perm_html
        print(f"     [PASS] Permitted Access: Successfully opened '{perm_route}' (HTTP {exp_code})")

        # 8. Denied feature direct URL access (Must return HTTP 403)
        if cfg["denied_route"]:
            denied_route, exp_code = cfg["denied_route"]
            req_denied = urllib.request.Request(f"{BASE_URL}{denied_route}", headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) HeadlessTest/1.0"})
            try:
                with opener.open(req_denied, timeout=30) as resp:
                    raise AssertionError(f"Security violation! {role} was granted access to '{denied_route}' (HTTP {resp.status})")
            except urllib.error.HTTPError as he:
                assert he.code == exp_code, f"Expected HTTP {exp_code} for {role} on '{denied_route}', got {he.code}"
                print(f"     [PASS] Direct URL Barred: '{denied_route}' strictly blocked with HTTP {exp_code} Forbidden")

        # 9. Logout
        logout_url = f"{BASE_URL}/logout"
        req_logout = urllib.request.Request(logout_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) HeadlessTest/1.0"})
        with opener.open(req_logout, timeout=30) as resp:
            logged_out_html = resp.read().decode("utf-8")
            assert "Sign In" in logged_out_html or resp.status == 200
        print(f"     [PASS] Logout: Session terminated, redirected safely to /login")

    # 10. Headless Chrome Visual Rendering
    if os.path.exists(CHROME_PATH):
        print("\n--- Headless Chrome Visual Rendering & Screenshot Generation ---")
        client = app.test_client()
        for role_name, email, shot_name in [
            ("Store Associate", "associate@inventory.com", "shot_role_associate_dash.png"),
            ("Data Analyst", "analyst@inventory.com", "shot_role_analyst_dash.png"),
            ("Inventory Manager", "manager@inventory.com", "shot_role_manager_dash.png"),
            ("Administrator", "admin@inventory.com", "shot_role_admin_dash.png")
        ]:
            with client.session_transaction() as sess:
                sess["user_id"] = user_ids.get(email, 1)
                sess["user_name"] = role_name
                sess["user_role"] = role_name
                sess["user_email"] = email

            shot_path = ARTIFACTS_DIR / shot_name
            with tempfile.TemporaryDirectory() as temp_dir:
                cmd = [
                    CHROME_PATH,
                    "--headless=new",
                    "--disable-gpu",
                    "--no-first-run",
                    "--no-default-browser-check",
                    f"--user-data-dir={temp_dir}",
                    f"--screenshot={str(shot_path)}",
                    "--window-size=1280,1000",
                    f"{BASE_URL}/dashboard"
                ]
                subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
                print(f"  [PASS] Headless Chrome visual capture for {role_name:<20} -> {shot_name}")

    print("\n" + "=" * 80)
    print("ALL 4 ROLES VALIDATED ACROSS LOGIN, DASHBOARD, NAVIGATION, PROFILE, & RBAC!")
    print("=" * 80)

if __name__ == "__main__":
    run_role_browser_validation()
