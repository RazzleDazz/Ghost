#!/usr/bin/env python3
"""
ghost_agent/agent.py
Hardened local security & telemetry auditor for Termux / Android ARM64.
Features:
  - SQLite WAL mode with flash-friendly pragmas & busy timeout
  - Cryptographic SHA-256 hash-chained audit log (tamper detection)
  - Rootless /proc/net socket & interface enumeration
  - Termux:API battery-aware throttling
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import socket
import sqlite3
import struct
import subprocess
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("GHOST_DB_PATH", BASE_DIR / "ghost_events.db"))
LOG_DIR = Path(os.environ.get("GHOST_LOG_DIR", BASE_DIR / "logs"))

SECURITY_BINARIES = (
    "nmap",
    "tcpdump",
    "openssl",
    "ssh",
    "gpg",
    "sqlite3",
    "git",
    "python3",
    "curl",
    "nc",
    "wg",
)

TCP_STATES = {
    "01": "ESTABLISHED",
    "02": "SYN_SENT",
    "03": "SYN_RECV",
    "04": "FIN_WAIT1",
    "05": "FIN_WAIT2",
    "06": "TIME_WAIT",
    "07": "CLOSE",
    "08": "CLOSE_WAIT",
    "09": "LAST_ACK",
    "0A": "LISTEN",
    "0B": "CLOSING",
}

GENESIS_HASH = "0" * 64


@contextmanager
def get_db_connection(db_path: Path = DB_PATH) -> Generator[sqlite3.Connection, None, None]:
    """Open a hardened SQLite connection configured for Android UFS flash and concurrency."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), timeout=10.0, isolation_level=None)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.execute("PRAGMA auto_vacuum=INCREMENTAL;")
        yield conn
    finally:
        conn.close()


