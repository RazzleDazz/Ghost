from pathlib import Path

import agent


def test_hash_chain_integrity_and_tamper_detection(tmp_path: Path) -> None:
    db_file = tmp_path / "test_ghost.db"
    log_dir = tmp_path / "logs"

    first = agent.run_audit(db_path=db_file, log_dir=log_dir)
    second = agent.run_audit(db_path=db_file, log_dir=log_dir)

    assert first["prev_hash"] == agent.GENESIS_HASH
    assert second["prev_hash"] == first["event_hash"]

    with agent.get_db_connection(db_file) as conn:
        valid, count, err = agent.verify_hash_chain(conn)
        assert valid is True
        assert count == 2
        assert err is None

        conn.execute(
            "UPDATE audit_events SET payload_json = '{\"tampered\":true}' WHERE id = 1;"
        )
        valid_after, bad_id, err_after = agent.verify_hash_chain(conn)
        assert valid_after is False
        assert bad_id == 1
        assert err_after is not None
        assert "tampering detected" in err_after


def test_ipv4_hex_decoder() -> None:
    decoded = agent._decode_ipv4_hex("0100007F:1F90")
    assert decoded == "127.0.0.1:8080"
