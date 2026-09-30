from fastapi.testclient import TestClient

from tests.api.helpers import post, travel_pair


def review(client: TestClient, txn_id: str, action: str, note: str | None = "checked"):
    return client.post(f"/api/transactions/{txn_id}/review",
                       json={"action": action, "reviewer": "Priya", "note": note})


def test_flagged_reviewed_cleared_writes_history(client: TestClient) -> None:
    txn_id = travel_pair(client)["transaction"]["id"]

    r1 = review(client, txn_id, "REVIEWED", "Called customer, card stolen")
    assert r1.status_code == 200
    assert r1.json()["assessment"]["status"] == "REVIEWED"
    assert r1.json()["allowed_actions"] == ["CLEARED"]

    r2 = review(client, txn_id, "CLEARED", "Customer was travelling after all")
    detail = r2.json()
    assert detail["assessment"]["status"] == "CLEARED" and detail["allowed_actions"] == []
    assert [(r["from_status"], r["to_status"]) for r in detail["reviews"]] == [
        ("REVIEWED", "CLEARED"), ("FLAGGED", "REVIEWED")]  # newest first
    assert detail["reviews"][1]["reviewer"] == "Priya"
    assert detail["reviews"][1]["note"] == "Called customer, card stolen"


def test_cleared_cannot_be_reviewed(client: TestClient) -> None:
    txn_id = travel_pair(client)["transaction"]["id"]
    review(client, txn_id, "CLEARED")
    r = review(client, txn_id, "REVIEWED")
    assert r.status_code == 409
    assert r.json()["detail"] == "Cannot mark a CLEARED transaction as REVIEWED"


def test_clean_transaction_cannot_be_reviewed(client: TestClient) -> None:
    txn_id = post(client)["transaction"]["id"]
    assert review(client, txn_id, "REVIEWED").status_code == 409


def test_unknown_transaction_404(client: TestClient) -> None:
    assert review(client, "missing", "CLEARED").status_code == 404


def test_review_validation(client: TestClient) -> None:
    txn_id = travel_pair(client)["transaction"]["id"]
    bad = [{"action": "APPROVE", "reviewer": "x"}, {"action": "CLEARED", "reviewer": ""},
           {"action": "CLEARED", "reviewer": "x", "note": "n" * 1001}]
    for payload in bad:
        assert client.post(f"/api/transactions/{txn_id}/review", json=payload).status_code == 422
