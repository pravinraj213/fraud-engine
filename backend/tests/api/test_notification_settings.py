from unittest.mock import patch

from fastapi.testclient import TestClient

from app.config import Settings
from app.notifications.log import LogNotifier
from tests.api.helpers import travel_pair
from tests.fakes import FakeNotifier


def test_settings_expose_configured_recipients(client: TestClient, settings: Settings) -> None:
    settings.alert_recipient_email = "reviewer@example.com"
    settings.ses_sender_email = "alerts@example.com"
    result = client.get("/api/system").json()
    assert result["alert_recipients"] == ["reviewer@example.com"]
    assert result["email_configured"] is True


def test_enabling_requires_configuration(client: TestClient) -> None:
    before = client.app.state.notifier
    assert client.put("/api/system/notifications", json={"enabled": True}).status_code == 409
    assert client.app.state.notifier is before


def test_switch_uses_only_configured_recipients(client: TestClient, settings: Settings) -> None:
    settings.alert_recipient_email = "reviewer@example.com"
    settings.ses_sender_email = "alerts@example.com"
    fake = FakeNotifier()
    fake.channel = "ses"
    with patch("app.services.notification_service.get_notifier", return_value=fake) as factory:
        result = client.put("/api/system/notifications", json={"enabled": True})
    assert result.status_code == 200
    assert result.json()["notifier"] == "ses"
    assert factory.call_args.args[0].alert_recipients == ["reviewer@example.com"]
    assert factory.call_args.args[0].notifier == "ses"
    assert fake.sent == []
    travel_pair(client, "EMAIL-ON")
    assert len(fake.sent) == 1
    result = client.put("/api/system/notifications", json={"enabled": False})
    assert result.json()["notifier"] == "log"
    assert isinstance(client.app.state.notifier, LogNotifier)
    travel_pair(client, "EMAIL-OFF")
    assert len(fake.sent) == 1


def test_failed_switch_preserves_mode(client: TestClient, settings: Settings) -> None:
    settings.alert_recipient_email = "reviewer@example.com"
    settings.ses_sender_email = "alerts@example.com"
    before = client.app.state.notifier
    with patch("app.services.notification_service.get_notifier", side_effect=RuntimeError("profile unavailable")):
        result = client.put("/api/system/notifications", json={"enabled": True})
    assert result.status_code == 409
    assert client.app.state.notifier is before


def test_switch_rejects_recipient_override_and_non_boolean(client: TestClient) -> None:
    for body in ({"enabled": True, "recipient": "other@example.com"}, {"enabled": "true"}, {}):
        assert client.put("/api/system/notifications", json=body).status_code == 422
