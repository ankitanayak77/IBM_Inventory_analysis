"""
Authentication & User Management Service
----------------------------------------
Provides secure password hashing, registration, authentication,
and session management for the Smart Inventory & Sales Analysis System.
"""

import re
from functools import wraps
from flask import session, redirect, url_for, request, flash, g
from werkzeug.security import generate_password_hash, check_password_hash
import db

def init_auth_table():
    """Ensure the users table exists and seed default accounts if empty."""
    conn = db.get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'Analyst',
            created_at TEXT NOT NULL DEFAULT (DATETIME('now'))
        );
    """)
    conn.commit()

    # Check if any users exist; if not, seed default demo accounts
    cur = conn.execute("SELECT COUNT(*) AS total FROM users;")
    row = cur.fetchone()
    if row and row["total"] == 0:
        demo_users = [
            ("Admin User", "admin@inventory.com", generate_password_hash("Admin@123"), "Administrator"),
            ("Inventory Manager", "manager@inventory.com", generate_password_hash("Manager@123"), "Inventory Manager"),
            ("Data Analyst", "analyst@inventory.com", generate_password_hash("Analyst@123"), "Analyst")
        ]
        conn.executemany("""
            INSERT INTO users (name, email, password_hash, role)
            VALUES (?, ?, ?, ?);
        """, demo_users)
        conn.commit()

def register_user(name, email, password, confirm_password, role="Analyst"):
    """
    Validate and register a new user.
    Returns: dict(success=bool, message=str, user=dict|None)
    """
    name = (name or "").strip()
    email = (email or "").strip().lower()
    password = password or ""
    confirm_password = confirm_password or ""
    role = (role or "Analyst").strip()

    valid_roles = ["Analyst", "Inventory Manager", "Store Associate", "Administrator"]
    if role not in valid_roles:
        role = "Analyst"

    if not name or len(name) < 2:
        return {"success": False, "message": "Please enter a valid full name (minimum 2 characters).", "user": None}

    email_regex = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    if not re.match(email_regex, email):
        return {"success": False, "message": "Please enter a valid email address.", "user": None}

    if len(password) < 6:
        return {"success": False, "message": "Password must be at least 6 characters long.", "user": None}

    if password != confirm_password:
        return {"success": False, "message": "Passwords do not match. Please verify both fields.", "user": None}

    conn = db.get_db()
    existing = conn.execute("SELECT user_id FROM users WHERE email = ?;", (email,)).fetchone()
    if existing:
        return {"success": False, "message": f"An account with email '{email}' already exists. Please sign in.", "user": None}

    pw_hash = generate_password_hash(password)
    cur = conn.execute("""
        INSERT INTO users (name, email, password_hash, role)
        VALUES (?, ?, ?, ?);
    """, (name, email, pw_hash, role))
    conn.commit()
    new_id = cur.lastrowid

    user = {
        "user_id": new_id,
        "name": name,
        "email": email,
        "role": role
    }
    return {"success": True, "message": "Account created successfully! Welcome to Smart Inventory.", "user": user}

def authenticate_user(email, password):
    """
    Authenticate user by email and password.
    Returns: dict(success=bool, message=str, user=dict|None)
    """
    email = (email or "").strip().lower()
    password = password or ""

    if not email or not password:
        return {"success": False, "message": "Please provide both email and password.", "user": None}

    conn = db.get_db()
    user_row = conn.execute("""
        SELECT user_id, name, email, password_hash, role, created_at
        FROM users
        WHERE email = ?;
    """, (email,)).fetchone()

    if not user_row or not check_password_hash(user_row["password_hash"], password):
        return {"success": False, "message": "Invalid email or password. Please try again.", "user": None}

    user = {
        "user_id": user_row["user_id"],
        "name": user_row["name"],
        "email": user_row["email"],
        "role": user_row["role"],
        "created_at": user_row["created_at"]
    }
    return {"success": True, "message": f"Welcome back, {user['name']}!", "user": user}

def get_user_by_id(user_id):
    """Retrieve user dictionary by ID."""
    if not user_id:
        return None
    conn = db.get_db()
    row = conn.execute("SELECT user_id, name, email, role, created_at FROM users WHERE user_id = ?;", (user_id,)).fetchone()
    return dict(row) if row else None

def login_required(f):
    """Decorator to require login on sensitive view endpoints."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please sign in to access this page.", "warning")
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function
