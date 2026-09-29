"""
Enterprise Authentication & Role-Based Access Control (RBAC) Service
---------------------------------------------------------------------
Provides secure scrypt password hashing (Werkzeug default), brute-force abuse protection,
normalized registration, session management, safe redirect validation,
and role authorization for the Smart Inventory & Sales Analysis System.
"""

import re
import datetime
import math
from functools import wraps
from urllib.parse import urlparse, urljoin
from flask import session, redirect, url_for, request, flash, g, current_app, jsonify, render_template
from werkzeug.security import generate_password_hash, check_password_hash
import db

# Role Definitions & Hierarchy
ROLE_ADMIN = "Administrator"
ROLE_MANAGER = "Inventory Manager"
ROLE_ANALYST = "Data Analyst"
ROLE_ASSOCIATE = "Store Associate"

ALL_ROLES = [ROLE_ADMIN, ROLE_MANAGER, ROLE_ANALYST, ROLE_ASSOCIATE]
DEFAULT_PUBLIC_ROLE = ROLE_ASSOCIATE  # Default role for public registration fallback
PUBLIC_SELECTABLE_ROLES = [ROLE_MANAGER, ROLE_ANALYST, ROLE_ASSOCIATE]

def canonicalize_role(role_name):
    """
    Standardize role names to ensure consistent comparison.
    Maps 'System Administrator' to 'Administrator' and trims whitespace.
    """
    if not role_name:
        return ""
    r = role_name.strip()
    if r in ("Administrator", "System Administrator"):
        return ROLE_ADMIN
    return r

def validate_email_format(email):
    """
    Strict email validation:
    - No whitespace anywhere
    - Exactly one '@' symbol
    - Non-empty local part and domain part
    - Local part allows letters, numbers, dot, underscore, plus, hyphen
    - Domain part must have at least one dot
    - Domain parts cannot be empty (no leading, trailing, or double dots)
    - TLD must be at least 2 alphabetic characters
    - Rejects: ankitgmail.com, ankit@, @gmail.com, ankit @gmail.com, ankit@gmail, ankit.com
    - Accepts: ankit@gmail.com, user@example.com
    """
    if not email or not isinstance(email, str):
        return False, "Please enter a valid email address. Email address is required."

    email = email.strip()
    if not email:
        return False, "Please enter a valid email address. Email address cannot be empty."

    if re.search(r"\s", email):
        return False, "Please enter a valid email address. Email address cannot contain spaces."

    if email.count("@") != 1:
        return False, "Please enter a valid email address containing exactly one '@' symbol."

    local_part, domain_part = email.split("@", 1)
    if not local_part:
        return False, "Please enter a valid email address. Recipient username before '@' is missing."
    if not domain_part:
        return False, "Please enter a valid email address. Domain name after '@' is missing."

    if not re.match(r"^[a-zA-Z0-9_.+-]+$", local_part):
        return False, "Please enter a valid email address. Recipient username contains invalid characters."

    if "." not in domain_part:
        return False, "Please enter a valid email address. Domain must include a top-level domain (e.g., .com)."

    domain_parts = domain_part.split(".")
    if any(len(p) == 0 for p in domain_parts):
        return False, "Please enter a valid email address. Domain contains empty segment or consecutive dots."

    tld = domain_parts[-1]
    if not re.match(r"^[a-zA-Z]{2,}$", tld):
        return False, "Please enter a valid email address. Domain must end with a valid top-level domain (e.g., .com)."

    for part in domain_parts:
        if not re.match(r"^[a-zA-Z0-9-]+$", part) or part.startswith("-") or part.endswith("-"):
            return False, "Please enter a valid email address. Domain contains invalid characters or misplaced hyphens."

    email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*\.[a-zA-Z]{2,}$"
    if not re.match(email_regex, email) or len(email) > 120:
        return False, "Please enter a valid email address (e.g., user@example.com)."

    return True, None

# Common weak passwords blacklist
COMMON_WEAK_PASSWORDS = frozenset([
    "password", "password123", "12345678", "123456789", "1234567890",
    "qwerty123", "admin123", "adminadmin", "welcome1", "letmein1",
    "iloveyou", "monkey123", "dragon123", "sunshine1", "princess1"
])

