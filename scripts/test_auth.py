"""
Smart Inventory & Sales Analysis System - Comprehensive Authentication & RBAC Test Suite
----------------------------------------------------------------------------------------
Tests all 40 role-based signup, sign-in, session, route authorization, profile immutability,
email validation, and enterprise security requirements.
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
import db

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

def cleanup_temporary_users():
    """Ensure database returns to exact 4 baseline users."""
    with app.app_context():
        conn = db.get_db()
        conn.execute("""
            DELETE FROM users 
            WHERE email NOT IN (
                'admin@inventory.com', 
                'manager@inventory.com', 
                'analyst@inventory.com', 
                'associate@inventory.com'
            );
        """)
        # Reset failed attempts or lockouts on seeded users
        conn.execute("UPDATE users SET failed_login_attempts = 0, locked_until = NULL, is_active = 1;")
        conn.commit()

def run_tests():
    print("=" * 80)
    print("STARTING TEST SUITE: COMPLETE ROLE-BASED AUTH & RBAC ACCESS CONTROL (40 TESTS)")
    print("=" * 80)

    with app.app_context():
        auth_service.init_auth_table()
    cleanup_temporary_users()

    try:
        # 1. Signup with Store Associate
        c1 = app.test_client()
        res1 = post_form(c1, "/signup", {
            "name": "Test Associate User",
            "email": "test_assoc_qa@inventory.com",
            "role": "Store Associate",
            "password": "Password@2026",
            "confirm_password": "Password@2026"
        }, form_page="/signup", follow_redirects=True)
        assert res1.status_code == 200
        with app.app_context():
            conn = db.get_db()
            row1 = conn.execute("SELECT role FROM users WHERE email = 'test_assoc_qa@inventory.com';").fetchone()
            assert row1 and row1["role"] == "Store Associate", f"Expected Store Associate, got {row1['role'] if row1 else None}"
        print("[1/40] Signup with Store Associate: PASS")

        # 2. Signup with Data Analyst
        c2 = app.test_client()
        res2 = post_form(c2, "/signup", {
            "name": "Test Analyst User",
            "email": "test_analyst_qa@inventory.com",
            "role": "Data Analyst",
            "password": "Password@2026",
            "confirm_password": "Password@2026"
        }, form_page="/signup", follow_redirects=True)
        assert res2.status_code == 200
        with app.app_context():
            conn = db.get_db()
            row2 = conn.execute("SELECT role FROM users WHERE email = 'test_analyst_qa@inventory.com';").fetchone()
            assert row2 and row2["role"] == "Data Analyst", f"Expected Data Analyst, got {row2['role'] if row2 else None}"
        print("[2/40] Signup with Data Analyst: PASS")

        # 3. Signup with Inventory Manager
        c3 = app.test_client()
        res3 = post_form(c3, "/signup", {
            "name": "Test Manager User",
            "email": "test_manager_qa@inventory.com",
            "role": "Inventory Manager",
            "password": "Password@2026",
            "confirm_password": "Password@2026"
        }, form_page="/signup", follow_redirects=True)
        assert res3.status_code == 200
        with app.app_context():
            conn = db.get_db()
            row3 = conn.execute("SELECT role FROM users WHERE email = 'test_manager_qa@inventory.com';").fetchone()
            assert row3 and row3["role"] == "Inventory Manager", f"Expected Inventory Manager, got {row3['role'] if row3 else None}"
        print("[3/40] Signup with Inventory Manager: PASS")

        # 4. Admin excluded from public signup
        c4 = app.test_client()
        res4 = post_form(c4, "/signup", {
            "name": "Malicious Admin Candidate",
            "email": "hacker_admin@inventory.com",
            "role": "System Administrator",
            "password": "Password@2026",
            "confirm_password": "Password@2026"
        }, form_page="/signup")
        assert res4.status_code == 400
        with app.app_context():
            conn = db.get_db()
            row4 = conn.execute("SELECT * FROM users WHERE email = 'hacker_admin@inventory.com';").fetchone()
            assert row4 is None, "Administrator account was improperly created in public signup!"
        print("[4/40] Admin strictly excluded from public signup: PASS")

        # 5. Valid email accepted
        valid, msg = auth_service.validate_email_format("ankit@gmail.com")
        assert valid is True and msg is None, f"Expected ankit@gmail.com to be valid, got {msg}"
        print("[5/40] Valid email accepted ('ankit@gmail.com'): PASS")

        # 6. Missing @ rejected
        v6, msg6 = auth_service.validate_email_format("ankitgmail.com")
        assert v6 is False and "valid email" in msg6.lower()
        print("[6/40] Missing @ rejected ('ankitgmail.com'): PASS")

        # 7. Malformed email rejected
        malformed_examples = ["ankit@", "@gmail.com", "ankit @gmail.com", "ankit@gmail", "ankit.com"]
        for bad_email in malformed_examples:
            v7, msg7 = auth_service.validate_email_format(bad_email)
            assert v7 is False, f"Malformed email '{bad_email}' should be rejected!"
            assert "valid email" in msg7.lower()
        print(f"[7/40] All malformed email formats rejected ({len(malformed_examples)} variants): PASS")

        # 8. Email normalized lowercase
        c8 = app.test_client()
        post_form(c8, "/signup", {
            "name": "Case Test User",
            "email": "ANKIT_NORMALIZED@GMAIL.COM",
            "role": "Store Associate",
            "password": "Password@2026",
            "confirm_password": "Password@2026"
        }, form_page="/signup")
        with app.app_context():
            conn = db.get_db()
            row8 = conn.execute("SELECT email FROM users WHERE email = 'ankit_normalized@gmail.com';").fetchone()
            assert row8 is not None, "Email was not normalized to lowercase in storage!"
            assert row8["email"] == "ankit_normalized@gmail.com"
        print("[8/40] Email normalized to lowercase in database: PASS")

        # 9. Duplicate email rejected
        c9 = app.test_client()
        res9 = post_form(c9, "/signup", {
            "name": "Duplicate User",
            "email": "ankit_normalized@gmail.com",
            "role": "Store Associate",
            "password": "Password@2026",
            "confirm_password": "Password@2026"
        }, form_page="/signup")
        assert res9.status_code == 400
        assert b"already registered" in res9.data.lower() or b"already in use" in res9.data.lower()
        print("[9/40] Duplicate email registration rejected: PASS")

        # 10. Login correct credentials
        c10 = app.test_client()
        res10 = post_form(c10, "/login", {
            "email": "manager@inventory.com",
            "password": "ManagerDev@2026",
            "role": "Inventory Manager"
        }, form_page="/login", follow_redirects=True)
        assert res10.status_code == 200
        with c10.session_transaction() as sess10:
            assert sess10.get("user_email") == "manager@inventory.com"
            assert sess10.get("user_role") == "Inventory Manager"
        print("[10/40] Login with correct credentials & role accepted: PASS")

        # 11. Login wrong password rejected
        c11 = app.test_client()
        res11 = post_form(c11, "/login", {
            "email": "manager@inventory.com",
            "password": "IncorrectPassword@2026",
            "role": "Inventory Manager"
        }, form_page="/login")
        assert res11.status_code == 401
        assert b"Invalid email, password, or role." in res11.data
        print("[11/40] Login wrong password rejected with generic error: PASS")

        # 12. Login wrong role rejected
        c12 = app.test_client()
        # manager@inventory.com has stored role Inventory Manager; attacker picks Store Associate
        res12 = post_form(c12, "/login", {
            "email": "manager@inventory.com",
            "password": "ManagerDev@2026",
            "role": "Store Associate"
        }, form_page="/login")
        assert res12.status_code == 401
        assert b"Invalid email, password, or role." in res12.data
        print("[12/40] Login with mismatched role rejected: PASS")

        # 13. Login correct role accepted
        c13 = app.test_client()
        res13 = post_form(c13, "/login", {
            "email": "associate@inventory.com",
            "password": "AssociateDev@2026",
            "role": "Store Associate"
        }, form_page="/login", follow_redirects=True)
        assert res13.status_code == 200
        with c13.session_transaction() as sess13:
            assert sess13.get("user_role") == "Store Associate"
        print("[13/40] Login with matching role accepted: PASS")

        # 14. Unauthenticated dashboard redirects
        c14 = app.test_client()
        res14 = c14.get("/dashboard")
        assert res14.status_code == 302
        assert "/login" in res14.headers.get("Location", "")
        print("[14/40] Unauthenticated dashboard request redirects to /login: PASS")

        # Retrieve actual user_ids for seeded accounts
        with app.app_context():
            conn = db.get_db()
            uid_map = {r["email"]: r["user_id"] for r in conn.execute("SELECT email, user_id FROM users;").fetchall()}
            admin_id = uid_map["admin@inventory.com"]
            manager_id = uid_map["manager@inventory.com"]
            analyst_id = uid_map["analyst@inventory.com"]
            associate_id = uid_map["associate@inventory.com"]

        # 15. Manager dashboard access
        c_mgr = app.test_client()
        with c_mgr.session_transaction() as s:
            s["user_id"] = manager_id
            s["user_name"] = "Inventory Manager"
            s["user_role"] = "Inventory Manager"
            s["user_email"] = "manager@inventory.com"
        res15 = c_mgr.get("/dashboard")
        assert res15.status_code == 200
        assert b"Executive Dashboard" in res15.data or b"Manager Quick Actions" in res15.data
        print("[15/40] Manager dashboard access (200 OK with manager controls): PASS")

        # 16. Analyst dashboard access
        c_anl = app.test_client()
        with c_anl.session_transaction() as s:
            s["user_id"] = analyst_id
            s["user_name"] = "Data Analyst"
            s["user_role"] = "Data Analyst"
            s["user_email"] = "analyst@inventory.com"
        res16 = c_anl.get("/dashboard")
        assert res16.status_code == 200
        assert b"Data Analyst Workspace" in res16.data or b"Sales Velocity" in res16.data
        print("[16/40] Analyst dashboard access (200 OK with analytical view): PASS")

        # 17. Store dashboard access
        c_ast = app.test_client()
        with c_ast.session_transaction() as s:
            s["user_id"] = associate_id
            s["user_name"] = "Store Associate"
            s["user_role"] = "Store Associate"
            s["user_email"] = "associate@inventory.com"
        res17 = c_ast.get("/dashboard")
        assert res17.status_code == 200
        assert b"Store Associate Operations" in res17.data or b"Stock Lookup" in res17.data
        print("[17/40] Store associate dashboard access (200 OK with operational view): PASS")

        # 18. Manager access to inventory
        res18 = c_mgr.get("/inventory")
        assert res18.status_code == 200
        print("[18/40] Manager access to /inventory (200 OK): PASS")

        # 19. Manager access to restock
        res19 = c_mgr.get("/restock")
        assert res19.status_code == 200
        print("[19/40] Manager access to /restock (200 OK): PASS")

        # 20. Manager access to analytics
        res20 = c_mgr.get("/analytics")
        assert res20.status_code == 200
        print("[20/40] Manager access to /analytics (200 OK): PASS")

        # 21. Manager access to recommendations
        res21 = c_mgr.get("/recommendations")
        assert res21.status_code == 200
        print("[21/40] Manager access to /recommendations (200 OK): PASS")

        # 22. Analyst access to analytics
        res22 = c_anl.get("/analytics")
        assert res22.status_code == 200
        print("[22/40] Analyst access to /analytics (200 OK): PASS")

        # 23. Analyst cannot restock
        res23 = c_anl.get("/restock/add")
        assert res23.status_code == 403
        print("[23/40] Analyst cannot access restock operations (403 Forbidden): PASS")

        # 24. Analyst cannot modify products
        res24 = c_anl.get("/products/add")
        assert res24.status_code == 403
        print("[24/40] Analyst cannot modify products (403 Forbidden): PASS")

        # 25. Store associate cannot access analytics
        res25 = c_ast.get("/analytics")
        assert res25.status_code == 403
        print("[25/40] Store Associate cannot access analytics (403 Forbidden): PASS")

        # 26. Store associate cannot access recommendations
        res26 = c_ast.get("/recommendations")
        assert res26.status_code == 403
        print("[26/40] Store Associate cannot access recommendations (403 Forbidden): PASS")

        # 27. Store associate cannot restock
        res27 = c_ast.get("/restock/add")
        assert res27.status_code == 403
        print("[27/40] Store Associate cannot restock (403 Forbidden): PASS")

        # 28. Manager cannot access admin governance
        res28 = c_mgr.get("/admin/users")
        assert res28.status_code == 403
        print("[28/40] Manager cannot access admin governance (403 Forbidden): PASS")

        # 29. Analyst cannot access admin governance
        res29 = c_anl.get("/admin/users")
        assert res29.status_code == 403
        print("[29/40] Analyst cannot access admin governance (403 Forbidden): PASS")

        # 30. Store associate cannot access admin governance
        res30 = c_ast.get("/admin/users")
        assert res30.status_code == 403
        print("[30/40] Store Associate cannot access admin governance (403 Forbidden): PASS")

        # 31. Admin can access admin governance
        c_adm = app.test_client()
        with c_adm.session_transaction() as s:
            s["user_id"] = admin_id
            s["user_name"] = "System Administrator"
            s["user_role"] = "Administrator"
            s["user_email"] = "admin@inventory.com"
        res31 = c_adm.get("/admin/users")
        assert res31.status_code == 200
        assert b"User &amp; Role Governance" in res31.data or b"User & Role Governance" in res31.data
        print("[31/40] Admin can access admin governance (200 OK): PASS")

        # 32. Profile shows correct role
        for cl, expected_role in [(c_adm, "Administrator"), (c_mgr, "Inventory Manager"), (c_anl, "Data Analyst"), (c_ast, "Store Associate")]:
            resp = cl.get("/profile")
            assert resp.status_code == 200
            assert expected_role.encode("utf-8") in resp.data
        print("[32/40] Profile displays authentic stored role for each account: PASS")

        # 33. Profile role cannot be changed
        res33 = post_form(c_mgr, "/profile/edit", {
            "name": "Hacked Manager",
            "email": "manager@inventory.com",
            "role": "Administrator"
        }, form_page="/profile/edit")
        with app.app_context():
            conn = db.get_db()
            role_chk = conn.execute("SELECT role FROM users WHERE email = 'manager@inventory.com';").fetchone()["role"]
            assert role_chk == "Inventory Manager", f"Privilege escalation bug! Manager changed role to {role_chk}"
            conn.execute("UPDATE users SET name = 'Inventory Manager' WHERE email = 'manager@inventory.com';")
            conn.commit()
        print("[33/40] User cannot modify role via profile update: PASS")

        # 34. CSRF protection
        c34 = app.test_client()
        res34 = c34.post("/login", data={
            "email": "manager@inventory.com",
            "password": "ManagerDev@2026",
            "role": "Inventory Manager"
        })
        assert res34.status_code == 400
        assert b"security token" in res34.data.lower() or b"csrf" in res34.data.lower()
        print("[34/40] CSRF token strictly required on form submissions: PASS")

        # 35. Password hashing verified
        with app.app_context():
            conn = db.get_db()
            hashes = conn.execute("SELECT password_hash FROM users;").fetchall()
            for h in hashes:
                raw_hash = h["password_hash"]
                assert raw_hash.startswith("scrypt:") or raw_hash.startswith("pbkdf2:"), f"Insecure password hash: {raw_hash}"
                assert "Dev@2026" not in raw_hash
        print("[35/40] Passwords stored exclusively as secure cryptographic hashes: PASS")

        # 36. Inactive account rejected
        with app.app_context():
            conn = db.get_db()
            conn.execute("UPDATE users SET is_active = 0 WHERE email = 'associate@inventory.com';")
            conn.commit()
        c36 = app.test_client()
        res36 = post_form(c36, "/login", {
            "email": "associate@inventory.com",
            "password": "AssociateDev@2026",
            "role": "Store Associate"
        }, form_page="/login")
        assert res36.status_code == 401
        assert b"deactivated" in res36.data.lower()
        # Restore active status
        with app.app_context():
            conn = db.get_db()
            conn.execute("UPDATE users SET is_active = 1 WHERE email = 'associate@inventory.com';")
            conn.commit()
        print("[36/40] Deactivated account login rejected: PASS")

        # 37. Account lockout triggered on brute-force attempts
        c37 = app.test_client()
        with app.app_context():
            conn = db.get_db()
            conn.execute("UPDATE users SET failed_login_attempts = 0, locked_until = NULL WHERE email = 'associate@inventory.com';")
            conn.commit()
        for i in range(5):
            res_fail = post_form(c37, "/login", {
                "email": "associate@inventory.com",
                "password": f"WrongAttempt{i}@2026",
                "role": "Store Associate"
            }, form_page="/login")
            assert res_fail.status_code == 401
        assert b"locked" in res_fail.data.lower()
        with app.app_context():
            conn = db.get_db()
            locked_val = conn.execute("SELECT locked_until FROM users WHERE email = 'associate@inventory.com';").fetchone()["locked_until"]
            assert locked_val is not None
            # Reset lockout
            conn.execute("UPDATE users SET failed_login_attempts = 0, locked_until = NULL WHERE email = 'associate@inventory.com';")
            conn.commit()
        print("[37/40] Brute-force account lockout enforced after threshold: PASS")

        # 38. Safe next redirect
        c38 = app.test_client()
        # Safe relative redirect
        res38_safe = post_form(c38, "/login?next=/analytics", {
            "email": "manager@inventory.com",
            "password": "ManagerDev@2026",
            "role": "Inventory Manager"
        }, form_page="/login")
        assert res38_safe.status_code == 302
        assert res38_safe.headers.get("Location") == "/analytics"

        # Evil external redirect
        c38_evil = app.test_client()
        res38_evil = post_form(c38_evil, "/login?next=https://malicious-site.com/steal", {
            "email": "manager@inventory.com",
            "password": "ManagerDev@2026",
            "role": "Inventory Manager"
        }, form_page="/login")
        assert res38_evil.status_code == 302
        assert res38_evil.headers.get("Location") == "/dashboard"
        print("[38/40] Open-redirect attacks prevented with safe URL validation: PASS")

        # 39. IDOR prevention
        c39 = app.test_client()
        with c39.session_transaction() as s:
            s["user_id"] = analyst_id
            s["user_name"] = "Data Analyst"
            s["user_role"] = "Data Analyst"
            s["user_email"] = "analyst@inventory.com"
        # Attempt to modify admin account via forged post
        res39 = post_form(c39, "/profile/edit", {
            "user_id": admin_id,
            "name": "Tampered Admin",
            "email": "hacked_admin@inventory.com"
        }, form_page="/profile/edit")
        with app.app_context():
            conn = db.get_db()
            admin_row = conn.execute("SELECT name, email FROM users WHERE user_id = ?;", (admin_id,)).fetchone()
            assert admin_row["email"] == "admin@inventory.com", "IDOR vulnerability: Admin email was modified!"
            assert admin_row["name"] == "Admin User" or admin_row["name"] == "System Administrator"
        print("[39/40] IDOR strictly prevented; updates bound to session user_id: PASS")

        # 40. User can change own profile
        c40 = app.test_client()
        with c40.session_transaction() as s:
            s["user_id"] = analyst_id
            s["user_name"] = "Data Analyst"
            s["user_role"] = "Data Analyst"
            s["user_email"] = "analyst@inventory.com"
        res40 = post_form(c40, "/profile/edit", {
            "name": "Senior Data Analyst",
            "email": "analyst@inventory.com"
        }, form_page="/profile/edit", follow_redirects=True)
        assert res40.status_code == 200
        with app.app_context():
            conn = db.get_db()
            updated_name = conn.execute("SELECT name FROM users WHERE user_id = ?;", (analyst_id,)).fetchone()["name"]
            assert updated_name == "Senior Data Analyst"
            # Restore baseline name
            conn.execute("UPDATE users SET name = 'Data Analyst' WHERE user_id = ?;", (analyst_id,))
            conn.commit()
        print("[40/40] User can successfully update their own profile details: PASS")

    finally:
        cleanup_temporary_users()

    # Final database baseline verification
    with app.app_context():
        conn = db.get_db()
        user_count = conn.execute("SELECT COUNT(*) FROM users;").fetchone()[0]
        assert user_count == 4, f"Baseline violation! Expected 4 users, got {user_count}"

    print("=" * 80)
    print("ALL 40 ENTERPRISE AUTHENTICATION & RBAC TESTS PASSED SUCCESSFULLY! (100% SUCCESS)")
    print("=" * 80)

if __name__ == "__main__":
    run_tests()
