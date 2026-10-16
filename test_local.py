import subprocess
def mock_bridge():
    cmd = "uptime"
    print(f"[+] Executing local mock command: {cmd}")
    out = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode("utf-8")
    print(f"[+] Output:\n{out.strip()}")
if __name__ == "__main__":
    mock_bridge()
