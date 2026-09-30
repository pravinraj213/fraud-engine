import { useEffect, useState } from "react";
import { useOutletContext } from "react-router-dom";
import { api } from "../api/client.js";
import { ruleLabel } from "../utils/format.js";

function formatParam(value) {
  if (Array.isArray(value)) return value.join(", ");
  if (typeof value === "number") return value.toLocaleString("en-IN");
  return String(value);
}

export default function RulesPage() {
  const { system } = useOutletContext();
  const [rules, setRules] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.rules().then(setRules).catch((e) => setError(e.message));
  }, []);

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Rules</h1>
          <p className="muted">
            Every registered rule and its configuration from <code>backend/rules.yaml</code>. Scores of triggered
            rules are multiplied by their weight and summed (capped at 100).
          </p>
        </div>
      </header>

      {system && (
        <section className="levels">
          <div className="level-band band-low"><strong>LOW</strong><span>1 – {system.medium_threshold - 1}</span></div>
          <div className="level-band band-medium"><strong>MEDIUM</strong><span>{system.medium_threshold} – {system.high_risk_threshold - 1}</span></div>
          <div className="level-band band-high"><strong>HIGH</strong><span>{system.high_risk_threshold}+ · sends an alert</span></div>
        </section>
      )}

      {error && <div className="banner banner-error" role="alert">{error}</div>}
      {!rules && !error && <p className="empty">Loading rules…</p>}
      <div className="rule-grid">
        {rules?.map((r) => (
          <article key={r.name} className={`panel rule-card ${r.enabled ? "" : "disabled"}`}>
            <div className="panel-head">
              <h2>{ruleLabel(r.name)}</h2>
              <span className={`badge ${r.enabled ? "status-cleared" : "risk-none"}`}>{r.enabled ? "Enabled" : "Disabled"}</span>
            </div>
            <p>{r.description}</p>
            <dl className="facts compact">
              <div><dt>Weight</dt><dd>{r.weight}</dd></div>
              {Object.entries(r.params).map(([k, v]) => (
                <div key={k}><dt>{k.replace(/_/g, " ")}</dt><dd>{formatParam(v)}</dd></div>
              ))}
            </dl>
          </article>
        ))}
      </div>
      <p className="muted small">
        To add a rule, drop one file into <code>backend/app/engine/rules/</code>; see <code>docs/ADDING_A_RULE.md</code>.
      </p>
    </div>
  );
}
