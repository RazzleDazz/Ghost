from pathlib import Path
import sqlite3

import ast_and_db_tools


def test_scan_python_ast_detects_risky_calls(tmp_path: Path) -> None:
    clean_file = tmp_path / "clean_mod.py"
    clean_file.write_text("def add(a: int, b: int) -> int:\n    return a + b\n", encoding="utf-8")

    risky_file = tmp_path / "risky_mod.py"
    risky_file.write_text(
        "import os\ndef run_bad(cmd: str) -> None:\n    eval('1+1')\n    os.system(cmd)\n",
        encoding="utf-8",
    )

    findings = ast_and_db_tools.scan_python_ast(tmp_path)
    calls = {(item["file"], item["call"]) for item in findings}
    assert ("risky_mod.py", "eval") in calls
    assert ("risky_mod.py", "os.system") in calls
    assert all(item["file"] != "clean_mod.py" for item in findings)


def test_maintain_sqlite_wal_and_integrity(tmp_path: Path) -> None:
    db_file = tmp_path / "test_events.db"
    conn = sqlite3.connect(str(db_file))
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("CREATE TABLE IF NOT EXISTS sample (id INTEGER PRIMARY KEY, val TEXT);")
        conn.execute("INSERT INTO sample (val) VALUES ('ok');")
        conn.commit()
    finally:
        conn.close()

    report = ast_and_db_tools.maintain_sqlite(db_file)
    assert report["integrity"] == "ok"
    assert isinstance(report["wal_checkpoint"], list)
