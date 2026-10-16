import json
import os
from datetime import datetime

LOG_FILE = "audit.json"

def log_event(event_type, details):
    entry = {
        "timestamp": datetime.now().isoformat(),
        "event": event_type,
        "details": details
    }
    logs = []
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r") as f:
                logs = json.load(f)
        except json.JSONDecodeError:
            logs = []
    logs.append(entry)
    with open(LOG_FILE, "w") as f:
        json.dump(logs, f, indent=4)
    print(f"[*] Audit event logged: {event_type}")

if __name__ == "__main__":
    log_event("TEST_EVENT", {"status": "success"})
