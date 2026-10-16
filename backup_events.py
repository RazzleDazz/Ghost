import os
import shutil
from datetime import datetime

db_path = "ghost_events.db"
backup_dir = "backups"

os.makedirs(backup_dir, exist_ok=True)
if os.path.exists(db_path):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, f"ghost_events_{timestamp}.db")
    shutil.copy2(db_path, backup_path)
    print(f"[+] Database backed up to {backup_path}")
else:
    print("[-] Database not found.")
