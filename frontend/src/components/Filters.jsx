import { useEffect, useState } from "react";

const STATUS_TABS = [
  ["FLAGGED", "Flagged"],
  ["REVIEWED", "Reviewed"],
  ["CLEARED", "Cleared"],
  ["ALL", "All"],
];

export default function Filters({ filters, onChange }) {
  const [account, setAccount] = useState(filters.account_id);
  useEffect(() => setAccount(filters.account_id), [filters.account_id]);

  return (
    <div className="filters">
      <div className="tabs" role="tablist" aria-label="Status">
        {STATUS_TABS.map(([value, label]) => (
          <button
            key={value}
            role="tab"
            aria-selected={filters.status === value}
            className={filters.status === value ? "tab active" : "tab"}
            onClick={() => onChange({ status: value })}
          >
            {label}
          </button>
        ))}
      </div>
      <div className="filter-controls">
        <label>
          Risk
          <select value={filters.risk_level} onChange={(e) => onChange({ risk_level: e.target.value })}>
            <option value="">Any</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>
        </label>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            onChange({ account_id: account.trim() });
          }}
        >
          <label>
            Account
            <input
              type="search"
              value={account}
              placeholder="ACC-1001"
              onChange={(e) => setAccount(e.target.value)}
              onBlur={() => account.trim() !== filters.account_id && onChange({ account_id: account.trim() })}
            />
          </label>
        </form>
        <label>
          Sort
          <select value={filters.sort} onChange={(e) => onChange({ sort: e.target.value })}>
            <option value="score">Highest risk</option>
            <option value="newest">Newest</option>
          </select>
        </label>
      </div>
    </div>
  );
}
