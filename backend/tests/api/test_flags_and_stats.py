import pytest
from fastapi.testclient import TestClient

from tests.api.helpers import post, travel_pair


@pytest.fixture
def seeded(client: TestClient) -> dict[str, str]:
    """HIGH (travel, ACC-1), MEDIUM (cold start, ACC-2), MEDIUM (cold start, ACC-3, reviewed), CLEAN."""
    high = travel_pair(client, "ACC-1")["transaction"]["id"]
    med = post(client, account_id="ACC-2", amount="150000.00", minutes=-30)["transaction"]["id"]
    reviewed = post(client, account_id="ACC-3", amount="200000.00", minutes=-20)["transaction"]["id"]
    client.post(f"/api/transactions/{reviewed}/review", json={"action": "REVIEWED", "reviewer": "Priya"})
    post(client, account_id="ACC-4")
    return {"high": high, "medium": med, "reviewed": reviewed}


def ids(client: TestClient, **params) -> list[str]:
    return [i["transaction_id"] for i in client.get("/api/flags", params=params).json()["items"]]


def test_default_queue_is_flagged_by_score(client: TestClient, seeded: dict) -> None:
    assert ids(client) == [seeded["high"], seeded["medium"]]


def test_status_filters(client: TestClient, seeded: dict) -> None:
    assert ids(client, status="REVIEWED") == [seeded["reviewed"]]
    assert ids(client, status="CLEARED") == []
    assert set(ids(client, status="ALL")) == set(seeded.values())


def test_level_account_and_sort(client: TestClient, seeded: dict) -> None:
    assert ids(client, risk_level="HIGH") == [seeded["high"]]
    assert ids(client, account_id="ACC-2") == [seeded["medium"]]
    assert ids(client, sort="newest") == [seeded["high"], seeded["medium"]]
    assert ids(client, status="ALL", sort="newest") == [seeded["high"], seeded["reviewed"], seeded["medium"]]


def test_limit_offset_and_total(client: TestClient, seeded: dict) -> None:
    page = client.get("/api/flags", params={"status": "ALL", "limit": 1, "offset": 1}).json()
    assert page["total"] == 3 and len(page["items"]) == 1


def test_bad_filters_422(client: TestClient) -> None:
    for params in ({"status": "CLEAN"}, {"risk_level": "EXTREME"}, {"limit": 0}, {"limit": 201}, {"sort": "x"}):
        assert client.get("/api/flags", params=params).status_code == 422


def test_stats(client: TestClient, seeded: dict) -> None:
    assert client.get("/api/stats").json() == {
        "by_status": {"CLEAN": 2, "FLAGGED": 2, "REVIEWED": 1, "CLEARED": 0},  # 2 CLEAN: Chennai leg + ACC-4
        "flagged_by_level": {"LOW": 0, "MEDIUM": 1, "HIGH": 1},
        "notifications": {"SENT": 1, "FAILED": 0},
    }
