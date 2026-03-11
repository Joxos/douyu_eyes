import os
import pytest

from fastapi.testclient import TestClient


try:
    from backend.main import app
except Exception:
    app = None


DYKIT_DSN = os.getenv("DYKIT_DSN")


@pytest.fixture(scope="session")
def client():
    if app is None:
        pytest.skip("backend.app not available; skipping API tests")
    return TestClient(app)


def _skip_if_no_dykit():
    if not DYKIT_DSN:
        pytest.skip("DYKIT_DSN not set; skipping DB-backed tests")


def test_smoke_health_endpoint(client):
    # keep existing minimal smoke test style
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)
    assert "status" in data


def test_search_endpoint_basic_success(client):
    # skip heavy DB tests if no DSN
    _skip_if_no_dykit()

    resp = client.get("/api/search", params={"q": "test"})
    assert resp.status_code == 200
    data = resp.json()
    # shape assertions
    assert isinstance(data, dict)
    assert "items" in data and isinstance(data["items"], list)
    assert "limit" in data and isinstance(data["limit"], int)
    assert "offset" in data and isinstance(data["offset"], int)
    assert "total" in data and isinstance(data["total"], int)
    assert "total_pages" in data and isinstance(data["total_pages"], int)
    assert "current_page" in data and isinstance(data["current_page"], int)


def test_search_endpoint_sort_modes(client):
    _skip_if_no_dykit()

    by_count = client.get("/api/search", params={"q": "比赛", "limit": 10, "offset": 0, "sort": "count"})
    by_last_seen = client.get("/api/search", params={"q": "比赛", "limit": 10, "offset": 0, "sort": "last_seen"})
    assert by_count.status_code == 200
    assert by_last_seen.status_code == 200
    assert isinstance(by_count.json().get("items", []), list)
    assert isinstance(by_last_seen.json().get("items", []), list)


def test_search_endpoint_invalid_sort_bad_request(client):
    resp = client.get("/api/search", params={"q": "比赛", "sort": "unknown"})
    assert resp.status_code == 400


def test_search_endpoint_returns_deduplicated_items(client):
    _skip_if_no_dykit()

    resp = client.get("/api/search", params={"q": "比赛", "limit": 20, "offset": 0})
    assert resp.status_code == 200
    data = resp.json()
    items = data.get("items", [])
    assert isinstance(items, list)
    assert len(items) == len(set(items))


def test_search_endpoint_empty_query_bad_request(client):
    resp = client.get("/api/search", params={"q": ""})
    assert resp.status_code == 400


def test_search_endpoint_overflow_keywords_bad_request(client):
    # construct an input that is likely to be considered too many tokens
    long_q = " ".join(["k"] * 1000)
    resp = client.get("/api/search", params={"q": long_q})
    # server validates and converts parse errors to 400
    assert resp.status_code == 400


def test_stats_summary_and_current_minute(client):
    _skip_if_no_dykit()

    resp = client.get("/api/stats/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)
    # expected keys
    assert "unique_count_all_time" in data
    assert "current_minute_count" in data
    assert "top20" in data and isinstance(data["top20"], list)
    # top20 items should be objects with content and count when present
    if data["top20"]:
        item = data["top20"][0]
        assert isinstance(item, dict)
        assert "content" in item
        assert "count" in item and isinstance(item["count"], int)

    # current minute endpoint
    resp2 = client.get("/api/stats/current-minute")
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert isinstance(data2, dict)
    assert "minute_start" in data2 and "minute_end" in data2 and "count" in data2


def test_random_endpoint_returns_content(client):
    _skip_if_no_dykit()

    resp = client.get("/api/random")
    # random may 404 if no content; treat 404 as acceptable but non-failing
    if resp.status_code == 404:
        pytest.skip("No random content in DB")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)
    assert "content" in data
    assert isinstance(data["content"], str) and data["content"].strip() != ""
