import { useState } from "react";
import { Link, useOutletContext } from "react-router-dom";
import ManualTransactionForm from "../components/ManualTransactionForm.jsx";
import RiskBadge from "../components/RiskBadge.jsx";
import { runScenarios, SCENARIOS } from "../simulator/scenarios.js";
import { ruleLabel } from "../utils/format.js";

function EmailGuard({ system, emails, acknowledged, onAcknowledge }) {
  if (!system) return null;
  if (system.notifier !== "ses") {
    return (
      <div className="callout callout-info">
        <strong>Email alerts are off.</strong> HIGH-risk results are written to the server log only, so
        you can run the simulator as often as you like.
      </div>
    );
  }
  const remaining = Math.max(0, system.alert_daily_limit - system.alerts_sent_24h);
  return (
    <div className="callout callout-warn">
      <div>
        <strong>Email alerts are on.</strong> Every HIGH-risk transaction sends a real email through Amazon
        SES. {system.alerts_sent_24h} of {system.alert_daily_limit} daily alerts used; {remaining} left.
      </div>
      <label className="check">
        <input type="checkbox" checked={acknowledged} onChange={(e) => onAcknowledge(e.target.checked)} />
        I understand this can send up to {emails} real email{emails === 1 ? "" : "s"}.
      </label>
    </div>
  );
}

function ResultsTable({ result }) {
  const passed = result.checks.filter((c) => c.expected === c.actual).length;
  const all = passed === result.checks.length;
  return (
    <section className="panel">
      <div className="panel-head">
        <h2>Results</h2>
        <span className={`result-summary ${all ? "ok" : "bad"}`}>
          {all ? "✓" : "✗"} {passed}/{result.checks.length} checks passed
        </span>
      </div>
      <p className="muted small">Accounts in this run end in <code>-{result.tag}</code>.</p>
      <div className="table-wrap">
        <table className="grid">
          <thead>
            <tr>
              <th>Scenario</th><th>Account</th><th>Expected</th><th>Actual</th><th>Rules</th><th>Result</th><th />
            </tr>
          </thead>
          <tbody>
            {result.checks.map((c) => {
              const ok = c.expected === c.actual;
              return (
                <tr key={c.transactionId} className={ok ? "" : "row-fail"}>
                  <td><strong>{c.scenario}</strong><div className="muted small">{c.description}</div></td>
                  <td className="mono">{c.account}</td>
                  <td>{c.expected}</td>
                  <td><RiskBadge level={c.actual} score={c.score} /></td>
                  <td>{c.rules.length ? c.rules.map((r) => <span key={r} className="chip">{ruleLabel(r)}</span>) : <span className="muted">–</span>}</td>
                  <td className={ok ? "pass" : "fail"}>{ok ? "Pass" : "Fail"}</td>
                  <td>{c.actual !== "NONE" && <Link to={`/transactions/${c.transactionId}`}>Open</Link>}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export default function SimulatorPage() {
  const { system, refreshStats } = useOutletContext();
  const [selected, setSelected] = useState(() => new Set(SCENARIOS.map((s) => s.id)));
  const [acknowledged, setAcknowledged] = useState(false);
  const [progress, setProgress] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const chosen = SCENARIOS.filter((s) => selected.has(s.id));
  const totalRequests = chosen.reduce((n, s) => n + s.requests, 0);
  const emails = chosen.reduce((n, s) => n + s.highAlerts, 0);
  const emailOn = system?.notifier === "ses";
  const blocked = emailOn && emails > 0 && !acknowledged;
  const running = progress !== null;

  const toggle = (id) => {
    const next = new Set(selected);
    next.has(id) ? next.delete(id) : next.add(id);
    setSelected(next);
  };

  async function run() {
    setError(null);
    setResult(null);
    setProgress(0);
    try {
      const order = SCENARIOS.map((s) => s.id).filter((id) => selected.has(id));
      setResult(await runScenarios(order, { onProgress: setProgress }));
    } catch (e) {
      setError(e.message);
    } finally {
      setProgress(null);
      setAcknowledged(false);
      refreshStats();
    }
  }

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Transaction simulator</h1>
          <p className="muted">
            Send realistic normal and fraudulent traffic to the API and check each verdict against the expected
            result. Everything it creates appears in the review queue.
          </p>
        </div>
      </header>

      <EmailGuard system={system} emails={emails} acknowledged={acknowledged} onAcknowledge={setAcknowledged} />

      <section className="panel">
        <div className="panel-head">
          <h2>Scenarios</h2>
          <div className="row-gap">
            <button className="btn-link" onClick={() => setSelected(new Set(SCENARIOS.map((s) => s.id)))}>Select all</button>
            <button className="btn-link" onClick={() => setSelected(new Set())}>Clear</button>
          </div>
        </div>
        <div className="scenario-grid">
          {SCENARIOS.map((s) => (
            <label key={s.id} className={`scenario ${selected.has(s.id) ? "selected" : ""}`}>
              <input type="checkbox" checked={selected.has(s.id)} onChange={() => toggle(s.id)} disabled={running} />
              <span className="scenario-title">{s.title}</span>
              <span className="scenario-desc">{s.description}</span>
              <span className="scenario-meta">
                <span>Expect <strong>{s.expect}</strong></span>
                <span>{s.requests} requests</span>
                {s.highAlerts > 0 && <span className="tone-high">{s.highAlerts} HIGH alert</span>}
              </span>
            </label>
          ))}
        </div>
        <div className="run-bar">
          <button className="btn-primary" disabled={running || chosen.length === 0 || blocked} onClick={run}>
            {running ? "Running…" : `Run ${chosen.length} scenario${chosen.length === 1 ? "" : "s"}`}
          </button>
          <span className="muted small">
            {totalRequests} transactions{emails > 0 && `, ${emails} expected HIGH`}
            {blocked && " · tick the email confirmation above to run"}
          </span>
        </div>
        {running && (
          <div className="progress" role="progressbar" aria-valuenow={progress} aria-valuemax={totalRequests}>
            <div style={{ width: `${Math.min(100, (progress / totalRequests) * 100)}%` }} />
            <span>{progress} / {totalRequests}</span>
          </div>
        )}
        {error && <div className="banner banner-error" role="alert">{error}</div>}
      </section>

      {result && <ResultsTable result={result} />}

      <ManualTransactionForm system={system} onCreated={refreshStats} />
    </div>
  );
}
