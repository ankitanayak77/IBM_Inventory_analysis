"""
Database Initialization Script
------------------------------
Initializes the SQLite schema for the Smart Inventory & Sales Analysis System.

Key Design Decisions:
- product_id and store_id are INTEGER PRIMARY KEY (no autoincrement) to match source IDs.
- reorder_level lives primarily in the inventory table (store-product level).
- Normalized relational design with strict FOREIGN KEY constraints.
- Optimized composite indexes for fast date-range, product, and store analytics.
"""

import os
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_DIR = BASE_DIR / "database"
DB_PATH = DB_DIR / "inventory.db"

SCHEMA_SQL = """
-- Enable Foreign Key support
PRAGMA foreign_keys = ON;

-- 1. PRODUCTS TABLE
CREATE TABLE IF NOT EXISTS products (
    product_id INTEGER PRIMARY KEY,
    product_name TEXT NOT NULL,
    category TEXT NOT NULL,
    cost_price REAL NOT NULL CHECK(cost_price >= 0),
    selling_price REAL NOT NULL CHECK(selling_price >= 0),
    active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0, 1)),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. STORES TABLE
CREATE TABLE IF NOT EXISTS stores (
    store_id INTEGER PRIMARY KEY,
    store_name TEXT NOT NULL,
    city TEXT NOT NULL,
    location TEXT NOT NULL,
    open_date DATE NOT NULL,
    active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0, 1)),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. INVENTORY TABLE (Store-specific stock and reorder thresholds)
CREATE TABLE IF NOT EXISTS inventory (
    inventory_id INTEGER PRIMARY KEY AUTOINCREMENT,
    store_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    stock_on_hand INTEGER NOT NULL DEFAULT 0 CHECK(stock_on_hand >= 0),
    reorder_level INTEGER NOT NULL DEFAULT 10 CHECK(reorder_level >= 0),
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (store_id) REFERENCES stores(store_id) ON DELETE RESTRICT,
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE RESTRICT,
    UNIQUE(store_id, product_id)
);

-- 4. SALES TABLE (Historical & real-time sales transactions)
CREATE TABLE IF NOT EXISTS sales (
    sale_id INTEGER PRIMARY KEY,
    product_id INTEGER NOT NULL,
    store_id INTEGER NOT NULL,
    sale_date DATE NOT NULL,
    quantity INTEGER NOT NULL CHECK(quantity > 0),
    unit_price REAL NOT NULL CHECK(unit_price >= 0),
    total_amount REAL NOT NULL CHECK(total_amount >= 0),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE RESTRICT,
    FOREIGN KEY (store_id) REFERENCES stores(store_id) ON DELETE RESTRICT
);

-- 5. RESTOCKS TABLE (Inventory replenishment records)
CREATE TABLE IF NOT EXISTS restocks (
    restock_id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    store_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL CHECK(quantity > 0),
    cost_per_unit REAL NOT NULL CHECK(cost_per_unit >= 0),
    restock_date DATE NOT NULL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE RESTRICT,
    FOREIGN KEY (store_id) REFERENCES stores(store_id) ON DELETE RESTRICT
);

-- 6. STOCK MOVEMENTS TABLE (Complete immutable audit trail)
CREATE TABLE IF NOT EXISTS stock_movements (
    movement_id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    store_id INTEGER NOT NULL,
    movement_type TEXT NOT NULL CHECK(movement_type IN ('OPENING_STOCK', 'SALE', 'RESTOCK', 'MANUAL_ADJUSTMENT')),
    quantity INTEGER NOT NULL,
    reference_id INTEGER,
    movement_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE RESTRICT,
    FOREIGN KEY (store_id) REFERENCES stores(store_id) ON DELETE RESTRICT
);

-- INDEXES FOR FAST ANALYTICS
CREATE INDEX IF NOT EXISTS idx_sales_date ON sales(sale_date);
CREATE INDEX IF NOT EXISTS idx_sales_product ON sales(product_id);
CREATE INDEX IF NOT EXISTS idx_sales_store ON sales(store_id);
CREATE INDEX IF NOT EXISTS idx_sales_date_product ON sales(sale_date, product_id);
CREATE INDEX IF NOT EXISTS idx_sales_store_perf ON sales(store_id, quantity, total_amount);
CREATE INDEX IF NOT EXISTS idx_sales_date_perf ON sales(sale_date, quantity, total_amount);
CREATE INDEX IF NOT EXISTS idx_sales_product_perf ON sales(product_id, quantity, total_amount);
CREATE INDEX IF NOT EXISTS idx_sales_date_prod_agg ON sales(sale_date, product_id, quantity, total_amount);
CREATE INDEX IF NOT EXISTS idx_inventory_lookup ON inventory(store_id, product_id);
CREATE INDEX IF NOT EXISTS idx_stock_movements_prod ON stock_movements(product_id, store_id);
CREATE INDEX IF NOT EXISTS idx_restocks_prod_store ON restocks(product_id, store_id);
"""

def init_database(reset=False):
    """Create database and apply schema."""
    DB_DIR.mkdir(parents=True, exist_ok=True)

    if reset and DB_PATH.exists():
        print(f"Removing existing database at {DB_PATH.relative_to(BASE_DIR)}...")
        DB_PATH.unlink()

    print(f"Initializing database at: {DB_PATH.relative_to(BASE_DIR)}")
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.executescript(SCHEMA_SQL)
        conn.commit()

        # Query created tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables = [row[0] for row in cursor.fetchall()]
        print("\nTables created successfully:")
        for t in sorted(tables):
            cursor.execute(f"PRAGMA table_info({t});")
            cols = [c[1] for c in cursor.fetchall()]
            print(f"  - {t:<16} (columns: {', '.join(cols)})")

        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%';")
        indexes = [row[0] for row in cursor.fetchall()]
        print(f"\nIndexes created: {len(indexes)} indexes")
        for idx in sorted(indexes):
            print(f"  * {idx}")

    finally:
        conn.close()

if __name__ == "__main__":
    import sys
    should_reset = "--reset" in sys.argv
    init_database(reset=should_reset)
