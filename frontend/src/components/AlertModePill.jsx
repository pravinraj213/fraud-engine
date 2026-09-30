import { useState } from "react";
import { api } from "../api/client.js";

/** Configure alert delivery for the current server session. */
export default function AlertModePill({ system, onChange }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  if (!system) return <span className="mode-pill mode-log">Alert settings unavailable</span>;
  const email = system.notifier === "ses";
  async function toggle() {
    setBusy(true);
    setError(null);
    try { onChange(await api.setEmailAlerts(!email)); }
    catch (e) { setError(e.message); }
    finally { setBusy(false); }
  }
  return (
    <details className="notification-settings">
      <summary className={`mode-pill ${email ? "mode-email" : "mode-log"}`}>
        <span className="dot" aria-hidden="true" />
        {email ? "Email alerts on" : "Email alerts off"}<span aria-hidden="true">⌄</span>
      </summary>
      <div className="notification-popover">
        <strong>Email notifications</strong>
        <p>Send an email when a new transaction is assessed as HIGH risk.</p>
        <span className="eyebrow">RECIPIENT</span>
        <div className="notification-recipient">{system.alert_recipients?.join(", ") || "No recipient configured"}</div>
        <p>{system.alerts_sent_24h} / {system.alert_daily_limit} alerts sent in the last 24 hours.</p>
        <button className={email ? "" : "btn-primary"} onClick={toggle} disabled={busy || (!email && !system.email_configured)}>
          {busy ? "Updating…" : email ? "Turn off email alerts" : "Turn on email alerts"}
        </button>
        {!system.email_configured && <p className="hint">Configure a sender and recipient on the server to enable email.</p>}
        <p className="small">Applies to new transactions for this server session. Restarting restores the startup setting. Alerts already queued may still be delivered.</p>
        {error && <p className="banner banner-error" role="alert">{error}</p>}
      </div>
    </details>
  );
}
