import { useState } from "react";

const MAX_NOTE = 1000;
const ACTIONS = {
  REVIEWED: { label: "Mark reviewed", hint: "Confirmed or escalated as suspicious", className: "btn-warn" },
  CLEARED: { label: "Clear", hint: "Legitimate, false positive", className: "btn-ok" },
};

export default function ReviewPanel({ allowedActions, reviewer, onSubmit }) {
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState(null);

  if (allowedActions.length === 0) {
    // Final state (CLEARED): no more actions, but keep the confirmation of what just happened.
    return message ? <p className={`banner banner-${message.tone}`} role="status">{message.text}</p> : null;
  }

  async function act(action) {
    if (action === "CLEARED" && !window.confirm("Clear this transaction as legitimate? This is final.")) return;
    setBusy(true);
    setMessage(null);
    try {
      await onSubmit(action, note.trim());
      setNote("");
      setMessage({ tone: "ok", text: action === "CLEARED" ? "Transaction cleared." : "Marked as reviewed." });
    } catch (e) {
      setMessage({ tone: "error", text: e.message });
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel">
      <h2>Decision</h2>
      <label className="note">
        <span>Note (optional)</span>
        <textarea
          value={note}
          maxLength={MAX_NOTE}
          rows={3}
          placeholder="e.g. Called customer, confirmed card stolen"
          onChange={(e) => setNote(e.target.value)}
        />
        <small className="muted">{note.length}/{MAX_NOTE}</small>
      </label>
      <div className="actions">
        {allowedActions.map((action) => (
          <button
            key={action}
            className={ACTIONS[action]?.className}
            disabled={busy || !reviewer}
            onClick={() => act(action)}
          >
            {ACTIONS[action]?.label ?? action}
            <small>{ACTIONS[action]?.hint}</small>
          </button>
        ))}
      </div>
      {!reviewer && <p className="hint">Enter your name in the header to review.</p>}
      {message && (
        <p className={`banner banner-${message.tone}`} role={message.tone === "error" ? "alert" : "status"}>
          {message.text}
        </p>
      )}
    </section>
  );
}
