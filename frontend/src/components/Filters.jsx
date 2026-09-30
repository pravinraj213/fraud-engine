import { useEffect, useState } from "react";
import Icon from "./Icon.jsx";
const STATUS_TABS = [
  ["FLAGGED", "Awaiting review"],
  ["REVIEWED", "Reviewed"],
  ["CLEARED", "Cleared"],
  ["ALL", "All flags"],
];
export default function Filters({ filters, onChange }) {
  const [account, setAccount] = useState(filters.account_id);
  useEffect(() => setAccount(filters.account_id), [filters.account_id]);
  return (
    <div className="filters">
      <div className="tabs" role="group" aria-label="Status">
        {STATUS_TABS.map(([value, label]) => (
          <button
            key={value}
            aria-pressed={filters.status === value}
            className={filters.status === value ? "tab active" : "tab"}
            onClick={() => onChange({ status: value })}
          >
            {label}
          </button>
        ))}
      </div>
      <div className="filter-controls">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            onChange({ account_id: account.trim() });
          }}
        >
          <label className="account-search">
            <Icon name="search" size={15} />
            <input
              aria-label="Search by account ID"
              type="search"
              value={account}
              placeholder="Search by account ID…"
              onChange={(e) => setAccount(e.target.value)}
              onBlur={() =>
                account.trim() !== filters.account_id &&
                onChange({ account_id: account.trim() })
              }
            />
          </label>
        </form>
        <label>
          Risk level
          <select
            value={filters.risk_level}
            onChange={(e) => onChange({ risk_level: e.target.value })}
          >
            <option value="">All levels</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>
        </label>
        <label>
          Sort by
          <select
            value={filters.sort}
            onChange={(e) => onChange({ sort: e.target.value })}
          >
            <option value="score">Highest risk</option>
            <option value="newest">Newest first</option>
          </select>
        </label>
      </div>
    </div>
  );
}
