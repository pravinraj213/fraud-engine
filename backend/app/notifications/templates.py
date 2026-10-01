"""Alert email rendering: pure functions of an AlertPayload."""
from html import escape
from urllib.parse import urlparse

from app.notifications.base import AlertPayload

FOOTER = "This alert was generated automatically by Fraud Rule Engine."
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


def render_test_subject() -> str:
    return "Suraksha email delivery test"


def render_test_text() -> str:
    return "\n".join([
        "Suraksha email delivery test",
        "",
        "Your Amazon SES email configuration is working.",
        "This message was requested from the notification settings in the Suraksha console.",
        "No transaction was created and automatic fraud alerts were not changed.",
        "",
        "You can now use the console to send high-risk transaction alerts.",
    ])


def render_test_html() -> str:
    return """<!doctype html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Suraksha email delivery test</title></head>
<body style="margin:0;padding:0;background:#f3f5fa;font-family:Arial,Helvetica,sans-serif;color:#19263c">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#f3f5fa">
<tr><td align="center" style="padding:40px 16px">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;background:#ffffff;border:1px solid #e0e6ef">
<tr><td bgcolor="#0f1b2d" style="padding:24px 36px;color:#ffffff">
<p style="margin:0;font-size:16px;font-weight:bold">Suraksha</p>
<p style="margin:4px 0 0;font-size:12px;color:#c9d4e3">FRAUD ENGINE</p></td></tr>
<tr><td style="padding:36px">
<p style="margin:0 0 12px;font-size:12px;font-weight:bold;letter-spacing:1px;color:#087f73">DELIVERY TEST SUCCESSFUL</p>
<h1 style="margin:0 0 16px;font-size:28px;line-height:1.2;color:#19263c">Your email configuration is working</h1>
<p style="margin:0 0 16px;font-size:14px;line-height:1.7;color:#526179">This message was requested from the notification settings in the Suraksha console.</p>
<p style="margin:0;font-size:14px;line-height:1.7;color:#526179">No transaction was created and automatic fraud alerts were not changed.</p>
</td></tr></table></td></tr></table></body></html>"""


def render_text(alert: AlertPayload) -> str:
    lines = [
        "Transaction requires review",
        "A transaction has been flagged for high risk. Review the evidence before taking action.",
        "",
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
        "Next step: inspect the rule evidence, then mark the transaction reviewed or clear it as legitimate.",
        "A risk alert is a signal for investigation, not a confirmation of fraud.",
        "",
        FOOTER,
    ]
    return "\n".join(lines)


def _link_block(alert: AlertPayload) -> str:
    url = escape(alert.console_url, quote=True)
    if is_local_url(alert.console_url):
        # A button to localhost looks clickable but fails on any other device, so show the address as text.
        return (f'<p style="background:#f3f5fa;border:1px solid #e0e6ef;border-radius:8px;padding:16px;'
                f'font-size:13px;line-height:1.6;color:#526179;overflow-wrap:anywhere;word-break:break-word">'
                f'Review this transaction on the computer running the console:<br>'
                f'<span style="font-family:monospace">{url}</span><br>{escape(LOCAL_NOTE)}</p>')
    return (f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:24px 0 16px">'
            f'<tr><td bgcolor="#2459d6" style="border-radius:8px;text-align:center;mso-padding-alt:14px 24px">'
            f'<a href="{url}" style="background:#2459d6;border:1px solid #2459d6;color:#ffffff;'
            f'padding:14px 24px;border-radius:8px;text-decoration:none;display:inline-block;'
            f'font-size:15px;font-weight:bold">Review transaction &rarr;</a></td></tr></table>'
            f'<p style="font-size:12px;line-height:1.6;color:#607087;overflow-wrap:anywhere;word-break:break-word">'
            f'Or copy this address into your browser:<br>{url}</p>')


def render_html(alert: AlertPayload) -> str:
    facts = [("Amount", _money(alert)), ("Merchant", alert.merchant),
             ("Location", alert.location_label or "Not provided"), ("Time", _when(alert)), ("Account", alert.account_id),
             ("Transaction ID", alert.transaction_id)]
    fact_rows = "".join(
        f'<tr><th scope="row" class="fact-label" style="width:120px;padding:12px 0;border-bottom:1px solid #e0e6ef;'
        f'text-align:left;vertical-align:top;color:#607087;font-size:13px;font-weight:normal">{escape(k)}</th>'
        f'<td class="fact-value" style="padding:12px 0 12px 16px;border-bottom:1px solid #e0e6ef;'
        f'font-size:14px;color:#19263c;overflow-wrap:anywhere;word-break:break-word">{escape(v)}</td></tr>'
        for k, v in facts)
    hit_rows = "".join(
        f'<tr><td style="padding:16px;background:#f8f9fc;border-bottom:4px solid #ffffff;'
        f'overflow-wrap:anywhere;word-break:break-word">'
        f'<p style="margin:0 0 6px;font-size:14px;font-weight:bold;color:#19263c">'
        f'{escape(name.replace("_", " ").title())} <span style="font-weight:normal;color:#607087">&middot; Rule score {score}/100</span></p>'
        f'<p style="margin:0;font-size:13px;line-height:1.7;color:#526179">{escape(reason)}</p></td></tr>'
        for name, score, reason in alert.hits)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="color-scheme" content="light"><meta name="supported-color-schemes" content="light">
