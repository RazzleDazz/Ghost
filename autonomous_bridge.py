import os
import urllib.request
import urllib.error
import json
import subprocess
import time
from datetime import datetime

API_KEY = os.environ.get("GEMINI_API_KEY")
URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={API_KEY}"
LOG_FILE = "bridge_audit.log"
ALLOWED_COMMANDS = ["uname", "uptime", "date", "df", "free"]

def log_event(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] {message}\n"
    print(entry.strip())
    with open(LOG_FILE, "a") as f:
        f.write(entry)

def execute_bridge():
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{
            "parts": [{
                "text": "Return a JSON object with a single key 'command' containing a safe bash command like 'uptime' or 'none'."
            }]
        }]
    }

    try:
        req = urllib.request.Request(URL, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req) as response:
            res = json.loads(response.read().decode("utf-8"))
            raw = res["candidates"][0]["content"]["parts"][0]["text"].strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            raw = raw.strip()
            cmd = json.loads(raw).get("command", "none")
            log_event(f"Received instruction: {cmd}")

            base_cmd = cmd.split()[0] if cmd else ""
            if base_cmd in ALLOWED_COMMANDS:
                out = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode("utf-8")
                log_event(f"Execution Output:\n{out.strip()}")
            elif cmd == "none":
                log_event("No remote action required.")
            else:
                log_event(f"Blocked unauthorized command: {cmd}")
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        log_event(f"HTTP Error {e.code}: {err_body}")
    except Exception as e:
        log_event(f"Execution failed: {e}")

if __name__ == "__main__":
    log_event("Starting live production autonomous bridge daemon...")
    execute_bridge()
