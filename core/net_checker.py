import socket
import sys

def check_loopback():
    print("[*] Auditing local loopback interfaces...")
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        result = s.connect_ex(('127.0.0.1', 80))
        s.close()
        print(f"[*] Loopback socket status check completed (Exit code: {result})")
    except Exception as e:
        print(f"[!] Network check exception: {e}")

if __name__ == "__main__":
    check_loopback()
