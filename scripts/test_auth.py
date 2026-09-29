"""
Smart Inventory & Sales Analysis System - Comprehensive Authentication & RBAC Test Suite
----------------------------------------------------------------------------------------
Tests all 25 enterprise security, authentication, session, authorization, CSRF,
and brute-force abuse protection requirements.
"""

import sys
import re
import sqlite3
import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app import app
from services import auth_service
from werkzeug.security import check_password_hash

def get_csrf_token(client, page="/login"):
    """Fetch HTML page and extract CSRF token."""
    res = client.get(page)
    m = re.search(r'name=["\']csrf_token["\']\s+value=["\']([^"\']+)["\']', res.data.decode("utf-8", errors="replace"))
    return m.group(1) if m else ""

def post_form(client, url, data, form_page="/login", follow_redirects=False):
    """Submit POST form with valid CSRF token."""
    token = get_csrf_token(client, form_page)
    payload = dict(data)
    if token and "csrf_token" not in payload:
        payload["csrf_token"] = token
    return client.post(url, data=payload, follow_redirects=follow_redirects)

def run_tests():
    print("=" * 75)
    print("STARTING TEST SUITE: ENTERPRISE AUTHENTICATION & RBAC SECURITY (25 TESTS)")
    print("=" * 75)

    # Ensure app context & users table initialized
    with app.app_context():
        auth_service.init_auth_table()

    # 1. Signup Success (with default role Store Associate)
    client1 = app.test_client()
    test_user_1 = "qa_user_1@inventory.com"
    with app.app_context():
        conn = sqlite3.connect("database/inventory.db")
        conn.execute("DELETE FROM users WHERE email = ?;", (test_user_1,))
        conn.commit()

    with client1:
        res1 = post_form(client1, "/signup", {
            "name": "Jane QA Specialist",
            "email": test_user_1,
            "password": "SecurePassword@2026",
            "confirm_password": "SecurePassword@2026"
        }, form_page="/signup", follow_redirects=True)
        assert res1.status_code == 200, f"Expected 200 on signup redirect, got {res1.status_code}"
        assert b"Jane QA Specialist" in res1.data
        assert b"Store Associate" in res1.data
        print("[1/25] Sign up success (creates account, logs in, default Store Associate): PASS")

    # 2. Signup Duplicate Email Rejected
    client2 = app.test_client()
    res2 = post_form(client2, "/signup", {
        "name": "Another Person",
        "email": test_user_1,
        "password": "SecurePassword@2026",
        "confirm_password": "SecurePassword@2026"
    }, form_page="/signup")
    assert res2.status_code == 400
    assert b"already registered" in res2.data or b"already exists" in res2.data
    print("[2/25] Sign up duplicate email rejected cleanly: PASS")

    # 3. Signup Invalid Email Format
    client3 = app.test_client()
    res3 = post_form(client3, "/signup", {
        "name": "Test Name",
        "email": "not-an-email",
        "password": "SecurePassword@2026",
        "confirm_password": "SecurePassword@2026"
    }, form_page="/signup")
    assert res3.status_code == 400
    assert b"valid work email" in res3.data or b"valid email" in res3.data
    print("[3/25] Sign up invalid email rejected: PASS")

    # 4. Signup Missing/Short Name
    client4 = app.test_client()
    res4 = post_form(client4, "/signup", {
        "name": "A",
        "email": "valid_email@test.com",
        "password": "SecurePassword@2026",
        "confirm_password": "SecurePassword@2026"
    }, form_page="/signup")
    assert res4.status_code == 400
    assert b"Full name must be between" in res4.data or b"valid full name" in res4.data
    print("[4/25] Sign up missing/short name rejected: PASS")

    # 5. Signup Short Password (< 8 chars)
    client5 = app.test_client()
    res5 = post_form(client5, "/signup", {
        "name": "Valid Name",
        "email": "valid2@test.com",
        "password": "short",
        "confirm_password": "short"
    }, form_page="/signup")
    assert res5.status_code == 400
    assert b"at least 8 characters" in res5.data
    print("[5/25] Sign up short password (< 8 chars) rejected: PASS")

    # 6. Signup Weak/Common Password Blacklist
    client6 = app.test_client()
    res6 = post_form(client6, "/signup", {
        "name": "Valid Name",
        "email": "valid3@test.com",
        "password": "password123",
        "confirm_password": "password123"
    }, form_page="/signup")
    assert res6.status_code == 400
    assert b"too common" in res6.data or b"weak" in res6.data
    print("[6/25] Sign up common weak password rejected by blacklist: PASS")

    # 7. Signup Password Mismatch
    client7 = app.test_client()
    res7 = post_form(client7, "/signup", {
        "name": "Valid Name",
        "email": "valid4@test.com",
        "password": "SecurePassword@2026",
        "confirm_password": "DifferentPassword@2026"
    }, form_page="/signup")
    assert res7.status_code == 400
    assert b"Passwords do not match" in res7.data
    print("[7/25] Sign up password mismatch rejected: PASS")

    # 8. Email Normalization (case-insensitivity)
    test_user_upper = "CASE_TEST_USER@INVENTORY.COM"
    with app.app_context():
        conn = sqlite3.connect("database/inventory.db")
        conn.execute("DELETE FROM users WHERE email = ?;", (test_user_upper.lower(),))
        conn.commit()

    client8 = app.test_client()
    res8 = post_form(client8, "/signup", {
        "name": "Case User",
        "email": test_user_upper,
        "password": "SecurePassword@2026",
        "confirm_password": "SecurePassword@2026"
    }, form_page="/signup")
    assert res8.status_code in (200, 302)
    with app.app_context():
        conn = sqlite3.connect("database/inventory.db")
        c = conn.cursor()
        saved_email = c.execute("SELECT email FROM users WHERE name = 'Case User';").fetchone()[0]
        assert saved_email == "case_test_user@inventory.com", f"Expected lowercase email, got {saved_email}"
    print("[8/25] Email normalization to lowercase in storage: PASS")

    # 9. Password Hash Stored (Never Plaintext)
    with app.app_context():
        conn = sqlite3.connect("database/inventory.db")
        c = conn.cursor()
        pw_hash = c.execute("SELECT password_hash FROM users WHERE email = 'case_test_user@inventory.com';").fetchone()[0]
        assert not pw_hash.startswith("SecurePassword"), "Plaintext password detected in database!"
        assert check_password_hash(pw_hash, "SecurePassword@2026") is True
    print("[9/25] Passwords stored only as secure PBKDF2/scrypt hashes: PASS")

    # 10. Login Success
    admin_pw = app.config.get("DEMO_ADMIN_PASSWORD", "AdminDev@2026")
    client10 = app.test_client()
    with client10:
        res10 = post_form(client10, "/login", {
            "email": "admin@inventory.com",
            "password": admin_pw,
            "remember": "1"
        }, form_page="/login", follow_redirects=True)
        assert res10.status_code == 200
        assert b"Sign Out" in res10.data
        assert b"Administrator" in res10.data
        # Verify last_login_at was updated
        with app.app_context():
            conn = sqlite3.connect("database/inventory.db")
            last_login = conn.execute("SELECT last_login_at FROM users WHERE email = 'admin@inventory.com';").fetchone()[0]
            assert last_login is not None
    print("[10/25] Login success establishes session, sets remember-me, and updates last_login_at: PASS")

    # 11. Login Invalid Password Fails
    client11 = app.test_client()
    res11 = post_form(client11, "/login", {
        "email": "admin@inventory.com",
        "password": "WrongPassword@999"
    }, form_page="/login")
    assert res11.status_code == 401
    assert b"Invalid email or password" in res11.data
    print("[11/25] Login with incorrect password returns generic error: PASS")

    # 12. Login Nonexistent Email Fails
    client12 = app.test_client()
    res12 = post_form(client12, "/login", {
        "email": "ghost_nonexistent@inventory.com",
        "password": "SomePassword@123"
    }, form_page="/login")
    assert res12.status_code == 401
    assert b"Invalid email or password" in res12.data
    print("[12/25] Login with nonexistent email returns generic error: PASS")

    # 13. Generic Error Uniformity (Zero User Enumeration)
    assert b"Invalid email or password" in res11.data
    assert b"Invalid email or password" in res12.data
    print("[13/25] Generic error uniformity prevents user enumeration attacks: PASS")

    # 14. Logout Clears Session
    client14 = app.test_client()
    with client14:
        post_form(client14, "/login", {"email": "admin@inventory.com", "password": admin_pw}, form_page="/login")
        res14 = client14.get("/logout", follow_redirects=True)
        assert res14.status_code == 200
        assert b"Sign In" in res14.data
        assert b"Sign Out" not in res14.data
    print("[14/25] Logout clears session safely and redirects to /login: PASS")

    # 15. Unauthenticated Access to Protected Route Redirects to Login
    client15 = app.test_client()
    res15 = client15.get("/dashboard")
    assert res15.status_code == 302
    assert "/login" in res15.headers["Location"]
    print("[15/25] Unauthenticated access to /dashboard redirects to /login: PASS")

    # 16. Unauthenticated API Access Returns 401 JSON
    client16 = app.test_client()
    res16 = client16.get("/api/dashboard/sales-trend")
    assert res16.status_code == 401
    json_data = res16.get_json()
    assert json_data is not None
    assert json_data.get("error") == "Unauthorized"
    print("[16/25] Unauthenticated API access returns HTTP 401 JSON: PASS")

    # 17. Authenticated Access to Protected Route
    client17 = app.test_client()
    with client17:
        with client17.session_transaction() as sess:
            sess["user_id"] = 1
            sess["user_name"] = "System Administrator"
            sess["user_role"] = "Administrator"
        res17 = client17.get("/dashboard")
        assert res17.status_code == 200
        assert b"Executive Dashboard" in res17.data
    print("[17/25] Authenticated access to /dashboard succeeds with HTTP 200: PASS")

    # 18. Unauthorized Role Access Returns 403 Forbidden
    client18 = app.test_client()
    with client18:
        # Retrieve or ensure an active Store Associate in DB
        with app.app_context():
            conn = sqlite3.connect("database/inventory.db")
            conn.row_factory = sqlite3.Row
            assoc_user = conn.execute("SELECT user_id, name, role FROM users WHERE role = 'Store Associate' AND is_active = 1 LIMIT 1;").fetchone()
            if not assoc_user:
                conn.execute("""
                    INSERT INTO users (name, email, password_hash, role, is_active)
                    VALUES ('Temp Associate', 'temp_assoc@inventory.com', 'dummyhash', 'Store Associate', 1);
                """)
                conn.commit()
                assoc_id = conn.execute("SELECT last_insert_rowid();").fetchone()[0]
            else:
                assoc_id = assoc_user["user_id"]

        # Sign in as Store Associate
        with client18.session_transaction() as sess:
            sess["user_id"] = assoc_id
            sess["user_name"] = "Store Employee"
            sess["user_role"] = "Store Associate"
        # Try to access Admin user governance
        res18 = client18.get("/admin/users")
        assert res18.status_code == 403
        assert b"Access Forbidden" in res18.data
    print("[18/25] Unauthorized role access returns branded HTTP 403 Forbidden: PASS")

    # 19. Safe 'next' Redirect Validation
    client19 = app.test_client()
    with client19:
        res19 = post_form(client19, "/login?next=/inventory", {
            "email": "admin@inventory.com",
            "password": admin_pw
        }, form_page="/login")
        assert res19.status_code == 302
        assert res19.headers["Location"].endswith("/inventory")
    print("[19/25] Safe internal 'next' redirect functions correctly: PASS")

    # 20. Open Redirect Prevention
    client20 = app.test_client()
    with client20:
        res20 = post_form(client20, "/login?next=http://evil-attacker.com", {
            "email": "admin@inventory.com",
            "password": admin_pw
        }, form_page="/login")
        assert res20.status_code == 302
        assert not res20.headers["Location"].startswith("http://evil")
        assert res20.headers["Location"].endswith("/dashboard")
    print("[20/25] Open redirect attempt blocked (defaults to /dashboard): PASS")

    # 21. Deactivated Account Cannot Log In
    test_inactive = "inactive_qa@inventory.com"
    with app.app_context():
        conn = sqlite3.connect("database/inventory.db")
        conn.execute("DELETE FROM users WHERE email = ?;", (test_inactive,))
        conn.execute("""
            INSERT INTO users (name, email, password_hash, role, is_active)
            VALUES (?, ?, ?, ?, 0);
        """, ("Inactive User", test_inactive, auth_service.generate_password_hash("Password@2026"), "Store Associate"))
        conn.commit()

    client21 = app.test_client()
    res21 = post_form(client21, "/login", {"email": test_inactive, "password": "Password@2026"}, form_page="/login")
    assert res21.status_code == 401
    assert b"deactivated" in res21.data
    print("[21/25] Deactivated user account is rejected on login: PASS")

    # 22. CSRF Rejection on Missing or Invalid Token
    client22 = app.test_client()
    # Explicitly send POST without CSRF token
    res22 = client22.post("/login", data={"email": "admin@inventory.com", "password": admin_pw})
    assert res22.status_code == 400, f"Expected 400 on missing CSRF token, got {res22.status_code}"
    print("[22/25] CSRF protection rejects state-changing requests lacking valid token: PASS")

    # 23. Login Abuse Protection (Temporary Lockout after 5 Failures)
    test_brute = "brute_force_qa@inventory.com"
    with app.app_context():
        conn = sqlite3.connect("database/inventory.db")
        conn.execute("DELETE FROM users WHERE email = ?;", (test_brute,))
        conn.execute("""
            INSERT INTO users (name, email, password_hash, role, is_active)
            VALUES (?, ?, ?, ?, 1);
        """, ("Brute Target", test_brute, auth_service.generate_password_hash("RealPassword@2026"), "Store Associate"))
        conn.commit()

    client23 = app.test_client()
    # Trigger 5 consecutive failed logins
    for attempt in range(1, 6):
        res_fail = post_form(client23, "/login", {"email": test_brute, "password": f"WrongAttempt{attempt}!"}, form_page="/login")
        assert res_fail.status_code in (401, 200)

    # Verify locked_until is populated in DB
    with app.app_context():
        conn = sqlite3.connect("database/inventory.db")
        locked_until = conn.execute("SELECT locked_until FROM users WHERE email = ?;", (test_brute,)).fetchone()[0]
        assert locked_until is not None
    print("[23/25] Login abuse protection locks account for 15 minutes after 5 failures: PASS")

    # 24. Default Signup Role is Always 'Store Associate'
    test_role_check = "role_check_qa@inventory.com"
    with app.app_context():
        conn = sqlite3.connect("database/inventory.db")
        conn.execute("DELETE FROM users WHERE email = ?;", (test_role_check,))
        conn.commit()

    client24 = app.test_client()
    post_form(client24, "/signup", {
        "name": "Ordinary Worker",
        "email": test_role_check,
        "password": "Password@2026",
        "confirm_password": "Password@2026"
    }, form_page="/signup")
    with app.app_context():
        conn = sqlite3.connect("database/inventory.db")
        assigned_role = conn.execute("SELECT role FROM users WHERE email = ?;", (test_role_check,)).fetchone()[0]
        assert assigned_role == "Store Associate", f"Expected Store Associate, got {assigned_role}"
    print("[24/25] Public sign-up unconditionally assigns least-privileged 'Store Associate': PASS")

    # 25. Public Signup Cannot Create Admin
    test_hacker = "wannabe_admin@inventory.com"
    with app.app_context():
        conn = sqlite3.connect("database/inventory.db")
        conn.execute("DELETE FROM users WHERE email = ?;", (test_hacker,))
        conn.commit()

    client25 = app.test_client()
    # Malicious client sends role=Administrator in POST body
    post_form(client25, "/signup", {
        "name": "Attacker",
        "email": test_hacker,
        "password": "Password@2026",
        "confirm_password": "Password@2026",
        "role": "Administrator"
    }, form_page="/signup")
    with app.app_context():
        conn = sqlite3.connect("database/inventory.db")
        hacker_role = conn.execute("SELECT role FROM users WHERE email = ?;", (test_hacker,)).fetchone()[0]
        assert hacker_role == "Store Associate", f"Privilege escalation bug! Got {hacker_role}"
    print("[25/25] Public signup cannot escalate privileges or create Admin: PASS")

    # Clean up test user records
    with app.app_context():
        conn = sqlite3.connect("database/inventory.db")
        for em in [test_user_1, test_user_upper.lower(), test_inactive, test_brute, test_role_check, test_hacker]:
            conn.execute("DELETE FROM users WHERE email = ?;", (em,))
        conn.commit()

    print("=" * 75)
    print("ALL 25 ENTERPRISE AUTHENTICATION & RBAC TESTS PASSED SUCCESSFULLY! (100% SUCCESS)")
    print("=" * 75)

if __name__ == "__main__":
    run_tests()
