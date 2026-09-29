"""
Flask Application Configuration
-------------------------------
Contains configuration settings for development and production.
Uses project-relative paths to ensure portability across environments.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-smart-inventory-secret-key-2026")
    DATABASE = str(BASE_DIR / "database" / "inventory.db")
    DEBUG = True
    APP_NAME = "Smart Inventory & Sales Analysis System"
    VERSION = "1.0.0"
