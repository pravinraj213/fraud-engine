import pytest
from fastapi.testclient import TestClient

from tests.api.helpers import body, post, travel_pair
from tests.fakes import FakeNotifier


def test_health(client: TestClient) -> None:
    assert client.get("/api/health").json() == {"status": "ok"}


def test_normal_transaction_is_clean_and_not_in_queue(client: TestClient) -> None:
    detail = post(client)
    assert detail["assessment"]["status"] == "CLEAN"
    assert detail["assessment"]["risk_level"] == "NONE"
    assert detail["rule_hits"] == [] and detail["notification"] is None
    assert detail["transaction"]["amount"] == "1000.00"            # money as a string
    assert detail["transaction"]["occurred_at"].endswith("Z")      # ISO 8601 UTC
    assert client.get("/api/flags").json() == {"items": [], "total": 0}


def test_travel_pair_is_high_first_in_queue_and_alerts_once(client: TestClient, notifier: FakeNotifier) -> None:
    post(client, account_id="ACC-9", amount="50000.00")  # cold start, below threshold: CLEAN
    post(client, account_id="ACC-8", amount="150000.00")  # cold start: MEDIUM
    high = travel_pair(client)
    assert high["assessment"]["risk_level"] == "HIGH" and high["assessment"]["total_score"] == 90
    assert high["rule_hits"][0]["rule_name"] == "impossible_travel"
    assert high["rule_hits"][0]["weighted_score"] == 90

    items = client.get("/api/flags").json()["items"]
    assert [i["transaction_id"] for i in items][0] == high["transaction"]["id"]
    assert items[0]["notification_status"] == "SENT"
    assert len(notifier.sent) == 1 and notifier.sent[0].transaction_id == high["transaction"]["id"]
    assert notifier.sent[0].console_url == f"http://console.test/transactions/{high['transaction']['id']}"

    detail = client.get(f"/api/transactions/{high['transaction']['id']}").json()
    assert detail["notification"]["status"] == "SENT"
    assert detail["allowed_actions"] == ["REVIEWED", "CLEARED"]


@pytest.mark.parametrize("override", [
    {"amount": "-5"}, {"amount": "0"}, {"latitude": 95}, {"amount": "10.005"},
    {"merchant": ""}, {"currency": "inr"}, {"account_id": "x" * 65},
])
def test_validation_errors(client: TestClient, override: dict) -> None:
    assert client.post("/api/transactions", json=body(**override)).status_code == 422


def test_naive_timestamp_treated_as_utc(client: TestClient) -> None:
    detail = post(client, occurred_at="2026-10-01T09:15:00")
    assert detail["transaction"]["occurred_at"] == "2026-10-01T09:15:00Z"


def test_missing_timestamp_defaults_to_now(client: TestClient) -> None:
    b = body()
    del b["occurred_at"]
    assert client.post("/api/transactions", json=b).status_code == 201


def test_unknown_transaction_404(client: TestClient) -> None:
    assert client.get("/api/transactions/nope").status_code == 404


def test_rules_endpoint_lists_three_rules(client: TestClient) -> None:
    names = {r["name"] for r in client.get("/api/rules").json()}
    assert {"velocity", "unusual_amount", "impossible_travel"} <= names
