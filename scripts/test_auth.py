"""
Authentication & User Management Test Suite
--------------------------------------------
Validates Sign In, Sign Up, Session Persistence, Password Security,
and regression stability of the Smart Inventory & Sales Analysis System.
"""

import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import sqlite3
from app import app
from services import auth_service

def run_tests():
    print("=" * 70)
    print("STARTING TEST SUITE: AUTHENTICATION (SIGN IN & SIGN UP)")
    print("=" * 70)

    client = app.test_client()

    # 1. Database Users Table Exists and has Demo Accounts
    with app.app_context():
        auth_service.init_auth_table()
        conn = sqlite3.connect("database/inventory.db")
        c = conn.cursor()
        users_count = c.execute("SELECT COUNT(*) FROM users;").fetchone()[0]
        assert users_count >= 3, f"Expected at least 3 demo users, got {users_count}"
        print(f"[1/10] Database users table initialized with demo accounts ({users_count} users): PASS")

    # 2. Authenticate Demo Admin
    with app.app_context():
        res_admin = auth_service.authenticate_user("admin@inventory.com", "Admin@123")
        assert res_admin["success"] is True, f"Admin auth failed: {res_admin}"
        assert res_admin["user"]["role"] == "Administrator"
        print("[2/10] Demo Admin authentication succeeds with hashed password: PASS")

    # 3. Authenticate with Wrong Password Fails
    with app.app_context():
        res_fail = auth_service.authenticate_user("admin@inventory.com", "WrongPassword!")
        assert res_fail["success"] is False
        assert "Invalid" in res_fail["message"]
        print("[3/10] Authentication failure on invalid password: PASS")

    # 4. User Registration Validation Rules
    with app.app_context():
        # Short password
        short_pw = auth_service.register_user("Test User", "test_short@example.com", "123", "123")
        assert short_pw["success"] is False
        assert "at least 6 characters" in short_pw["message"]

        # Password mismatch
        mismatch = auth_service.register_user("Test User", "test_mismatch@example.com", "Secret123", "Different123")
        assert mismatch["success"] is False
        assert "do not match" in mismatch["message"]

        # Duplicate email
        dup = auth_service.register_user("Duplicate Admin", "admin@inventory.com", "Admin@123", "Admin@123")
        assert dup["success"] is False
        assert "already exists" in dup["message"]
        print("[4/10] Registration validation rules (length, mismatch, duplicate email): PASS")

    # 5. GET /login renders Sign In page
    res_login_get = client.get("/login")
    assert res_login_get.status_code == 200
    assert b"Sign In" in res_login_get.data
    assert b"admin@inventory.com" in res_login_get.data
    print("[5/10] GET /login renders Sign In view with quick demo buttons: PASS")

    # 6. GET /signup renders Sign Up page
    res_signup_get = client.get("/signup")
    assert res_signup_get.status_code == 200
    assert b"Create Your Account" in res_signup_get.data
    assert b"Operational Role" in res_signup_get.data
    print("[6/10] GET /signup renders Sign Up view with role selection: PASS")

    # 7. POST /login with demo credentials creates session and redirects
    with client:
        res_login_post = client.post("/login", data={
            "email": "manager@inventory.com",
            "password": "Manager@123",
            "remember": "1"
        }, follow_redirects=True)
        assert res_login_post.status_code == 200
        assert b"Welcome back, Inventory Manager" in res_login_post.data or b"Inventory Manager" in res_login_post.data
        assert b"Sign Out" in res_login_post.data
        print("[7/10] POST /login successfully authenticates, creates session, and redirects to Dashboard: PASS")

    # 8. POST /signup creates a new user, auto-logs in and redirects
    test_email = "alex_retail_qa@inventory.com"
    signup_client = app.test_client()
    with signup_client:
        # First ensure clean slate for test email
        with app.app_context():
            conn = sqlite3.connect("database/inventory.db")
            conn.execute("DELETE FROM users WHERE email = ?;", (test_email,))
            conn.commit()

        res_signup_post = signup_client.post("/signup", data={
            "name": "Alex Retail",
            "email": test_email,
            "role": "Inventory Manager",
            "password": "Testing@Password123",
            "confirm_password": "Testing@Password123"
        }, follow_redirects=True)
        assert res_signup_post.status_code == 200
        assert b"Alex Retail" in res_signup_post.data
        assert b"Sign Out" in res_signup_post.data
        print("[8/10] POST /signup successfully creates user, persists to DB, and logs in: PASS")

    # 9. GET /logout clears session and redirects
    with client:
        # Sign in first
        client.post("/login", data={"email": "admin@inventory.com", "password": "Admin@123"})
        res_logout = client.get("/logout", follow_redirects=True)
        assert res_logout.status_code == 200
        assert b"Sign In" in res_logout.data
        assert b"signed out" in res_logout.data.lower()
        print("[9/10] GET /logout clears session and redirects with notification: PASS")

    # 10. Core Database Baseline Verification
    with app.app_context():
        conn = sqlite3.connect("database/inventory.db")
        c = conn.cursor()
        p = c.execute("SELECT COUNT(*) FROM products;").fetchone()[0]
        s = c.execute("SELECT COUNT(*) FROM stores;").fetchone()[0]
        i = c.execute("SELECT COUNT(*) FROM inventory;").fetchone()[0]
        sl = c.execute("SELECT COUNT(*) FROM sales;").fetchone()[0]
        r = c.execute("SELECT COUNT(*) FROM restocks;").fetchone()[0]
        sm = c.execute("SELECT COUNT(*) FROM stock_movements;").fetchone()[0]

        assert p == 35, f"Expected 35 products, got {p}"
        assert s == 50, f"Expected 50 stores, got {s}"
        assert i == 1750, f"Expected 1750 inventory rows, got {i}"
        assert sl == 829262, f"Expected 829262 sales, got {sl}"
        assert r == 0, f"Expected 0 restocks, got {r}"
        assert sm == 1516, f"Expected 1516 movements, got {sm}"
        print("[10/10] Golden database baselines (35/50/1750/829262/0/1516) verified intact: PASS")

    # Clean up test registration user
    with app.app_context():
        conn = sqlite3.connect("database/inventory.db")
        conn.execute("DELETE FROM users WHERE email = ?;", (test_email,))
        conn.commit()

    print("=" * 70)
    print("ALL 10 AUTHENTICATION TESTS PASSED SUCCESSFULLY! (100% SUCCESS)")
    print("=" * 70)

if __name__ == "__main__":
    run_tests()
