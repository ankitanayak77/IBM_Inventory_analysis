"""
Database Connection & Query Helper
----------------------------------
Manages SQLite connections for the Flask application.
Ensures:
1. Reusable connection bound to Flask application context (g.db).
2. Clean teardown after every request to prevent memory or connection leaks.
3. PRAGMA foreign_keys = ON is enforced on every new connection.
4. Row factory configured to sqlite3.Row for dictionary-like column access.
"""

import sqlite3
from pathlib import Path
from flask import g, current_app

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = str(BASE_DIR / "database" / "inventory.db")

def get_db():
    """Retrieve or open a database connection for the current request context."""
    if "db" not in g:
        db_path = current_app.config.get("DATABASE", DEFAULT_DB_PATH)
        g.db = sqlite3.connect(
            db_path,
            timeout=30.0,
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
        # Enforce foreign key constraints and high-concurrency PRAGMAs on every connection
        g.db.execute("PRAGMA foreign_keys = ON;")
        g.db.execute("PRAGMA journal_mode = WAL;")
        g.db.execute("PRAGMA busy_timeout = 30000;")
        g.db.execute("PRAGMA synchronous = NORMAL;")
    return g.db

def close_db(e=None):
    """Close the database connection at the end of the request context."""
    db = g.pop("db", None)
    if db is not None:
        db.close()

def query_db(query, args=(), one=False):
    """Convenience helper to execute SQL queries and return dictionary-like Rows."""
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def init_app(app):
    """Register database functions with the Flask app."""
    app.teardown_appcontext(close_db)
