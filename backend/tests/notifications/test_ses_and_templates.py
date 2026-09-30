from dataclasses import replace
from decimal import Decimal

import boto3
import pytest
from botocore.stub import ANY, Stubber

from app.config import Settings
from app.notifications.base import AlertPayload
from app.notifications.factory import get_notifier
from app.notifications.log import LogNotifier
from app.notifications.ses import SESNotifier
from app.notifications.templates import render_html, render_subject, render_text
from tests.fakes import NOW

ALERT = AlertPayload(
    assessment_id="a-1", transaction_id="t-1", account_id="ACC-1001", amount=Decimal("4999.00"),
    currency="INR", merchant="Croma Electronics", location_label="London, GB", occurred_at=NOW,
    total_score=90, risk_level="HIGH",
    hits=[("impossible_travel", 90, "Chennai, IN → London, GB: 8,210 km in 45 min")],
    console_url="http://192.168.1.20:5173/transactions/t-1",
)


def stubbed_ses() -> tuple[SESNotifier, Stubber]:
    client = boto3.client("sesv2", region_name="ap-south-1", aws_access_key_id="x", aws_secret_access_key="x")
    return SESNotifier("alerts@example.com", ["reviewer@example.com"], "ap-south-1", client=client), Stubber(client)


def test_ses_sends_expected_request() -> None:
    notifier, stub = stubbed_ses()
    stub.add_response("send_email", {"MessageId": "msg-123"}, {
        "FromEmailAddress": "alerts@example.com",
        "Destination": {"ToAddresses": ["reviewer@example.com"]},
        "Content": {"Simple": {
            "Subject": {"Data": render_subject(ALERT), "Charset": "UTF-8"},
            "Body": {"Text": {"Data": render_text(ALERT), "Charset": "UTF-8"},
                     "Html": {"Data": render_html(ALERT), "Charset": "UTF-8"}},
        }},
    })
    with stub:
        result = notifier.send_high_risk_alert(ALERT)
    assert result.success and result.provider_message_id == "msg-123"


def test_ses_client_error_becomes_failed_result() -> None:
    notifier, stub = stubbed_ses()
    stub.add_client_error("send_email", "MessageRejected", "Email address is not verified.",
                          expected_params={"FromEmailAddress": ANY, "Destination": ANY, "Content": ANY})
    with stub:
        result = notifier.send_high_risk_alert(ALERT)
    assert not result.success and "not verified" in result.error


def test_subject_format() -> None:
    assert render_subject(ALERT) == "[HIGH RISK 90] ACC-1001 · INR 4,999.00 at Croma Electronics"


def test_bodies_contain_facts_and_link() -> None:
    text, html = render_text(ALERT), render_html(ALERT)
    for part in ("Risk score: 90 (HIGH)", "INR 4,999.00", "impossible_travel (90)", "Transaction ID: t-1",
                 "Open in reviewer console: http://192.168.1.20:5173/transactions/t-1", "generated automatically"):
        assert part in text
    assert 'href="http://192.168.1.20:5173/transactions/t-1"' in html
    assert "only works on the computer" not in text


def test_localhost_link_is_text_not_a_button() -> None:
    local = replace(ALERT, console_url="http://localhost:5173/transactions/t-1")
    html, text = render_html(local), render_text(local)
    assert "href=" not in html and "http://localhost:5173/transactions/t-1" in html
    assert "only works on the computer running the console" in text


def test_html_escapes_user_values() -> None:
    html = render_html(replace(ALERT, merchant="<script>alert(1)</script>"))
    assert "<script>" not in html and "&lt;script&gt;" in html


def test_log_notifier_always_succeeds(caplog: pytest.LogCaptureFixture) -> None:
    assert LogNotifier().send_high_risk_alert(ALERT).success
    assert "[HIGH RISK 90]" in caplog.text


def test_factory() -> None:
    assert isinstance(get_notifier(Settings(_env_file=None, notifier="log")), LogNotifier)
    with pytest.raises(ValueError, match="Unknown NOTIFIER"):
        get_notifier(Settings(_env_file=None, notifier="pigeon"))
    with pytest.raises(ValueError, match="SES_SENDER_EMAIL"):
        get_notifier(Settings(_env_file=None, notifier="ses", ses_sender_email=""))
    ses = get_notifier(Settings(_env_file=None, notifier="ses", ses_sender_email="a@x.com",
                                alert_recipient_email="b@x.com, c@x.com"))
    assert isinstance(ses, SESNotifier) and ses.recipients == ["b@x.com", "c@x.com"]
