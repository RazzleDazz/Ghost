import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import autonomous_bridge
import test_local


class _OKHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        if length > 0:
            self.rfile.read(length)
        body = b'{"accepted":true}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


def test_backoff_bounds() -> None:
    d0 = autonomous_bridge.compute_backoff_seconds(0, base_delay=0.2, max_delay=2.0, jitter=0.1)
    d2 = autonomous_bridge.compute_backoff_seconds(2, base_delay=0.2, max_delay=2.0, jitter=0.1)
    assert 0.2 <= d0 <= 0.31
    assert 0.8 <= d2 <= 0.91


def test_offline_failover_and_audit_log(tmp_path: Path) -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _OKHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        mock_url = f"http://127.0.0.1:{port}/v1/bridge"
        audit_file = tmp_path / "bridge_audit.log"

        res = autonomous_bridge.dispatch_with_failover(
            payload={"cmd": "status"},
            primary_url="http://127.0.0.1:1/unreachable",
            fallback_url=mock_url,
            max_retries=1,
            base_delay=0.01,
            max_delay=0.02,
            timeout=0.5,
            audit_log_path=audit_file,
            sleep_fn=lambda _: None,
        )

        assert res["delivered"] is True
        assert res["mode"] == "offline_mock_fallback"
        assert audit_file.exists()

        lines = audit_file.read_text(encoding="utf-8").strip().splitlines()
        parsed = [json.loads(line) for line in lines]
        assert any(item["event"] == "bridge_dispatch_retry" for item in parsed)
        assert parsed[-1]["event"] == "bridge_dispatch_ok"
    finally:
        server.shutdown()
        server.server_close()


def test_local_module_contract() -> None:
    test_local.test_build_payload_request_contract()