<title>Transaction requires review</title>
<style>
body {{ margin:0; padding:0; -webkit-text-size-adjust:100%; }}
table {{ border-collapse:collapse; mso-table-lspace:0; mso-table-rspace:0; }}
@media only screen and (max-width:600px) {{
  .outer {{ padding:12px 8px !important; }}
  .content {{ padding:24px 20px !important; }}
  .email-title {{ font-size:25px !important; }}
  .fact-label {{ width:90px !important; }}
  .fact-value {{ padding-left:10px !important; }}
}}
</style></head>
<body style="margin:0;padding:0;background:#f3f5fa;font-family:Arial,Helvetica,sans-serif;color:#19263c;line-height:1.5">
<div style="display:none;font-size:1px;color:#f3f5fa;line-height:1px;max-height:0;max-width:0;opacity:0;overflow:hidden;mso-hide:all">Review requested: {escape(alert.account_id)} · {escape(_money(alert))} · Risk score {alert.total_score}/100.</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#f3f5fa">
<tr><td class="outer" align="center" style="padding:40px 16px">
<!--[if mso]><table role="presentation" width="640" align="center"><tr><td><![endif]-->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:640px;background:#ffffff;border:1px solid #e0e6ef">
<tr><td class="content" bgcolor="#0f1b2d" style="padding:24px 36px;color:#ffffff">
<p style="margin:0;font-size:16px;font-weight:bold;letter-spacing:.3px">Fraud Rule Engine</p>
<p style="margin:4px 0 0;font-size:12px;color:#c9d4e3">TRANSACTION MONITORING</p></td></tr>
<tr><td class="content" style="padding:32px 36px">
<p style="margin:0 0 14px;font-size:12px;font-weight:bold;letter-spacing:1px;color:#b3261e">{escape(alert.risk_level)} RISK &middot; REVIEW REQUESTED</p>
<h1 class="email-title" style="margin:0 0 12px;font-size:30px;line-height:1.2;letter-spacing:-.7px;color:#19263c">Transaction requires review</h1>
<p style="margin:0 0 24px;font-size:14px;line-height:1.7;color:#526179">Our monitoring rules flagged this transaction. Review the details and supporting evidence in the console.</p>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#fdecea" style="margin-bottom:24px;border-left:4px solid #b3261e">
<tr><td style="padding:18px 20px;color:#b3261e"><span style="font-size:12px;font-weight:bold">TOTAL RISK SCORE</span><br>
<strong style="font-size:36px;line-height:1.3">{alert.total_score}</strong><span style="font-size:16px"> / 100</span><br>
<span style="font-size:12px">Weighted rule scores, capped at 100</span></td></tr></table>
<h2 style="margin:0 0 4px;font-size:16px;color:#19263c">Transaction details</h2>
<table aria-label="Transaction details" width="100%" cellpadding="0" cellspacing="0" border="0" style="table-layout:fixed;margin-bottom:28px">{fact_rows}</table>
<h2 style="margin:0 0 12px;font-size:16px;color:#19263c">Why this was flagged</h2>
<table style="border-collapse:collapse;width:100%;margin-bottom:16px">{hit_rows}</table>
<h2 style="margin:24px 0 8px;font-size:16px;color:#19263c">Recommended next step</h2>
<p style="margin:0;font-size:14px;line-height:1.7;color:#526179">Inspect the rule evidence, then mark the transaction reviewed or clear it as legitimate. Record a note to support your decision.</p>
{_link_block(alert)}
<p style="margin:20px 0 0;font-size:12px;line-height:1.7;color:#607087">A risk alert is a signal for investigation, not a confirmation of fraud.</p>
</td></tr><tr><td class="content" bgcolor="#f8f9fc" style="padding:20px 36px;border-top:1px solid #e0e6ef">
<p style="margin:0;color:#607087;font-size:12px;line-height:1.7">{FOOTER}<br>Use the reviewer console to record your decision.</p>
</td></tr></table><!--[if mso]></td></tr></table><![endif]-->
</td></tr></table></body></html>"""
