import sqlite3
import os

db_path = "ghost_events.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM events WHERE timestamp < datetime('now', '-30 days');")
    deleted_rows = cursor.rowcount
    conn.commit()
    conn.execute("VACUUM")
    conn.close()
    print(f"[+] Pruned {deleted_rows} old event records and vacuumed database.")
else:
    print("[-] Database not found.")