def init_db(conn: sqlite3.Connection) -> None:
    """Initialize hash-chained audit tables and indexes."""
    conn.execute("BEGIN IMMEDIATE;")
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp_utc TEXT NOT NULL,
                event_type TEXT NOT NULL,
                host_node TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                prev_hash TEXT NOT NULL,
                event_hash TEXT NOT NULL UNIQUE
            );
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_audit_events_ts
            ON audit_events(timestamp_utc DESC);
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_audit_events_type
            ON audit_events(event_type);
            """
        )
        conn.execute("COMMIT;")
    except Exception:
        conn.execute("ROLLBACK;")
        raise


def compute_event_hash(
    timestamp_utc: str,
    event_type: str,
    host_node: str,
    payload_json: str,
    prev_hash: str,
) -> str:
    """Compute deterministic SHA-256 digest linking the current event to prev_hash."""
    canonical = f"{timestamp_utc}|{event_type}|{host_node}|{payload_json}|{prev_hash}"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def record_event(
    conn: sqlite3.Connection,
    event_type: str,
    payload: Dict[str, Any],
    timestamp_utc: Optional[str] = None,
) -> Dict[str, Any]:
    """Atomically append a tamper-evident event record to SQLite."""
    ts = timestamp_utc or datetime.now(timezone.utc).isoformat()
    host_node = os.uname().nodename
    payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))

    conn.execute("BEGIN IMMEDIATE;")
    try:
        row = conn.execute(
            "SELECT event_hash FROM audit_events ORDER BY id DESC LIMIT 1;"
        ).fetchone()
        prev_hash = row["event_hash"] if row else GENESIS_HASH
        event_hash = compute_event_hash(ts, event_type, host_node, payload_json, prev_hash)

        cursor = conn.execute(
            """
            INSERT INTO audit_events (
                timestamp_utc, event_type, host_node, payload_json, prev_hash, event_hash
            ) VALUES (?, ?, ?, ?, ?, ?);
            """,
            (ts, event_type, host_node, payload_json, prev_hash, event_hash),
        )
        event_id = cursor.lastrowid
        conn.execute("COMMIT;")
    except Exception:
        conn.execute("ROLLBACK;")
        raise

    return {
        "id": event_id,
        "timestamp_utc": ts,
        "event_type": event_type,
        "host_node": host_node,
        "prev_hash": prev_hash,
        "event_hash": event_hash,
    }


def verify_hash_chain(conn: sqlite3.Connection) -> Tuple[bool, int, Optional[str]]:
    """Verify full cryptographic integrity of audit_events from genesis to latest row."""
    rows = conn.execute(
        """
        SELECT id, timestamp_utc, event_type, host_node, payload_json, prev_hash, event_hash
        FROM audit_events
        ORDER BY id ASC;
        """
    ).fetchall()

    expected_prev = GENESIS_HASH
    for row in rows:
        if row["prev_hash"] != expected_prev:
            return (
                False,
                row["id"],
                f"Broken prev_hash link at id={row['id']}: expected {expected_prev}, got {row['prev_hash']}",
            )
        recomputed = compute_event_hash(
            row["timestamp_utc"],
            row["event_type"],
            row["host_node"],
            row["payload_json"],
            row["prev_hash"],
        )
        if recomputed != row["event_hash"]:
            return (
                False,
                row["id"],
                f"Payload tampering detected at id={row['id']}: expected {recomputed}, got {row['event_hash']}",
            )
        expected_prev = row["event_hash"]

    return True, len(rows), None


def _decode_ipv4_hex(hex_addr: str) -> str:
    ip_hex, port_hex = hex_addr.split(":")
    packed = bytes.fromhex(ip_hex)
    ip_str = socket.inet_ntoa(struct.pack("<I", int.from_bytes(packed, "big")))
    port = int(port_hex, 16)
    return f"{ip_str}:{port}"


def _decode_ipv6_hex(hex_addr: str) -> str:
    ip_hex, port_hex = hex_addr.split(":")
    words = [int(ip_hex[i : i + 8], 16) for i in range(0, 32, 8)]
    packed = struct.pack("<4I", *words)
    ip_str = socket.inet_ntop(socket.AF_INET6, packed)
    port = int(port_hex, 16)
    return f"[{ip_str}]:{port}"


def collect_sockets() -> List[Dict[str, str]]:
    """Enumerate local TCP/UDP sockets via /proc/net without requiring root."""
    sockets: List[Dict[str, str]] = []
    sources = (
        ("tcp", Path("/proc/net/tcp"), _decode_ipv4_hex),
        ("tcp6", Path("/proc/net/tcp6"), _decode_ipv6_hex),
        ("udp", Path("/proc/net/udp"), _decode_ipv4_hex),
    )

    for proto, proc_path, decoder in sources:
        if not proc_path.exists():
            continue
        try:
            lines = proc_path.read_text(encoding="utf-8").splitlines()[1:]
        except PermissionError:
            continue

        for line in lines:
            parts = line.split()
            if len(parts) < 4:
                continue
            local_ep = decoder(parts[1])
            remote_ep = decoder(parts[2])
            state_code = parts[3].upper()
            state_name = TCP_STATES.get(state_code, f"UNKNOWN_{state_code}")
            if proto == "udp" or state_name == "LISTEN":
                sockets.append(
                    {
                        "proto": proto,
                        "local": local_ep,
                        "remote": remote_ep,
                        "state": state_name,
                    }
                )
    return sockets


def collect_interfaces() -> List[Dict[str, Any]]:
    """Enumerate active network interfaces and byte counters from /proc/net/dev."""
    interfaces: List[Dict[str, Any]] = []
    dev_path = Path("/proc/net/dev")
    if not dev_path.exists():
        return interfaces

    try:
        lines = dev_path.read_text(encoding="utf-8").splitlines()[2:]
    except PermissionError:
        return interfaces

    for line in lines:
        if ":" not in line:
            continue
        iface_raw, stats_raw = line.split(":", 1)
        iface = iface_raw.strip()
        cols = stats_raw.split()
        if len(cols) < 10:
            continue
        rx_bytes = int(cols[0])
        tx_bytes = int(cols[8])
        if rx_bytes > 0 or tx_bytes > 0 or iface in ("lo", "wlan0", "tun0"):
            interfaces.append(
                {
                    "interface": iface,
                    "rx_bytes": rx_bytes,
                    "tx_bytes": tx_bytes,
                }
            )
    return interfaces


def collect_security_binaries() -> Dict[str, Optional[str]]:
    """Locate available security and diagnostic binaries in PATH."""
    return {binary: shutil.which(binary) for binary in SECURITY_BINARIES}


def get_battery_telemetry() -> Optional[Dict[str, Any]]:
    """Query Termux:API battery status safely with a strict 2-second timeout."""
    if not shutil.which("termux-battery-status"):
        return None
    try:
        proc = subprocess.run(
            ["termux-battery-status"],
            capture_output=True,
            text=True,
            timeout=2.0,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            data = json.loads(proc.stdout)
            return {
                "percentage": data.get("percentage"),
                "status": data.get("status"),
                "temperature": data.get("temperature"),
            }
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        return None
    return None


def run_audit(db_path: Path = DB_PATH, log_dir: Path = LOG_DIR) -> Dict[str, Any]:
    """Execute a full security audit sweep and persist results to SQLite and JSON log."""
    battery = get_battery_telemetry()
    throttled = bool(
        battery
        and isinstance(battery.get("percentage"), int)
        and battery["percentage"] < 20
        and battery.get("status") != "CHARGING"
    )

    payload: Dict[str, Any] = {
        "throttled_low_battery": throttled,
        "battery": battery,
        "interfaces": collect_interfaces(),
        "listening_sockets": [] if throttled else collect_sockets(),
        "binaries": collect_security_binaries(),
    }

    with get_db_connection(db_path) as conn:
        init_db(conn)
        meta = record_event(conn, "security_audit", payload)

    log_dir.mkdir(parents=True, exist_ok=True)
    ts_slug = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_file = log_dir / f"audit_{ts_slug}.json"
    output = {**meta, "payload": payload}
    log_file.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    return output


def main(argv: Optional[List[str]] = None) -> int:
    parser = parse_args(argv) if False else argparse.ArgumentParser(description="Ghost Agent Local Security Auditor")
    parser.add_argument(
        "--verify-chain",
        action="store_true",
        help="Verify SHA-256 hash chain integrity of ghost_events.db",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DB_PATH,
        help="Path to SQLite database file",
    )
    args = parser.parse_args(argv)

    with get_db_connection(args.db) as conn:
        init_db(conn)
        if args.verify_chain:
            valid, count, error = verify_hash_chain(conn)
            if valid:
                print(f"[OK] Hash chain verified across {count} event(s).")
                return 0
            print(f"[ALERT] {error}", file=sys.stderr)
            return 2

    result = run_audit(db_path=args.db)
    print(
        f"[OK] Recorded event #{result['id']} ({result['event_type']}) "
        f"hash={result['event_hash'][:12]}..."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())


def run_cmd_check(name: str, cmd: list[str], dry_run: bool = False, timeout: int = 15) -> str:
    """Backward-compatible command check helper for ghost_agent callers."""
    if dry_run:
        return f"[DRY-RUN] {name}: {' '.join(cmd)}"
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=float(timeout),
            check=False,
        )
        out = (proc.stdout or proc.stderr or "").strip()
        return f"[{name}] rc={proc.returncode}: {out[:300]}"
    except Exception as exc:
        return f"[{name}] error: {exc}"


def check_security_binaries(dry_run: bool = False) -> str:
    """Backward-compatible summary of available security binaries."""
    found = collect_security_binaries()
    present = [k for k, v in found.items() if v]
    if dry_run:
        return f"[DRY-RUN] binaries ({len(present)}/{len(found)})"
    return f"binaries available ({len(present)}/{len(found)}): {', '.join(present)}"


def check_storage_metrics(dry_run: bool = False) -> str:
    """Backward-compatible storage usage summary for Termux/Android."""
    if dry_run:
        return "[DRY-RUN] storage metrics"
    usage = shutil.disk_usage(str(BASE_DIR))
    free_gb = usage.free / (1024 ** 3)
    total_gb = usage.total / (1024 ** 3)
    return f"storage free={free_gb:.2f}GB / total={total_gb:.2f}GB"


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Backward-compatible CLI argument parser."""
    parser = argparse.ArgumentParser(description="Ghost Agent Local Security Auditor")
    parser.add_argument(
        "--verify-chain",
        action="store_true",
        help="Verify SHA-256 hash chain integrity of ghost_events.db",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DB_PATH,
        help="Path to SQLite database file",
    )
    return parser.parse_args(argv)
