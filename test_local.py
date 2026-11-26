#!/usr/bin/env python3
"""
ghost_agent/test_local.py
Local endpoint payload probe compatible with both direct execution and pytest.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, Tuple


def build_payload_request(
    target_url: str,
    command_text: str,
    timeout: float = 2.0,
) -> Tuple[urllib.request.Request, float]:
    body = json.dumps({"command": command_text, "source": "ghost_agent_local_test"}).encode(
        "utf-8"
    )
    req = urllib.request.Request(
        target_url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    return req, timeout


def test_payload(
    command_text: str,
    target_url: str | None = None,
    timeout: float = 2.0,
) -> Dict[str, Any]:
    url = target_url or os.environ.get("GHOST_TARGET_URL", "http://127.0.0.1:8787/health")
    req, req_timeout = build_payload_request(url, command_text, timeout=timeout)
    try:
        with urllib.request.urlopen(req, timeout=req_timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
            return {
                "ok": True,
                "command": command_text,
                "status": response.status,
                "response": raw[:300],
            }
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {
            "ok": False,
            "command": command_text,
            "status": None,
            "error": str(exc),
        }


def test_build_payload_request_contract() -> None:
    req, timeout = build_payload_request("http://127.0.0.1:8787/v1/dispatch", "uptime", timeout=1.5)
    assert req.full_url == "http://127.0.0.1:8787/v1/dispatch"
    assert req.get_method() == "POST"
    assert timeout == 1.5
    parsed = json.loads((req.data or b"{}").decode("utf-8"))
    assert parsed["command"] == "uptime"


if __name__ == "__main__":
    for cmd in ("uptime", "df -h"):
        res = test_payload(cmd)
        if res["ok"]:
            print(f"[+] Tested payload '{cmd}': HTTP {res['status']} -> {res['response']}")
        else:
            print(f"[-] Tested payload '{cmd}': Offline/Unreachable -> {res['error']}")
