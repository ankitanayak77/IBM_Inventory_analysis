"""
Flask Application Configuration
-------------------------------
Contains enterprise security and configuration settings for development and production.
Uses environment variables with safe development defaults and project-relative paths.
"""

import os
import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

class Config:
    # Security: Secret key for session signing and CSRF tokens
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-smart-inventory-secret-key-2026")
    
    # Database path
    DATABASE = str(BASE_DIR / "database" / "inventory.db")
    DEBUG = os.environ.get("FLASK_DEBUG", "True").lower() in ("true", "1", "yes")
    APP_NAME = "Smart Inventory & Sales Analysis System"
    VERSION = "1.0.0"

    # Session Security Controls
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() in ("true", "1", "yes")
    PERMANENT_SESSION_LIFETIME = datetime.timedelta(days=7)

    # CSRF Protection Controls
    WTF_CSRF_ENABLED = os.environ.get("WTF_CSRF_ENABLED", "true").lower() in ("true", "1", "yes")
    WTF_CSRF_TIME_LIMIT = int(os.environ.get("WTF_CSRF_TIME_LIMIT", "3600"))

    # Authentication Enforcement & Brute Force Controls
    AUTH_REQUIRED = os.environ.get("AUTH_REQUIRED", "true").lower() in ("true", "1", "yes")
    MAX_FAILED_LOGIN_ATTEMPTS = int(os.environ.get("MAX_FAILED_LOGIN_ATTEMPTS", "5"))
    LOCKOUT_DURATION_MINUTES = int(os.environ.get("LOCKOUT_DURATION_MINUTES", "15"))

    # Public Role Selection Control (Configurable for academic/demo environment)
    ALLOW_PUBLIC_ROLE_SELECTION = os.environ.get("ALLOW_PUBLIC_ROLE_SELECTION", "true").lower() in ("true", "1", "yes")
    DEMO_ACCOUNTS_ENABLED = os.environ.get("DEMO_ACCOUNTS_ENABLED", "true").lower() in ("true", "1", "yes")
    DEMO_ADMIN_PASSWORD = os.environ.get("DEMO_ADMIN_PASSWORD", "AdminDev@2026")
    DEMO_MANAGER_PASSWORD = os.environ.get("DEMO_MANAGER_PASSWORD", "ManagerDev@2026")
    DEMO_ANALYST_PASSWORD = os.environ.get("DEMO_ANALYST_PASSWORD", "AnalystDev@2026")
    DEMO_ASSOCIATE_PASSWORD = os.environ.get("DEMO_ASSOCIATE_PASSWORD", "AssociateDev@2026")
