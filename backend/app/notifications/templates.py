"""Alert email rendering: pure functions of an AlertPayload."""
from html import escape
from urllib.parse import urlparse

from app.notifications.base import AlertPayload

FOOTER = "This alert was generated automatically by fraud-rule-engine."
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}
LOCAL_NOTE = ("The reviewer console link only works on the computer running the console "
              "(set CONSOLE_BASE_URL to a reachable address to open it from other devices).")


def is_local_url(url: str) -> bool:
    """True when the link can only be opened on the machine running the console."""
    host = (urlparse(url).hostname or "").lower()
    return host in LOCAL_HOSTS or host.endswith(".localhost")


def _money(alert: AlertPayload) -> str:
    return f"{alert.currency} {alert.amount:,.2f}"


def _when(alert: AlertPayload) -> str:
    return alert.occurred_at.strftime("%d %b %Y, %H:%M UTC")


def render_subject(alert: AlertPayload) -> str:
    return f"[{alert.risk_level} RISK {alert.total_score}] {alert.account_id} · {_money(alert)} at {alert.merchant}"


def render_text(alert: AlertPayload) -> str:
    lines = [
        f"Risk score: {alert.total_score} ({alert.risk_level})",
        "",
        f"Amount:   {_money(alert)}",
        f"Merchant: {alert.merchant}",
        f"Location: {alert.location_label or '-'}",
        f"Time:     {_when(alert)}",
        f"Account:  {alert.account_id}",
        f"Transaction ID: {alert.transaction_id}",
        "",
        "Rules triggered:",
        *[f"  - {name} ({score}): {reason}" for name, score, reason in alert.hits],
        "",
        f"Open in reviewer console: {alert.console_url}",
        *([LOCAL_NOTE] if is_local_url(alert.console_url) else []),
        "",
        FOOTER,
    ]
    return "\n".join(lines)


def _link_block(alert: AlertPayload) -> str:
    url = escape(alert.console_url, quote=True)
    if is_local_url(alert.console_url):
        # A button to localhost looks clickable but fails on any other device, so show the address as text.
        return (f'<p style="background:#f4f6f8;border:1px solid #dfe3e8;border-radius:6px;padding:10px 12px;'
                f'font-size:13px;color:#4a5561">Review it in the console on the computer running it:<br>'
                f'<code style="font-size:13px">{url}</code><br>{escape(LOCAL_NOTE)}</p>')
    return (f'<p><a href="{url}" style="background:#2459d6;color:#fff;padding:10px 16px;border-radius:6px;'
            f'text-decoration:none;display:inline-block;font-weight:bold">Open in reviewer console</a></p>')


def render_html(alert: AlertPayload) -> str:
    cell = 'style="padding:6px 12px;border-bottom:1px solid #e5e5e5;text-align:left;vertical-align:top"'
    facts = [("Amount", _money(alert)), ("Merchant", alert.merchant),
             ("Location", alert.location_label or "-"), ("Time", _when(alert)), ("Account", alert.account_id),
             ("Transaction ID", alert.transaction_id)]
    fact_rows = "".join(f"<tr><th {cell}>{escape(k)}</th><td {cell}>{escape(v)}</td></tr>" for k, v in facts)
    hit_rows = "".join(
        f"<tr><td {cell}><strong>{escape(name)}</strong></td><td {cell}>{score}</td><td {cell}>{escape(reason)}</td></tr>"
        for name, score, reason in alert.hits)
    return f"""<div style="font-family:Arial,sans-serif;color:#1d232b;max-width:640px">
<h2 style="color:#c62828;margin:0 0 8px">Risk score {alert.total_score} ({escape(alert.risk_level)})</h2>
<table style="border-collapse:collapse;width:100%;margin-bottom:16px">{fact_rows}</table>
<h3 style="margin:0 0 8px">Rules triggered</h3>
<table style="border-collapse:collapse;width:100%;margin-bottom:16px">{hit_rows}</table>
{_link_block(alert)}
<p style="color:#66707c;font-size:12px">{FOOTER}</p>
</div>"""
