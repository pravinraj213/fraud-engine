from datetime import timedelta
from typing import Any

from fastapi.testclient import TestClient

from tests.fakes import CITIES, NOW


def body(city: str = "Chennai, IN", minutes: float = 0, **overrides: Any) -> dict[str, Any]:
    lat, lon = CITIES[city]
    return {"account_id": "ACC-1", "amount": "1000.00", "currency": "INR", "merchant": "Test Store",
            "latitude": lat, "longitude": lon, "location_label": city,
            "occurred_at": (NOW + timedelta(minutes=minutes)).isoformat()} | overrides


def post(client: TestClient, **kw: Any) -> dict[str, Any]:
    r = client.post("/api/transactions", json=body(**kw))
    assert r.status_code == 201, r.text
    return r.json()


def travel_pair(client: TestClient, account: str = "ACC-1") -> dict[str, Any]:
    post(client, city="Chennai, IN", minutes=-45, account_id=account)
    return post(client, city="London, GB", account_id=account)
