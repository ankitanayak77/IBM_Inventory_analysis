import sqlite3

conn = sqlite3.connect("database/inventory.db")
indexes = conn.execute("SELECT name, sql FROM sqlite_master WHERE type='index' AND tbl_name='sales'").fetchall()
for name, sql in indexes:
    print(f"{name}: {sql}")
