#!/usr/bin/env python3
"""
ghost_agent/mock_server.py
Zero-dependency local HTTP mock server for offline/fallback testing on Termux.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class MockGhostHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _send_json(self, status_code: int, payload: dict) -> None:
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:
        if self.path in ("/health", "/v1/health"):
            self._send_json(
                200,
                {
                    "status": "ok",
                    "mode": "offline_mock",
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                },
            )
            return
        self._send_json(404, {"error": "not_found", "path": self.path})

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        body_bytes = self.rfile.read(length) if length > 0 else b"{}"
        try:
            parsed = json.loads(body_bytes.decode("utf-8"))
        except json.JSONDecodeError:
            parsed = {"raw": body_bytes.decode("utf-8", errors="replace")}

        self._send_json(
            200,
            {
                "accepted": True,
                "mode": "offline_mock",
                "echo": parsed,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            },
        )

    def log_message(self, format: str, *args: object) -> None:
        return


def run_server(host: str = "127.0.0.1", port: int = 8787) -> None:
    server = ThreadingHTTPServer((host, port), MockGhostHandler)
    server.daemon_threads = True
    try:
        server.serve_forever(poll_interval=0.5)
    finally:
        server.server_close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ghost Agent Local Offline Mock Server")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8787, help="Bind port (default: 8787)")
    args = parser.parse_args(argv)
    print(f"[MOCK] Listening on http://{args.host}:{args.port}")
    run_server(args.host, args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
