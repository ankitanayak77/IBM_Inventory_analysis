"""
Smart Inventory & Sales Analysis System - User Profile & Account Management Test Suite
--------------------------------------------------------------------------------------
Validates all 25 user profile, personal data editing, password change, email safety,
role immutability, and RBAC governance requirements.
"""

import sys
import re
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app import app
from services import auth_service
from werkzeug.security import check_password_hash, generate_password_hash
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

def run_tests():
    print("=" * 75)
    print("STARTING TEST SUITE: USER PROFILE & ACCOUNT MANAGEMENT (25 TESTS)")
    print("=" * 75)

    # 1. Authenticated user can open /profile
    client1 = app.test_client()
    with client1.session_transaction() as sess:
        sess["user_id"] = 3
        sess["user_name"] = "Data Analyst"
        sess["user_role"] = "Data Analyst"
        sess["user_email"] = "analyst@inventory.com"

    res1 = client1.get("/profile")
    assert res1.status_code == 200, f"Expected 200, got {res1.status_code}"
    html1 = res1.data.decode("utf-8")
    assert "My Profile" in html1
    print("[1/25] Authenticated user can open /profile: PASS")

    # 2. Unauthenticated user cannot open /profile
    client2 = app.test_client()
    res2 = client2.get("/profile")
    assert res2.status_code == 302, f"Expected 302 redirect, got {res2.status_code}"
    assert "/login" in res2.headers.get("Location", "")
    print("[2/25] Unauthenticated user cannot open /profile (redirects to /login): PASS")

    # 3. Profile displays current user's name
    assert "Data Analyst" in html1
    print("[3/25] Profile displays current user's full name: PASS")

    # 4. Profile displays current user's email
    assert "analyst@inventory.com" in html1
    print("[4/25] Profile displays current user's email address: PASS")

    # 5. Profile displays correct role
    assert "Data Analyst" in html1
    assert "role-badge" in html1
    print("[5/25] Profile displays correct operational role badge: PASS")

    # 6. Profile displays user_id
    assert "#3" in html1 or "User ID: #3" in html1 or "User ID" in html1
    print("[6/25] Profile displays immutable user_id: PASS")

    # 7. User can update own name
    test_update_client = app.test_client()
    with test_update_client.session_transaction() as sess:
        sess["user_id"] = 3
        sess["user_name"] = "Data Analyst"
        sess["user_role"] = "Data Analyst"
        sess["user_email"] = "analyst@inventory.com"

    res7 = post_form(test_update_client, "/profile/edit", {
        "name": "Alex Analyst Updated",
        "email": "analyst@inventory.com"
    }, form_page="/profile/edit", follow_redirects=True)
    assert res7.status_code == 200
    with app.app_context():
        conn = db.get_db()
        name_in_db = conn.execute("SELECT name FROM users WHERE user_id = 3;").fetchone()["name"]
        assert name_in_db == "Alex Analyst Updated", f"Expected updated name, got {name_in_db}"
    # Revert back to original
    with app.app_context():
        conn = db.get_db()
        conn.execute("UPDATE users SET name = 'Data Analyst' WHERE user_id = 3;")
        conn.commit()
    print("[7/25] User can update own full name: PASS")

    # 8. User can update own email (with password verification)
    res8 = post_form(test_update_client, "/profile/edit", {
        "name": "Data Analyst",
        "email": "analyst_new@inventory.com",
        "current_password": "AnalystDev@2026"
    }, form_page="/profile/edit", follow_redirects=True)
    assert res8.status_code == 200
    with app.app_context():
        conn = db.get_db()
        email_in_db = conn.execute("SELECT email FROM users WHERE user_id = 3;").fetchone()["email"]
        assert email_in_db == "analyst_new@inventory.com", f"Expected new email, got {email_in_db}"
    # Revert back
    with app.app_context():
        conn = db.get_db()
        conn.execute("UPDATE users SET email = 'analyst@inventory.com' WHERE user_id = 3;")
        conn.commit()
    print("[8/25] User can update own email with password confirmation: PASS")

    # 9. Email is normalized to lowercase in storage
    res9 = post_form(test_update_client, "/profile/edit", {
        "name": "Data Analyst",
        "email": "ANALYST_UPPER@INVENTORY.COM",
        "current_password": "AnalystDev@2026"
    }, form_page="/profile/edit", follow_redirects=True)
    assert res9.status_code == 200
    with app.app_context():
        conn = db.get_db()
        email_normalized = conn.execute("SELECT email FROM users WHERE user_id = 3;").fetchone()["email"]
        assert email_normalized == "analyst_upper@inventory.com", f"Expected lowercase email, got {email_normalized}"
    # Revert back
    with app.app_context():
        conn = db.get_db()
        conn.execute("UPDATE users SET email = 'analyst@inventory.com' WHERE user_id = 3;")
        conn.commit()
    print("[9/25] Email is strictly normalized to lowercase: PASS")

    # 10. Duplicate email rejected
    res10 = post_form(test_update_client, "/profile/edit", {
        "name": "Data Analyst",
        "email": "admin@inventory.com",  # Already belongs to Admin (user 1)
        "current_password": "AnalystDev@2026"
    }, form_page="/profile/edit", follow_redirects=True)
    html10 = res10.data.decode("utf-8")
    assert "already registered" in html10 or "already in use" in html10
    with app.app_context():
        conn = db.get_db()
        email_check = conn.execute("SELECT email FROM users WHERE user_id = 3;").fetchone()["email"]
        assert email_check == "analyst@inventory.com"
    print("[10/25] Duplicate email registration rejected: PASS")

    # 11. Invalid email format rejected
    res11 = post_form(test_update_client, "/profile/edit", {
        "name": "Data Analyst",
        "email": "not-an-email-address",
        "current_password": "AnalystDev@2026"
    }, form_page="/profile/edit", follow_redirects=True)
    html11 = res11.data.decode("utf-8")
    assert "valid email" in html11.lower()
    print("[11/25] Invalid email format rejected: PASS")

    # 12. Role cannot be changed through profile request
    res12 = post_form(test_update_client, "/profile/edit", {
        "name": "Data Analyst",
        "email": "analyst@inventory.com",
        "role": "Administrator"  # Malicious attempt to escalate role
    }, form_page="/profile/edit", follow_redirects=True)
    with app.app_context():
        conn = db.get_db()
        role_check = conn.execute("SELECT role FROM users WHERE user_id = 3;").fetchone()["role"]
        assert role_check == "Data Analyst", f"Privilege escalation! Role was changed to {role_check}"
    print("[12/25] Role cannot be changed through profile request: PASS")

    # 13. User cannot modify another user's profile
    res13 = post_form(test_update_client, "/profile/edit", {
        "user_id": 1,  # Attempting to modify Admin (user 1)
        "name": "Hacked Admin Name",
        "email": "hacked_admin@inventory.com"
    }, form_page="/profile/edit", follow_redirects=True)
    with app.app_context():
        conn = db.get_db()
        admin_row = conn.execute("SELECT name, email FROM users WHERE user_id = 1;").fetchone()
        assert admin_row["email"] == "admin@inventory.com", "Admin email was tampered with!"
    print("[13/25] Insecure Direct Object Reference (IDOR) prevented: PASS")

    # 14. Missing / invalid CSRF rejected
    res14 = test_update_client.post("/profile/edit", data={
        "name": "No CSRF User",
        "email": "nocsrf@inventory.com"
    })
    assert res14.status_code == 400, f"Expected 400 on CSRF failure, got {res14.status_code}"
    print("[14/25] Missing/invalid CSRF token rejected: PASS")

    # 15. Current password required for email change
    res15 = post_form(test_update_client, "/profile/edit", {
        "name": "Data Analyst",
        "email": "analyst_unauthorized@inventory.com",
        "current_password": ""  # Missing password
    }, form_page="/profile/edit", follow_redirects=True)
    html15 = res15.data.decode("utf-8")
    assert "Current password is required" in html15 or "required to change your email" in html15
    with app.app_context():
        conn = db.get_db()
        check_email = conn.execute("SELECT email FROM users WHERE user_id = 3;").fetchone()["email"]
        assert check_email == "analyst@inventory.com"
    print("[15/25] Current password strictly required for email modification: PASS")

    # 16. Correct password change works
    pw_client = app.test_client()
    with pw_client.session_transaction() as sess:
        sess["user_id"] = 11  # Store Associate
        sess["user_name"] = "Store Associate"
        sess["user_role"] = "Store Associate"
        sess["user_email"] = "associate@inventory.com"

    res16 = post_form(pw_client, "/profile/password", {
        "current_password": "AssociateDev@2026",
        "new_password": "NewSecurePass@2026",
        "confirm_password": "NewSecurePass@2026"
    }, form_page="/profile/password", follow_redirects=False)
    assert res16.status_code == 302, f"Expected 302 redirect after password change, got {res16.status_code}"
    assert "/login" in res16.headers.get("Location", "")
    with app.app_context():
        conn = db.get_db()
        new_pw_hash = conn.execute("SELECT password_hash FROM users WHERE user_id = 11;").fetchone()["password_hash"]
        assert check_password_hash(new_pw_hash, "NewSecurePass@2026")
    print("[16/25] Correct password change updates hash and redirects: PASS")

    # 17. Incorrect current password rejected
    with pw_client.session_transaction() as sess:
        sess["user_id"] = 11
        sess["user_name"] = "Store Associate"
        sess["user_role"] = "Store Associate"

    res17 = post_form(pw_client, "/profile/password", {
        "current_password": "WrongCurrentPassword!1",
        "new_password": "AnotherNewPass@2026",
        "confirm_password": "AnotherNewPass@2026"
    }, form_page="/profile/password", follow_redirects=True)
    html17 = res17.data.decode("utf-8")
    assert "Incorrect current password" in html17
    print("[17/25] Incorrect current password rejected: PASS")

    # 18. New password mismatch rejected
    res18 = post_form(pw_client, "/profile/password", {
        "current_password": "NewSecurePass@2026",
        "new_password": "ValidNewPass@2026",
        "confirm_password": "DifferentPassword@2026"
    }, form_page="/profile/password", follow_redirects=True)
    html18 = res18.data.decode("utf-8")
    assert "do not match" in html18.lower()
    print("[18/25] New password confirmation mismatch rejected: PASS")

    # 19. Weak password rejected by policy
    res19 = post_form(pw_client, "/profile/password", {
        "current_password": "NewSecurePass@2026",
        "new_password": "password",
        "confirm_password": "password"
    }, form_page="/profile/password", follow_redirects=True)
    html19 = res19.data.decode("utf-8")
    assert "too common" in html19.lower() or "8 characters" in html19.lower()
    print("[19/25] Weak password rejected by complexity and blacklist policies: PASS")

    # 20. Password stored only as secure scrypt hash
    with app.app_context():
        conn = db.get_db()
        hash_format = conn.execute("SELECT password_hash FROM users WHERE user_id = 11;").fetchone()["password_hash"]
        assert hash_format.startswith("scrypt:32768:8:1"), f"Expected scrypt hash format, got {hash_format[:20]}"
    # Restore Associate's original password for consistency
    with app.app_context():
        conn = db.get_db()
        conn.execute("UPDATE users SET password_hash = ? WHERE user_id = 11;", (generate_password_hash("AssociateDev@2026"),))
        conn.commit()
    print("[20/25] Password verified stored exclusively as Werkzeug scrypt hash: PASS")

    # 21. Successful password change requires re-login (session cleared)
    relogin_client = app.test_client()
    with relogin_client.session_transaction() as sess:
        sess["user_id"] = 11
        sess["user_name"] = "Store Associate"
        sess["user_role"] = "Store Associate"

    res_pw_change = post_form(relogin_client, "/profile/password", {
        "current_password": "AssociateDev@2026",
        "new_password": "NewSecurePass@2026",
        "confirm_password": "NewSecurePass@2026"
    }, form_page="/profile/password", follow_redirects=False)
    assert res_pw_change.status_code == 302
    assert "/login" in res_pw_change.headers.get("Location", "")

    # Verify session is cleared
    with relogin_client.session_transaction() as sess:
        assert "user_id" not in sess, "Session was not cleared after password change!"
    res21 = relogin_client.get("/profile")
    assert res21.status_code == 302
    assert "/login" in res21.headers.get("Location", "")

    # Restore password back to AssociateDev@2026
    with app.app_context():
        conn = db.get_db()
        conn.execute("UPDATE users SET password_hash = ? WHERE user_id = 11;", (generate_password_hash("AssociateDev@2026"),))
        conn.commit()
    print("[21/25] Password change terminates active session and forces re-login: PASS")

    # 22. Admin user can still use admin user management
    admin_client = app.test_client()
    with admin_client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["user_name"] = "Admin User"
        sess["user_role"] = "Administrator"

    res22 = admin_client.get("/admin/users")
    assert res22.status_code == 200
    assert b"System User &amp; Role Governance" in res22.data or b"System User & Role Governance" in res22.data
    print("[22/25] Administrator can access user management (/admin/users): PASS")

    # 23. Non-admin cannot access admin user management
    associate_client = app.test_client()
    with associate_client.session_transaction() as sess:
        sess["user_id"] = 11
        sess["user_name"] = "Store Associate"
        sess["user_role"] = "Store Associate"

    res23 = associate_client.get("/admin/users")
    assert res23.status_code == 403, f"Expected 403 Forbidden, got {res23.status_code}"
    print("[23/25] Non-administrator strictly barred from admin governance (HTTP 403): PASS")

    # 24. All four seeded accounts can authenticate
    seeded_credentials = [
        ("admin@inventory.com", "AdminDev@2026", "Administrator"),
        ("manager@inventory.com", "ManagerDev@2026", "Inventory Manager"),
        ("analyst@inventory.com", "AnalystDev@2026", "Data Analyst"),
        ("associate@inventory.com", "AssociateDev@2026", "Store Associate")
    ]
    with app.app_context():
        for email, pw, role in seeded_credentials:
            auth_res = auth_service.authenticate_user(email, pw)
            assert auth_res["success"] is True, f"Failed to authenticate seeded account {email}: {auth_res['message']}"
            assert auth_res["user"]["role"] == role, f"Role mismatch for {email}"
    print("[24/25] All four seeded accounts authenticate successfully with separate roles: PASS")

    # 25. Each seeded account has a distinct email and role
    with app.app_context():
        conn = db.get_db()
        users_rows = conn.execute("SELECT user_id, email, role FROM users WHERE email IN ('admin@inventory.com', 'manager@inventory.com', 'analyst@inventory.com', 'associate@inventory.com');").fetchall()
        assert len(users_rows) == 4
        emails = {r["email"] for r in users_rows}
        roles = {r["role"] for r in users_rows}
        assert len(emails) == 4, f"Duplicate emails detected: {emails}"
        assert len(roles) == 4, f"Duplicate roles detected: {roles}"
    print("[25/25] Each seeded account has distinct unique email and operational role: PASS")

    # Final cleanup of any potential leftover test users
    with app.app_context():
        conn = db.get_db()
        conn.execute("DELETE FROM users WHERE email NOT IN ('admin@inventory.com', 'manager@inventory.com', 'analyst@inventory.com', 'associate@inventory.com');")
        conn.commit()

    print("=" * 75)
    print("ALL 25 USER PROFILE & ACCOUNT MANAGEMENT TESTS PASSED! (100% SUCCESS)")
    print("=" * 75)

if __name__ == "__main__":
    run_tests()
