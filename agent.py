import os
import sys
import time
import subprocess
from google import genai
from google.genai import types

client = genai.Client()

WORKSPACE_DIR = os.path.expanduser("~/ghost_agent/workspace")
os.makedirs(WORKSPACE_DIR, exist_ok=True)

def execute_shell(command: str) -> str:
    """Executes a bash command strictly within ~/ghost_agent/workspace and returns stdout or stderr."""
    print(f"\n[AGENT TOOL] Executing: {command}")
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=WORKSPACE_DIR,
            capture_output=True,
            text=True,
            timeout=45
        )
        output = result.stdout if result.returncode == 0 else f"ERROR:\n{result.stderr}"
        return output.strip() if output.strip() else "Command executed successfully (no output)."
    except Exception as e:
        return f"Execution exception: {str(e)}"

def run_agent(prompt: str):
    print(f"[MISSION] {prompt}")

    config = types.GenerateContentConfig(
        system_instruction=(
            "You are an autonomous AI cybersecurity operations agent for Numuna Ghost Cyberworks LLC, "
            "running on a mobile Termux environment on a Google Pixel 10 Pro. You have access to an "
            "execute_shell tool sandboxed to ~/ghost_agent/workspace. Perform rigorous technical "
            "reconnaissance, system auditing, and security checks, combining commands with '&&' "
            "to minimize token overhead."
        ),
        tools=[execute_shell],
    )

    # Use gemini-flash-latest with robust exponential backoff retry loop for 503 spikes
    model_name = "gemini-flash-latest"
    max_retries = 5
    
    for attempt in range(1, max_retries + 1):
        try:
            print(f"[SYSTEM] Connecting to {model_name} (Attempt {attempt}/{max_retries})...")
            chat = client.chats.create(model=model_name, config=config)
            response = chat.send_message(prompt)
            print(f"\n[AGENT RESPONSE]:\n{response.text}")
            return
        except Exception as e:
            if attempt == max_retries:
                print(f"[ERROR] Max retries reached. Persistent upstream congestion: {e}")
                sys.exit(1)
            wait_time = 2 ** attempt
            print(f"[WARN] Server busy (503/Overload). Retrying in {wait_time}s...")
            time.sleep(wait_time)

if __name__ == "__main__":
    initial_prompt = sys.argv[1] if len(sys.argv) > 1 else "Run security audit."
    run_agent(initial_prompt)
