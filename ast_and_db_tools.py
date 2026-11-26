#!/usr/bin/env python3
"""AST safety scanner & SQLite WAL checkpoint/vacuum utility for ghost_agent."""

from __future__ import annotations

import ast
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "ghost_events.db"

RISKY_CALLS = {"eval", "exec", "compile", "__import__"}
RISKY_ATTRS = {("os", "system"), ("subprocess", "Popen"), ("pickle", "loads")}


def scan_python_ast(target_dir: Path = BASE_DIR) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    for py_file in sorted(target_dir.glob("*.py")):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in RISKY_CALLS:
                    findings.append({"file": py_file.name, "line": node.lineno, "call": node.func.id})
                elif isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                    pair = (node.func.value.id, node.func.attr)
                    if pair in RISKY_ATTRS:
                        findings.append({"file": py_file.name, "line": node.lineno, "call": f"{pair[0]}.{pair[1]}"})
    return findings


def maintain_sqlite(db_path: Path = DB_PATH) -> Dict[str, Any]:
    conn = sqlite3.connect(str(db_path), timeout=10.0)
    try:
        wal_res = conn.execute("PRAGMA wal_checkpoint(TRUNCATE);").fetchone()
        conn.execute("PRAGMA incremental_vacuum(50);")
        integrity = conn.execute("PRAGMA integrity_check;").fetchone()[0]
        return {"wal_checkpoint": list(wal_res) if wal_res else [], "integrity": integrity}
    finally:
        conn.close()


if __name__ == "__main__":
    print(json.dumps({"ast_findings": scan_python_ast(), "db_maintenance": maintain_sqlite()}, indent=2))
