import { dateTime, money, ruleLabel, timeAgo } from "../utils/format.js";
import RiskBadge from "./RiskBadge.jsx";
import StatusBadge from "./StatusBadge.jsx";

function alertLabel(status, channel) {
  if (status === "FAILED") return "failed";
  return channel === "ses" ? "emailed" : "logged";
}

export default function FlagsTable({ items, onOpen }) {
  return (
    <div className="table-wrap">
      <table className="flags">
        <thead>
          <tr>
            <th>Risk</th>
            <th>Time</th>
            <th>Account</th>
            <th className="num">Amount</th>
            <th>Merchant</th>
            <th>Location</th>
            <th>Rules</th>
            <th>Status</th>
            <th>Alert</th>
          </tr>
        </thead>
        <tbody>
          {items.map((t) => (
            <tr
              key={t.transaction_id}
              className={t.risk_level === "HIGH" ? "row-high" : ""}
              tabIndex={0}
              onClick={() => onOpen(t.transaction_id)}
              onKeyDown={(e) => e.key === "Enter" && onOpen(t.transaction_id)}
            >
              <td><RiskBadge level={t.risk_level} score={t.total_score} /></td>
              <td title={dateTime(t.occurred_at)}>{timeAgo(t.occurred_at)}</td>
              <td className="mono">{t.account_id}</td>
              <td className="num">{money(t.amount, t.currency)}</td>
              <td>{t.merchant}</td>
              <td>{t.location_label || "–"}</td>
              <td>
                {t.rules_triggered.map((r) => <span key={r} className="chip">{ruleLabel(r)}</span>)}
              </td>
              <td><StatusBadge status={t.status} /></td>
              <td>
                {t.notification_status
                  ? <span className={`alert-${t.notification_status.toLowerCase()}`}>{alertLabel(t.notification_status, t.notification_channel)}</span>
                  : <span className="muted">none</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
