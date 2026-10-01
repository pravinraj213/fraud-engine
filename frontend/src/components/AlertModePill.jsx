import { useState } from "react";
import { api } from "../api/client.js";

/** Configure alert delivery for the current server session. */
export default function AlertModePill({ system, onChange }) {
  const [busy, setBusy] = useState(false);
  const [testing, setTesting] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [testRecipient, setTestRecipient] = useState("");
  const [consentConfirmed, setConsentConfirmed] = useState(false);
  if (!system) return <span className="mode-pill mode-log">Alert settings unavailable</span>;
  const email = system.notifier === "ses";
  async function toggle() {
    setBusy(true);
    setError(null);
    setSuccess(null);
    try { onChange(await api.setEmailAlerts(!email)); }
    catch (e) { setError(e.message); }
    finally { setBusy(false); }
  }
  async function sendTest(event) {
    event.preventDefault();
    setTesting(true);
    setError(null);
    setSuccess(null);
    try {
      const result = await api.sendTestEmail(testRecipient.trim());
      setSuccess(`Test email sent to ${result.recipients.join(", ")}.`);
      setConsentConfirmed(false);
    } catch (e) {
      setError(e.message);
    } finally {
      setTesting(false);
    }
  }
  return (
    <details className="notification-settings">
      <summary className={`mode-pill ${email ? "mode-email" : "mode-log"}`}>
        <span className="dot" aria-hidden="true" />
        {email ? "Email alerts on" : "Email alerts off"}<span aria-hidden="true">⌄</span>
      </summary>
      <div className="notification-popover">
        <div className="notification-heading">
          <strong>Email notifications</strong>
          <span className={`notification-state ${email ? "is-on" : "is-off"}`}>
            Automatic alerts {email ? "on" : "off"}
          </span>
        </div>
        <p>Automatically email the configured recipient when a new transaction is assessed as HIGH risk.</p>
        <span className="eyebrow">RECIPIENT</span>
        <div className="notification-recipient">{system.alert_recipients?.join(", ") || "No recipient configured"}</div>
        <button className={email ? "" : "btn-primary"} onClick={toggle} disabled={busy || (!email && !system.email_configured)}>
          {busy ? "Updating…" : email ? "Turn off automatic alerts" : "Turn on automatic alerts"}
        </button>
        {!system.email_configured && <p className="hint">Configure a sender and recipient on the server to enable email.</p>}
        <div className="notification-test">
          <div className="notification-test-heading">
            <span className="eyebrow">ONE-TIME TEST</span>
            <strong>Send a demo email</strong>
          </div>
          <p>Use an address supplied by a jury member. This will not change the automatic-alert recipient.</p>
          <form className="notification-test-form" onSubmit={sendTest}>
            <div className="notification-field">
              <label className="notification-test-label" htmlFor="test-email-recipient">Recipient email</label>
              <input
                id="test-email-recipient"
                type="email"
                required
                maxLength={254}
                value={testRecipient}
                onChange={(event) => {
                  setTestRecipient(event.target.value);
                  setConsentConfirmed(false);
                  setSuccess(null);
                }}
                placeholder="jury@example.com"
                autoComplete="email"
              />
              <span className="notification-field-hint">Used for this message only and not saved.</span>
            </div>
            <label className="notification-consent">
              <input
                type="checkbox"
                checked={consentConfirmed}
                onChange={(event) => setConsentConfirmed(event.target.checked)}
              />
              <span>
                <strong>Permission confirmed</strong>
                <small>The recipient asked to receive this test email.</small>
              </span>
            </label>
            <button className="btn-primary notification-test-button" type="submit" disabled={testing || busy || !system.email_configured || !consentConfirmed}>
              {testing ? "Sending test…" : "Send test email"}
            </button>
          </form>
        </div>
        <p className="small">The automatic-alert setting applies to this server session. Restarting restores the startup setting. Alerts already queued may still be delivered.</p>
        {success && <p className="banner banner-ok" role="status">{success}</p>}
        {error && <p className="banner banner-error" role="alert">{error}</p>}
      </div>
    </details>
  );
}
