import { dateTime, money, ruleLabel, timeAgo } from "../utils/format.js";
import RiskBadge from "./RiskBadge.jsx";
import StatusBadge from "./StatusBadge.jsx";
import Icon from "./Icon.jsx";
export default function FlagsTable({ items, onOpen }) {
  return (
    <div className="table-wrap">
      <table className="flags">
        <thead>
          <tr>
            <th>Transaction / account</th>
            <th>Merchant / location</th>
            <th className="num">Amount</th>
            <th>Risk score</th>
            <th>Triggered rules</th>
            <th>Status</th>
            <th aria-label="Open transaction" />
          </tr>
        </thead>
        <tbody>
          {items.map((t) => (
            <tr key={t.transaction_id}>
              <td data-label="Transaction">
                <button
                  className="transaction-link"
                  onClick={() => onOpen(t.transaction_id)}
                >
                  {t.account_id}
                  <Icon name="arrow" size={13} />
                </button>
                <div className="table-secondary mono" title={t.transaction_id}>
                  {t.transaction_id.slice(0, 8).toUpperCase()}{" "}
                  <span className="table-dot">·</span>{" "}
                  <span title={dateTime(t.occurred_at)}>
                    {timeAgo(t.occurred_at)}
                  </span>
                </div>
              </td>
              <td data-label="Merchant">
                <strong className="merchant-name">{t.merchant}</strong>
                <div className="table-secondary location">
                  <Icon name="globe" size={12} />
                  {t.location_label || "Unknown location"}
                </div>
              </td>
              <td data-label="Amount" className="num amount-cell">
                {money(t.amount, t.currency)}
              </td>
              <td data-label="Risk">
                <RiskBadge level={t.risk_level} score={t.total_score} />
                <div className="score-track">
                  <span
                    className={`score-${t.risk_level.toLowerCase()}`}
                    style={{ width: `${t.total_score}%` }}
                  />
                </div>
              </td>
              <td data-label="Rules" className="rules-cell">
                {t.rules_triggered.map((r) => (
                  <span key={r} className="chip">
                    {ruleLabel(r)}
                  </span>
                ))}
              </td>
              <td data-label="Status">
                <StatusBadge status={t.status} />
                {t.notification_status && (
                  <div
                    className={`table-secondary alert-${t.notification_status.toLowerCase()}`}
                  >
                    {t.notification_status === "FAILED"
                      ? "Alert failed"
                      : t.notification_status === "PENDING"
                        ? "Alert pending"
                        : t.notification_channel === "ses"
                          ? "Alert emailed"
                          : "Alert logged"}
                  </div>
                )}
              </td>
              <td>
                <button
                  className="row-open icon-button"
                  aria-label={`Review transaction ${t.transaction_id}`}
                  onClick={() => onOpen(t.transaction_id)}
                >
                  <Icon name="chevron" size={16} />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
