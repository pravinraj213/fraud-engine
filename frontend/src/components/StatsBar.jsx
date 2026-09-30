export default function StatsBar({ stats }) {
  const s = stats?.by_status ?? {};
  const lvl = stats?.flagged_by_level ?? {};
  const alerts = stats?.notifications ?? {};
  const v = (n) => (stats ? n ?? 0 : "–");

  return (
    <section className="stats" aria-label="Summary">
      <div className="stat stat-primary">
        <span className="stat-value">{v(s.FLAGGED)}</span>
        <span className="stat-label">Open flags</span>
        <div className="stat-split">
          <span className="lvl lvl-high">{v(lvl.HIGH)} high</span>
          <span className="lvl lvl-medium">{v(lvl.MEDIUM)} medium</span>
          <span className="lvl lvl-low">{v(lvl.LOW)} low</span>
        </div>
      </div>
      <div className="stat">
        <span className="stat-value tone-reviewed">{v(s.REVIEWED)}</span>
        <span className="stat-label">Reviewed</span>
      </div>
      <div className="stat">
        <span className="stat-value tone-cleared">{v(s.CLEARED)}</span>
        <span className="stat-label">Cleared</span>
      </div>
      <div className="stat">
        <span className="stat-value">{v(s.CLEAN)}</span>
        <span className="stat-label">Clean transactions</span>
      </div>
      <div className="stat">
        <span className="stat-value">
          {v(alerts.SENT)}
          {alerts.FAILED > 0 && <small className="tone-failed"> / {alerts.FAILED} failed</small>}
        </span>
        <span className="stat-label">Alerts (email or log)</span>
      </div>
    </section>
  );
}
