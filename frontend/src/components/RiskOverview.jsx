import { Link } from "react-router-dom";
import Icon from "./Icon.jsx";
export default function RiskOverview({ stats, system, onFilter }) {
  const levels = stats?.flagged_by_level ?? {};
  const total = Object.values(levels).reduce((sum, n) => sum + n, 0);
  const high = total ? ((levels.HIGH || 0) / total) * 100 : 0;
  const medium = total ? ((levels.MEDIUM || 0) / total) * 100 : 0;
  return (
    <div className="overview-grid">
      <section className="panel risk-overview">
        <div className="panel-head">
          <h2>Risk at a glance</h2>
          <span className="eyebrow">OPEN FLAGS</span>
        </div>
        <div className="risk-content">
          <div
            className="risk-donut"
            role="img"
            aria-label={
              stats
                ? `${levels.HIGH || 0} high, ${levels.MEDIUM || 0} medium, ${levels.LOW || 0} low risk open flags`
                : "Loading risk distribution"
            }
            style={{
              background: total
                ? `conic-gradient(#e77e69 0% ${high}%, #e8ba67 ${high}% ${high + medium}%, #78aaa1 ${high + medium}% 100%)`
                : "var(--border)",
            }}
          >
            <div>
              <strong>{stats ? total : "—"}</strong>
              <span>open flags</span>
            </div>
          </div>
          <div className="risk-legend">
            {[
              ["HIGH", "High risk", "Prioritize these flags"],
              ["MEDIUM", "Medium risk", "Needs a closer look"],
              ["LOW", "Low risk", "Review when available"],
            ].map(([level, label, description]) => (
              <button
                key={level}
                onClick={() => onFilter(level)}
                className="risk-legend-row"
              >
                <i className={`legend-dot ${level.toLowerCase()}`} />
                <span>
                  <strong>{label}</strong>
                  <small>{description}</small>
                </span>
                <b>{stats ? levels[level] || 0 : "—"}</b>
                <Icon name="chevron" size={14} />
              </button>
            ))}
          </div>
        </div>
      </section>
      <section className="intelligence-card">
        <div className="intelligence-copy">
          <span className="eyebrow">
            <i /> EXPLAINABLE BY DESIGN
          </span>
          <h2>
            Every signal.
            <br />A clearer decision.
          </h2>
          <p>
            Trace each flag to the rule behind it.
            <br />
            Review with context, act with confidence.
          </p>
          <Link to="/rules">
            View detection rules <Icon name="arrow" size={16} />
          </Link>
        </div>
        <div className="radar-art" aria-hidden="true">
          <div className="radar-ring ring-one" />
          <div className="radar-ring ring-two" />
          <div className="radar-ring ring-three" />
          <div className="radar-cross" />
          <span className="radar-center">
            <Icon name="shield" size={37} />
          </span>
          <i className="radar-point point-one" />
          <i className="radar-point point-two" />
          <span className="signal-label">
            <Icon name="check" size={12} /> Rule-based intelligence
          </span>
        </div>
        <div className="intelligence-foot">
          <Icon name="activity" size={14} />
          {system
            ? `High-risk alert threshold: ${system.high_risk_threshold} / 100`
            : "Connecting to your detection engine"}
        </div>
      </section>
    </div>
  );
}
