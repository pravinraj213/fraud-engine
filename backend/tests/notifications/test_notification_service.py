from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.config import Settings
from app.database import SessionLocal
from app.models import Notification
from app.repositories.assessments import get_by_transaction
from app.services.notification_service import notify_high_risk
from tests.api.helpers import post, travel_pair
from tests.fakes import FakeNotifier


def assessment_id(transaction_id: str) -> str:
    with SessionLocal() as s:
        return get_by_transaction(s, transaction_id).id


def notification_rows() -> list[Notification]:
    with SessionLocal() as s:
        return list(s.scalars(select(Notification)))


def test_second_call_sends_nothing(client: TestClient, notifier: FakeNotifier, settings: Settings) -> None:
    aid = assessment_id(travel_pair(client)["transaction"]["id"])  # first alert sent by the API
    notify_high_risk(aid, notifier, settings)
    notify_high_risk(aid, notifier, settings)
    assert len(notifier.sent) == 1
    assert len(notification_rows()) == 1


def test_non_high_assessment_is_ignored(client: TestClient, notifier: FakeNotifier, settings: Settings) -> None:
    aid = assessment_id(post(client, amount="150000.00")["transaction"]["id"])  # MEDIUM
    notify_high_risk(aid, notifier, settings)
    assert notifier.sent == [] and notification_rows() == []


def test_failure_is_recorded_not_raised(client: TestClient, settings: Settings) -> None:
    failing = FakeNotifier(fail_with="MessageRejected: Email address is not verified")
    client.app.state.notifier = failing
    detail = travel_pair(client)
    [row] = notification_rows()
    assert row.status == "FAILED" and "not verified" in row.error
    refreshed = client.get(f"/api/transactions/{detail['transaction']['id']}").json()
    assert refreshed["notification"]["status"] == "FAILED"
    assert client.get("/api/stats").json()["notifications"] == {"SENT": 0, "FAILED": 1}


def test_daily_limit_stops_sending(client: TestClient, notifier: FakeNotifier, settings: Settings) -> None:
    client.app.state.settings = settings.model_copy(update={"alert_daily_limit": 2})
    for account in ("ACC-A", "ACC-B", "ACC-C"):
        travel_pair(client, account)
    assert len(notifier.sent) == 2
    rows = sorted(notification_rows(), key=lambda r: r.status)
    assert [r.status for r in rows] == ["FAILED", "SENT", "SENT"]
    assert "Daily alert limit reached" in rows[0].error
    system = client.get("/api/system").json()
    assert system == {"notifier": "log", "alert_daily_limit": 2, "alerts_sent_24h": 2,
                      "medium_threshold": 40, "high_risk_threshold": 70,
                      "alert_recipients": [], "email_configured": False}


def test_unexpected_exception_is_swallowed(client: TestClient) -> None:
    class Exploding(FakeNotifier):
        def send_high_risk_alert(self, alert):
            raise RuntimeError("network down")

    client.app.state.notifier = Exploding()
    detail = travel_pair(client)  # the background task raises inside; the request still succeeds
    assert detail["assessment"]["risk_level"] == "HIGH"
    with SessionLocal() as s:
        assert s.scalar(select(func.count()).select_from(Notification)) == 1  # claim kept, no resend