def init_auth_table():
    """
    Ensure the users table exists with proper schema, indexes,
    and automatic column migration for existing databases.
    """
    conn = db.get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'Store Associate',
            is_active INTEGER NOT NULL DEFAULT 1,
            failed_login_attempts INTEGER NOT NULL DEFAULT 0,
            locked_until TEXT DEFAULT NULL,
            last_login_at TEXT DEFAULT NULL,
            created_at TEXT NOT NULL DEFAULT (DATETIME('now'))
        );
    """)
    conn.commit()

    # Column migration for existing tables
    existing_cols = {row["name"] for row in conn.execute("PRAGMA table_info(users);").fetchall()}
    columns_to_add = [
        ("is_active", "INTEGER NOT NULL DEFAULT 1"),
        ("failed_login_attempts", "INTEGER NOT NULL DEFAULT 0"),
        ("locked_until", "TEXT DEFAULT NULL"),
        ("last_login_at", "TEXT DEFAULT NULL")
    ]
    for col_name, col_def in columns_to_add:
        if col_name not in existing_cols:
            try:
                conn.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_def};")
                conn.commit()
            except Exception:
                pass

    conn.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);")
    conn.commit()

    # Synchronize default development demo accounts with configured credentials
    admin_pw = current_app.config.get("DEMO_ADMIN_PASSWORD", "AdminDev@2026")
    mgr_pw = current_app.config.get("DEMO_MANAGER_PASSWORD", "ManagerDev@2026")
    analyst_pw = current_app.config.get("DEMO_ANALYST_PASSWORD", "AnalystDev@2026")
    assoc_pw = current_app.config.get("DEMO_ASSOCIATE_PASSWORD", "AssociateDev@2026")

    demo_users = [
        ("System Administrator", "admin@inventory.com", generate_password_hash(admin_pw), ROLE_ADMIN, 1),
        ("Inventory Manager", "manager@inventory.com", generate_password_hash(mgr_pw), ROLE_MANAGER, 1),
        ("Data Analyst", "analyst@inventory.com", generate_password_hash(analyst_pw), ROLE_ANALYST, 1),
        ("Store Associate", "associate@inventory.com", generate_password_hash(assoc_pw), ROLE_ASSOCIATE, 1)
    ]
    for name, email, pw_hash, role, is_active in demo_users:
        conn.execute("""
            INSERT INTO users (name, email, password_hash, role, is_active)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(email) DO UPDATE SET
                password_hash = excluded.password_hash,
                role = excluded.role,
                is_active = excluded.is_active;
        """, (name, email, pw_hash, role, is_active))
    conn.commit()

def validate_password_strength(password):
    """
    Enforce enterprise password complexity:
    - Minimum 8 characters
    - Must contain at least one letter and at least one digit or symbol
    - Must not be in common weak passwords blacklist
    """
    if not password or len(password) < 8:
        return False, "Password must be at least 8 characters long."

    if len(password) > 128:
        return False, "Password cannot exceed 128 characters."

    has_letter = bool(re.search(r"[A-Za-z]", password))
    has_digit_or_symbol = bool(re.search(r"[0-9!@#$%^&*()_+\-=\[\]{}|;:,.<>?/~`]", password))

    if not (has_letter and has_digit_or_symbol):
        return False, "Password must contain both letters and at least one number or special character."

    if password.lower() in COMMON_WEAK_PASSWORDS:
        return False, "This password is too common or easily guessable. Please choose a stronger password."

    return True, None

def register_user(name, email, password, confirm_password, role=None):
    """
    Validate and register a new user account.
    - Full Name (2-60 chars)
    - Email validation (strictly verified with @ and valid domain structure)
    - Role assignment:
        - If ALLOW_PUBLIC_ROLE_SELECTION is True: allows Store Associate, Data Analyst, Inventory Manager.
        - System Administrator is strictly blocked from public registration.
        - If disabled or invalid: defaults to DEFAULT_PUBLIC_ROLE (Store Associate).
    - Password validation: minimum 8 characters, complexity rules.
    - Password hashing: Werkzeug scrypt hashing.
    - Normalized lowercase email storage & uniqueness enforcement.
    """
    name = (name or "").strip()
    email = (email or "").strip().lower()
    password = password or ""
    confirm_password = confirm_password or ""

    if not name or len(name) < 2 or len(name) > 60:
        return {"success": False, "message": "Full name must be between 2 and 60 characters.", "user": None}

    is_valid_email, email_err = validate_email_format(email)
    if not is_valid_email:
        return {"success": False, "message": email_err, "user": None}

    # Role resolution & security checks
    allow_public_role = current_app.config.get("ALLOW_PUBLIC_ROLE_SELECTION", True)
    assigned_role = DEFAULT_PUBLIC_ROLE

    if role:
        cleaned_role = role.strip()
        # Strictly block administrative privilege escalation
        if canonicalize_role(cleaned_role) == ROLE_ADMIN:
            return {
                "success": False,
                "message": "System Administrator accounts cannot be created via public registration.",
                "user": None
            }

        if allow_public_role:
            if cleaned_role in PUBLIC_SELECTABLE_ROLES:
                assigned_role = cleaned_role
            else:
                return {
                    "success": False,
                    "message": f"Invalid role selected: '{cleaned_role}'. Choose from Store Associate, Data Analyst, or Inventory Manager.",
                    "user": None
                }
        else:
            # Public selection disabled; force default least-privileged role
            assigned_role = DEFAULT_PUBLIC_ROLE

    is_valid_pw, pw_err = validate_password_strength(password)
    if not is_valid_pw:
        return {"success": False, "message": pw_err, "user": None}

    if password != confirm_password:
        return {"success": False, "message": "Passwords do not match. Please verify both fields.", "user": None}

    conn = db.get_db()
    existing = conn.execute("SELECT user_id FROM users WHERE email = ?;", (email,)).fetchone()
    if existing:
        return {"success": False, "message": f"An account with email '{email}' is already registered. Please sign in.", "user": None}

    pw_hash = generate_password_hash(password)
    cur = conn.execute("""
        INSERT INTO users (name, email, password_hash, role, is_active, failed_login_attempts)
        VALUES (?, ?, ?, ?, 1, 0);
    """, (name, email, pw_hash, assigned_role))
    conn.commit()
    new_id = cur.lastrowid

    user = {
        "user_id": new_id,
        "name": name,
        "email": email,
        "role": assigned_role,
        "is_active": 1
    }
    return {
        "success": True,
        "message": f"Welcome, {name}. You are signed in as {assigned_role}.",
        "user": user
    }

def authenticate_user(email, password, selected_role=None):
    """
    Authenticate user by email and password with role consistency check and brute-force lockout protection.
    Returns generic error messages to prevent account enumeration.
    
    The selected_role parameter verifies that the role chosen on the login screen
    matches the authoritative database-stored role. Selecting an elevated role
    does not grant access.
    """
    email = (email or "").strip().lower()
    password = password or ""

    if not email or not password:
        return {"success": False, "message": "Invalid email, password, or role.", "user": None}

    conn = db.get_db()
    user_row = conn.execute("""
        SELECT user_id, name, email, password_hash, role, is_active,
               failed_login_attempts, locked_until, last_login_at
        FROM users
        WHERE email = ?;
    """, (email,)).fetchone()

    # Generic timing-attack defense: run dummy hash comparison if user not found
    if not user_row:
        check_password_hash("scrypt:32768:8:1$pWrlq0Jk38yxKdiG$a0c7b3699a70ce5e1a14b06dd06c5837067d447129899de6cbd45d5de21808335a8a67b70e1d58eeda7a5a4f11a7b85cb3346c90a26d060d36df60a544446db2", password)
        return {"success": False, "message": "Invalid email, password, or role.", "user": None}

    user_id = user_row["user_id"]
    is_active = user_row["is_active"]
    failed_attempts = user_row["failed_login_attempts"] or 0
    locked_until_str = user_row["locked_until"]

    # Check if account is deactivated
    if not is_active:
        return {
            "success": False,
            "message": "Your account has been deactivated. Please contact a system administrator.",
            "user": None
        }

    # Check if account is temporarily locked
    now = datetime.datetime.now(datetime.timezone.utc)
    if locked_until_str:
        try:
            locked_until = datetime.datetime.fromisoformat(locked_until_str)
            if now < locked_until:
                remaining_secs = (locked_until - now).total_seconds()
                mins = max(1, math.ceil(remaining_secs / 60))
                return {
                    "success": False,
                    "message": f"Account temporarily locked due to multiple failed login attempts. Please try again in {mins} minute(s).",
                    "user": None,
                    "locked": True
                }
            else:
                # Lockout has expired; clear lock
                conn.execute("UPDATE users SET locked_until = NULL, failed_login_attempts = 0 WHERE user_id = ?;", (user_id,))
                conn.commit()
                failed_attempts = 0
        except Exception:
            pass

    max_attempts = current_app.config.get("MAX_FAILED_LOGIN_ATTEMPTS", 5)
    lockout_mins = current_app.config.get("LOCKOUT_DURATION_MINUTES", 15)

    # 1. Verify password hash
    if not check_password_hash(user_row["password_hash"], password):
        failed_attempts += 1
        if failed_attempts >= max_attempts:
            lockout_time = now + datetime.timedelta(minutes=lockout_mins)
            conn.execute("""
                UPDATE users
                SET failed_login_attempts = ?, locked_until = ?
                WHERE user_id = ?;
            """, (failed_attempts, lockout_time.isoformat(), user_id))
            conn.commit()
            return {
                "success": False,
                "message": f"Account temporarily locked due to {failed_attempts} failed login attempts. Please try again in {lockout_mins} minutes.",
                "user": None,
                "locked": True
            }
        else:
            conn.execute("UPDATE users SET failed_login_attempts = ? WHERE user_id = ?;", (failed_attempts, user_id))
            conn.commit()
            return {"success": False, "message": "Invalid email, password, or role.", "user": None}

    # 2. Verify selected login role consistency check (does NOT grant privileges)
    if selected_role is not None:
        selected_role_clean = selected_role.strip()
        if not selected_role_clean or canonicalize_role(selected_role_clean) != canonicalize_role(user_row["role"]):
            failed_attempts += 1
            if failed_attempts >= max_attempts:
                lockout_time = now + datetime.timedelta(minutes=lockout_mins)
                conn.execute("""
                    UPDATE users
                    SET failed_login_attempts = ?, locked_until = ?
                    WHERE user_id = ?;
                """, (failed_attempts, lockout_time.isoformat(), user_id))
                conn.commit()
                return {
                    "success": False,
                    "message": f"Account temporarily locked due to {failed_attempts} failed login attempts. Please try again in {lockout_mins} minutes.",
                    "user": None,
                    "locked": True
                }
            else:
                conn.execute("UPDATE users SET failed_login_attempts = ? WHERE user_id = ?;", (failed_attempts, user_id))
                conn.commit()
                return {"success": False, "message": "Invalid email, password, or role.", "user": None}

    # Successful authentication: reset failed attempts & update last_login_at
    conn.execute("""
        UPDATE users
        SET failed_login_attempts = 0, locked_until = NULL, last_login_at = ?
        WHERE user_id = ?;
    """, (now.isoformat(), user_id))
    conn.commit()

    user = {
        "user_id": user_row["user_id"],
        "name": user_row["name"],
        "email": user_row["email"],
        "role": user_row["role"],
        "is_active": user_row["is_active"],
        "last_login_at": user_row["last_login_at"]
    }
    return {"success": True, "message": f"Welcome back, {user['name']}!", "user": user}

def get_user_by_id(user_id):
    """Retrieve active user dictionary by ID."""
    if not user_id:
        return None
    conn = db.get_db()
    row = conn.execute("""
        SELECT user_id, name, email, role, is_active, last_login_at, created_at
        FROM users
        WHERE user_id = ? AND is_active = 1;
    """, (user_id,)).fetchone()
    return dict(row) if row else None

def is_safe_url(target):
    """
    Validate redirect target to prevent open redirect vulnerabilities.
    Only allows local/internal relative URLs.
    """
    if not target or not isinstance(target, str):
        return False
    target = target.strip()
    if target.startswith("//") or target.startswith("\\\\"):
        return False
    parsed = urlparse(target)
    # Target must have no host/netloc and start with a single slash
    return parsed.netloc == "" and target.startswith("/")

def login_required(f):
    """
    Decorator enforcing that user must be authenticated.
    Redirects unauthenticated browser requests to /login.
    Returns 401 JSON for API requests.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Support optional bypass during local headless non-auth tests if explicitly disabled
        auth_enforced = current_app.config.get("AUTH_REQUIRED", True)
        if not auth_enforced:
            return f(*args, **kwargs)

        user_id = session.get("user_id")
        if not user_id:
            if request.path.startswith("/api/") or request.headers.get("Accept") == "application/json":
                return jsonify({"error": "Unauthorized", "message": "Authentication required."}), 401
            flash("Please sign in to access this page.", "warning")
            next_url = request.full_path if request.query_string else request.path
            return redirect(url_for("login", next=next_url))

        # Verify account is still active in database
        user = get_user_by_id(user_id)
        if not user:
            session.clear()
            if request.path.startswith("/api/") or request.headers.get("Accept") == "application/json":
                return jsonify({"error": "Unauthorized", "message": "User inactive or session expired."}), 401
            flash("Your session has expired or your account is deactivated. Please sign in again.", "warning")
            return redirect(url_for("login"))

        return f(*args, **kwargs)
    return decorated_function

