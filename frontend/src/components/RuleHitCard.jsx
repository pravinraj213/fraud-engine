import { money, number, ruleLabel } from "../utils/format.js";

/** The key numbers for each known rule; unknown rules show their raw details. */
function detailRows(name, d) {
  switch (name) {
    case "impossible_travel":
      return [
        ["Previous location", d.previous_location],
        ["Distance", `${number(d.distance_km)} km`],
        ["Time between", `${number(d.minutes_between)} min`],
        ["Speed", d.simultaneous ? "same moment" : `${number(d.speed_kmh)} km/h`],
      ];
    case "unusual_amount":
      if (d.median === undefined) {
        return [["History", `${d.history_size} prior transactions`], ["Limit", money(d.absolute_threshold)]];
      }
      return [
        ["Median", money(d.median)],
        ["Ratio to median", `${number(d.ratio, 1)}×`],
        ["Z-score", d.z_score === null ? "n/a (identical history)" : number(d.z_score, 1)],
        ["History", `${d.history_size} transactions`],
      ];
    case "velocity":
      return [
        ["Count", `${d.count} transactions`],
        ["Window", `${d.window_minutes} min (limit ${d.max_transactions})`],
      ];
    default:
      return Object.entries(d).map(([k, v]) => [k.replace(/_/g, " "), String(v)]);
  }
}

export default function RuleHitCard({ hit }) {
  return (
    <article className="hit-card">
      <header>
        <h3>{ruleLabel(hit.rule_name)}</h3>
        <span className="hit-math" title="score × weight = weighted score">
          {hit.score} × {hit.weight} = <strong>{number(hit.weighted_score, 1)}</strong>
        </span>
      </header>
      <p>{hit.reason}</p>
      <dl className="facts compact">
        {detailRows(hit.rule_name, hit.details).map(([k, v]) => (
          <div key={k}>
            <dt>{k}</dt>
            <dd>{v}</dd>
          </div>
        ))}
      </dl>
    </article>
  );
}
