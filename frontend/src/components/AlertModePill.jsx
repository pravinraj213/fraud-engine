/** Shows whether HIGH-risk alerts send real email (SES) or only go to the server log. */
export default function AlertModePill({ system }) {
  if (!system) return null;
  const email = system.notifier === "ses";
  const title = email
    ? `HIGH-risk transactions send real email. ${system.alerts_sent_24h} of ${system.alert_daily_limit} sent in the last 24 h.`
    : "HIGH-risk alerts are written to the server log only. Start with ./start.sh --email to send real email.";
  return (
    <span className={`mode-pill ${email ? "mode-email" : "mode-log"}`} title={title}>
      <span className="dot" aria-hidden="true" />
      {email ? `Email alerts on · ${system.alerts_sent_24h}/${system.alert_daily_limit} today` : "Email alerts off"}
    </span>
  );
}