def role_required(*allowed_roles):
    """
    Decorator enforcing role-based access control (RBAC).
    Returns 403 Forbidden page or JSON for unauthorized users.
    Uses canonicalize_role for robust role equivalence (e.g. System Administrator vs Administrator).
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            auth_enforced = current_app.config.get("AUTH_REQUIRED", True)
            if not auth_enforced:
                return f(*args, **kwargs)

            user_id = session.get("user_id")
            if not user_id:
                if request.path.startswith("/api/") or request.headers.get("Accept") == "application/json":
                    return jsonify({"error": "Unauthorized", "message": "Authentication required."}), 401
                return redirect(url_for("login", next=request.path))

            user_role = session.get("user_role")
            canonical_user_role = canonicalize_role(user_role)
            canonical_allowed = {canonicalize_role(r) for r in allowed_roles}

            if canonical_user_role not in canonical_allowed:
                if request.path.startswith("/api/") or request.headers.get("Accept") == "application/json":
                    return jsonify({
                        "error": "Forbidden",
                        "message": "You do not have permission to perform this action.",
                        "required_roles": list(allowed_roles),
                        "current_role": user_role
                    }), 403
                return render_template("errors/403.html", required_roles=allowed_roles, user_role=user_role), 403

            return f(*args, **kwargs)
        return decorated_function
    return decorator

# User Administration Functions (System Administrator only)
def get_all_users():
    """Retrieve all users for administrative governance."""
    conn = db.get_db()
    rows = conn.execute("""
        SELECT user_id, name, email, role, is_active, failed_login_attempts,
               locked_until, last_login_at, created_at
        FROM users
        ORDER BY created_at DESC;
    """).fetchall()
    return [dict(r) for r in rows]

def update_user_role(admin_user_id, target_user_id, new_role):
    """Update another user's role. Protects against demoting the last administrator."""
    if new_role not in ALL_ROLES:
        return False, "Invalid role specified."

    conn = db.get_db()
    target = conn.execute("SELECT role FROM users WHERE user_id = ?;", (target_user_id,)).fetchone()
    if not target:
        return False, "User not found."

    # Prevent demoting the last active administrator
    if target["role"] == ROLE_ADMIN and new_role != ROLE_ADMIN:
        admin_count = conn.execute("SELECT COUNT(*) AS total FROM users WHERE role = ? AND is_active = 1;", (ROLE_ADMIN,)).fetchone()["total"]
        if admin_count <= 1:
            return False, "Cannot change role: At least one active Administrator must remain."

    conn.execute("UPDATE users SET role = ? WHERE user_id = ?;", (new_role, target_user_id))
    conn.commit()
    return True, f"User role updated to '{new_role}'."

