import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client.js";
import { CITIES, MERCHANTS } from "../simulator/scenarios.js";
import { money, ruleLabel } from "../utils/format.js";
import RiskBadge from "./RiskBadge.jsx";
import StatusBadge from "./StatusBadge.jsx";

const EMPTY = { account_id: "ACC-9001", amount: "2500.00", merchant: MERCHANTS[0], city: "Chennai, IN", minutes_ago: "0" };

/** Send one hand-made transaction and show the engine's verdict. */
export default function ManualTransactionForm({ system, onCreated }) {
  const [form, setForm] = useState(EMPTY);
  const [acknowledged, setAcknowledged] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [results, setResults] = useState([]);

  const emailOn = system?.notifier === "ses";
  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const [latitude, longitude] = CITIES[form.city];
    try {
      const detail = await api.createTransaction({
        account_id: form.account_id.trim(),
        amount: Number(form.amount).toFixed(2),
        currency: "INR",
        merchant: form.merchant.trim(),
        latitude,
        longitude,
        location_label: form.city,
        occurred_at: new Date(Date.now() - Number(form.minutes_ago || 0) * 60_000).toISOString(),
      });
      setResults([detail, ...results].slice(0, 5));
      setAcknowledged(false);
      onCreated?.();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel">
      <div className="panel-head">
        <h2>Send one transaction</h2>
      </div>
      <p className="muted small">
        Try your own cases, e.g. the same account in Chennai and then London a few minutes apart.
      </p>
      <form className="manual-form" onSubmit={submit}>
        <label>Account<input required maxLength={64} value={form.account_id} onChange={set("account_id")} /></label>
        <label>Amount (INR)<input required type="number" min="0.01" step="0.01" value={form.amount} onChange={set("amount")} /></label>
        <label>
          Merchant
          <input required maxLength={128} list="merchants" value={form.merchant} onChange={set("merchant")} />
          <datalist id="merchants">{MERCHANTS.map((m) => <option key={m} value={m} />)}</datalist>
        </label>
        <label>
          City
          <select value={form.city} onChange={set("city")}>
            {Object.keys(CITIES).map((c) => <option key={c}>{c}</option>)}
          </select>
        </label>
        <label>Minutes ago<input type="number" min="0" step="1" value={form.minutes_ago} onChange={set("minutes_ago")} /></label>
        <div className="manual-submit">
          {emailOn && (
            <label className="check">
              <input type="checkbox" checked={acknowledged} onChange={(e) => setAcknowledged(e.target.checked)} />
              OK to send 1 real email if HIGH
            </label>
          )}
          <button className="btn-primary" disabled={busy || (emailOn && !acknowledged)}>
            {busy ? "Sending…" : "Send transaction"}
          </button>
        </div>
      </form>
      {error && <div className="banner banner-error" role="alert">{error}</div>}
      {results.length > 0 && (
        <ul className="manual-results">
          {results.map((d) => (
            <li key={d.transaction.id}>
              <RiskBadge level={d.assessment.risk_level} score={d.assessment.total_score} />
              <StatusBadge status={d.assessment.status} />
              <span className="mono">{d.transaction.account_id}</span>
              <span>{money(d.transaction.amount)} · {d.transaction.location_label}</span>
              <span className="muted grow">
                {d.rule_hits.length ? d.rule_hits.map((h) => `${ruleLabel(h.rule_name)}: ${h.reason}`).join(" · ") : "No rules triggered"}
              </span>
              {d.assessment.status !== "CLEAN" && <Link to={`/transactions/${d.transaction.id}`}>Open</Link>}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
