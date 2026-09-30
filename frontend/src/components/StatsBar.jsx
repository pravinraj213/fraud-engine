import Icon from "./Icon.jsx";
export default function StatsBar({ stats }) {
  const s = stats?.by_status ?? {};
  const total = Object.values(s).reduce((sum, n) => sum + n, 0);
  const cards = [
    {
      label: "Transactions screened",
      value: total,
      icon: "activity",
      sub: "Across all accounts",
      tone: "teal",
    },
    {
      label: "Awaiting review",
      value: s.FLAGGED ?? 0,
      icon: "flag",
      sub: `${stats?.flagged_by_level?.HIGH ?? 0} high-priority flags`,
      tone: "orange",
    },
    {
      label: "Reviewed",
      value: s.REVIEWED ?? 0,
      icon: "check",
      sub: "Confirmed as suspicious",
      tone: "blue",
    },
    {
      label: "Cleared",
      value: s.CLEARED ?? 0,
      icon: "shield",
      sub: "Resolved as false positives",
      tone: "green",
    },
  ];
  return (
    <section className="stats" aria-label="All-time summary">
      {cards.map((c) => (
        <div className={`stat stat-${c.tone}`} key={c.label}>
          <div className="stat-top">
            <span className="stat-label">{c.label}</span>
            <span className="stat-icon">
              <Icon name={c.icon} size={18} />
            </span>
          </div>
          <span className="stat-value">
            {stats ? c.value.toLocaleString("en-IN") : "—"}
          </span>
          <span className="stat-description">
            <i />
            {stats ? c.sub : "Waiting for engine"}
          </span>
        </div>
      ))}
    </section>
  );
}