def toggle_user_status(admin_user_id, target_user_id):
    """Toggle a user's active/inactive status. Prevents self-deactivation."""
    if admin_user_id == target_user_id:
        return False, "You cannot deactivate your own account."

    conn = db.get_db()
    target = conn.execute("SELECT is_active, role FROM users WHERE user_id = ?;", (target_user_id,)).fetchone()
    if not target:
        return False, "User not found."

    new_status = 0 if target["is_active"] == 1 else 1

    # Prevent deactivating the last active administrator
    if target["role"] == ROLE_ADMIN and new_status == 0:
        admin_count = conn.execute("SELECT COUNT(*) AS total FROM users WHERE role = ? AND is_active = 1;", (ROLE_ADMIN,)).fetchone()["total"]
        if admin_count <= 1:
            return False, "Cannot deactivate the only active Administrator."

    conn.execute("UPDATE users SET is_active = ? WHERE user_id = ?;", (new_status, target_user_id))
    conn.commit()
    action = "activated" if new_status == 1 else "deactivated"
    return True, f"User account has been {action}."

# ==========================================================
# Profile & Account Management Services
# ==========================================================

def get_user_initials(name):
    """Generate 1-2 character uppercase initials from a user's name."""
    if not name:
        return "U"
    parts = [p for p in name.strip().split() if p]
    if len(parts) >= 2:
        return f"{parts[0][0]}{parts[-1][0]}".upper()
    elif len(parts) == 1:
        return parts[0][:2].upper()
    return "U"

