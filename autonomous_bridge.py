#!/usr/bin/env python3
"""
ghost_agent/autonomous_bridge.py
Resilient bridge dispatcher for Termux / Android ARM64.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

BASE_DIR = Path(__file__).resolve().parent
AUDIT_LOG_PATH = Path(os.environ.get("GHOST_BRIDGE_AUDIT_LOG", BASE_DIR / "bridge_audit.log"))
DEFAULT_MOCK_URL = "http://127.0.0.1:8787/v1/bridge"


def compute_backoff_seconds(
    attempt: int,
    base_delay: float = 0.5,
    max_delay: float = 8.0,
    jitter: float = 0.25,
) -> float:
    exp_delay = min(base_delay * (2 ** max(attempt, 0)), max_delay)
    return round(exp_delay + random.uniform(0.0, max(jitter, 0.0)), 4)


def append_bridge_audit(
    entry: Dict[str, Any],
    log_path: Path = AUDIT_LOG_PATH,
) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        **entry,
    }
    line = (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    fd = os.open(str(log_path), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        os.write(fd, line)
    finally:
        os.close(fd)


class _HTTPResult:
    def __init__(self, status: int, body: str, latency_ms: float) -> None:
        self.status = status
        self.body = body
        self.latency_ms = latency_ms


def _post_json(url: str, payload: Dict[str, Any], timeout: float = 3.0) -> _HTTPResult:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    start = time.monotonic()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8", errors="replace")
        latency_ms = round((time.monotonic() - start) * 1000.0, 2)
        return _HTTPResult(status=resp.status, body=body, latency_ms=latency_ms)


def dispatch_with_failover(
    payload: Dict[str, Any],
    primary_url: Optional[str] = None,
    fallback_url: str = DEFAULT_MOCK_URL,
    max_retries: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 8.0,
    timeout: float = 3.0,
    audit_log_path: Path = AUDIT_LOG_PATH,
    sleep_fn: Any = time.sleep,
) -> Dict[str, Any]:
    targets: list[tuple[str, str]] = []
    if primary_url:
        targets.append(("primary", primary_url))
    if fallback_url:
        targets.append(("offline_mock_fallback", fallback_url))

    last_error = "no_target_configured"

    for mode, url in targets:
        for attempt in range(max_retries):
            try:
                resp = _post_json(url, payload, timeout=timeout)
                if 200 <= resp.status < 300:
                    result = {
                        "delivered": True,
                        "mode": mode,
                        "url": url,
                        "attempt": attempt + 1,
                        "status": resp.status,
                        "latency_ms": resp.latency_ms,
                    }
                    append_bridge_audit({"event": "bridge_dispatch_ok", **result}, audit_log_path)
                    return result
                last_error = f"http_{resp.status}"
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                last_error = str(exc)

            append_bridge_audit(
                {
                    "event": "bridge_dispatch_retry",
                    "mode": mode,
                    "url": url,
                    "attempt": attempt + 1,
                    "max_retries": max_retries,
                    "error": last_error,
                },
                audit_log_path,
            )

            if attempt < max_retries - 1:
                delay = compute_backoff_seconds(
                    attempt=attempt,
                    base_delay=base_delay,
                    max_delay=max_delay,
                )
                sleep_fn(delay)

    fail_result = {
        "delivered": False,
        "mode": "exhausted",
        "fallback_url": fallback_url,
        "error": last_error,
    }
    append_bridge_audit({"event": "bridge_dispatch_failed", **fail_result}, audit_log_path)
    return fail_result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ghost Agent Autonomous Bridge")
    parser.add_argument(
        "--message",
        default="heartbeat",
        help="Payload message to dispatch through the bridge",
    )
    parser.add_argument(
        "--primary-url",
        default=os.environ.get("GHOST_PRIMARY_URL", ""),
        help="Optional primary endpoint URL",
    )
    parser.add_argument(
        "--fallback-url",
        default=os.environ.get("GHOST_MOCK_URL", DEFAULT_MOCK_URL),
        help="Offline mock server URL (default: http://127.0.0.1:8787/v1/bridge)",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=2,
        help="Retry attempts per target before failover",
    )
    args = parser.parse_args(argv)

    outcome = dispatch_with_failover(
        payload={"message": args.message, "source": "autonomous_bridge"},
        primary_url=args.primary_url or None,
        fallback_url=args.fallback_url,
        max_retries=args.max_retries,
    )
    print(json.dumps(outcome))
    return 0 if outcome["delivered"] else 1


if __name__ == "__main__":
    sys.exit(main())
