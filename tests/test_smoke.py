from backend.main import health_check


def test_health() -> None:
    payload = health_check()
    assert payload["status"] == "ok"
    assert "db_ok" in payload
    assert "now" in payload
    assert "latest_ts" in payload