def update_user_profile(user_id, name, email, current_password=None):
    """
    Update personal profile information for the authenticated user.
    - Name and Email are editable.
    - User ID, Role, Status, and Created Date are strictly immutable.
    - Changing email requires verifying current password confirmation.
    - Email uniqueness is strictly enforced against all other accounts.
    """
    if not user_id:
        return {"success": False, "message": "Authentication required."}

    conn = db.get_db()
    user_row = conn.execute("""
        SELECT user_id, name, email, password_hash, role, is_active
        FROM users
        WHERE user_id = ? AND is_active = 1;
    """, (user_id,)).fetchone()

    if not user_row:
        return {"success": False, "message": "User account not found or inactive."}

    # Validate name
    name = (name or "").strip()
    if not name or len(name) < 2 or len(name) > 60:
        return {"success": False, "message": "Full name must be between 2 and 60 characters."}

    # Validate email
    email = (email or "").strip().lower()
    is_valid_email, email_err = validate_email_format(email)
    if not is_valid_email:
        return {"success": False, "message": email_err}

    current_email = (user_row["email"] or "").strip().lower()
    email_changed = (email != current_email)

    # Email Change Safety: require current password confirmation
    if email_changed:
        if not current_password:
            return {
                "success": False,
                "message": "Current password is required to change your email address for account security."
            }

        if not check_password_hash(user_row["password_hash"], current_password):
            return {
                "success": False,
                "message": "Current password verification failed. Email address was not changed."
            }

        # Enforce email uniqueness against other users
        existing = conn.execute(
            "SELECT user_id FROM users WHERE email = ? AND user_id != ?;",
            (email, user_id)
        ).fetchone()
        if existing:
            return {
                "success": False,
                "message": f"The email '{email}' is already registered to another account."
            }

    # Save updates safely (only name and email are updated)
    conn.execute("""
        UPDATE users
        SET name = ?, email = ?
        WHERE user_id = ?;
    """, (name, email, user_id))
    conn.commit()

    updated_user = get_user_by_id(user_id)
    return {
        "success": True,
        "message": "Profile updated successfully.",
        "user": updated_user,
        "email_changed": email_changed
    }

