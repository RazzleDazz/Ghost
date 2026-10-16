import urllib.request
import json

URL = "http://127.0.0.1:8080"

def test_payload(command_text):
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{
            "parts": [{
                "text": json.dumps({"command": command_text})
            }]
        }]
    }
    req = urllib.request.Request(URL, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as response:
            print(f"[+] Tested payload '{command_text}': Success")
    except Exception as e:
        print(f"[-] Tested payload '{command_text}': Failed -> {e}")

if __name__ == "__main__":
    test_payload("uptime")
    test_payload("rm -rf /")
    test_payload("df -h")