def change_user_password(user_id, current_password, new_password, confirm_password):
    """
    Safely change password for authenticated user.
    - Verifies existing password hash.
    - Enforces password strength policy and confirmation matching.
    - Generates new scrypt hash using Werkzeug.
    - Plaintext password is never stored or logged.
    """
    if not user_id:
        return {"success": False, "message": "Authentication required."}

    conn = db.get_db()
    user_row = conn.execute("""
        SELECT user_id, password_hash
        FROM users
        WHERE user_id = ? AND is_active = 1;
    """, (user_id,)).fetchone()

    if not user_row:
        return {"success": False, "message": "User account not found or inactive."}

    # Verify current password
    if not current_password or not check_password_hash(user_row["password_hash"], current_password):
        return {"success": False, "message": "Incorrect current password."}

    # Verify confirmation match
    if not new_password or not confirm_password:
        return {"success": False, "message": "Please provide both the new password and confirmation."}

    if new_password != confirm_password:
        return {"success": False, "message": "New password and confirmation do not match."}

    # Check password strength policy
    is_valid, err_msg = validate_password_strength(new_password)
    if not is_valid:
        return {"success": False, "message": err_msg}

    # Save new password hash (scrypt)
    new_hash = generate_password_hash(new_password)
    conn.execute("""
        UPDATE users
        SET password_hash = ?
        WHERE user_id = ?;
    """, (new_hash, user_id))
    conn.commit()

    return {
        "success": True,
        "message": "Password changed successfully. Please sign in again with your new credentials."
    }

