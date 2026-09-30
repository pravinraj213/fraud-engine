import { useCallback, useRef, useState } from "react";
import {
  Link,
  useLocation,
  useNavigate,
  useOutletContext,
  useSearchParams,
} from "react-router-dom";
import { api } from "../api/client.js";
import Filters from "../components/Filters.jsx";
import FlagsTable from "../components/FlagsTable.jsx";
import Pagination from "../components/Pagination.jsx";
import StatsBar from "../components/StatsBar.jsx";
import RiskOverview from "../components/RiskOverview.jsx";
import Icon from "../components/Icon.jsx";
import usePolling from "../hooks/usePolling.js";
import { exportTransactions } from "../utils/export.js";

const PAGE_SIZE = 10;
const DEFAULTS = {
  status: "FLAGGED",
  risk_level: "",
  account_id: "",
  sort: "score",
  offset: "0",
};
function readFilters(params) {
  const f = Object.fromEntries(
    Object.entries(DEFAULTS).map(([k, d]) => [k, params.get(k) ?? d]),
  );
  return {
    ...f,
    status: ["FLAGGED", "REVIEWED", "CLEARED", "ALL"].includes(f.status)
      ? f.status
      : "FLAGGED",
    risk_level: ["HIGH", "MEDIUM", "LOW"].includes(f.risk_level)
      ? f.risk_level
      : "",
    sort: f.sort === "newest" ? "newest" : "score",
    offset: Number.isSafeInteger(Number(f.offset))
      ? Math.max(0, Number(f.offset))
      : 0,
  };
}
export default function QueuePage() {
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const location = useLocation();
  const { stats, system, refreshStats } = useOutletContext();
  const filters = readFilters(params);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [updated, setUpdated] = useState(null);
  const [notice, setNotice] = useState("");
  const requestId = useRef(0);
  const query = JSON.stringify(filters);
  const currentQuery = useRef(query);
  currentQuery.current = query;
  const load = useCallback(async () => {
    const id = ++requestId.current;
    const f = JSON.parse(query);
    const request = {
      status: f.status,
      sort: f.sort,
      limit: PAGE_SIZE,
      offset: f.offset,
    };
    if (f.risk_level) request.risk_level = f.risk_level;
    if (f.account_id) request.account_id = f.account_id;
    setBusy(true);
    try {
      const result = await api.flags(request);
      if (id !== requestId.current || currentQuery.current !== query) return;
      if (f.offset > 0 && f.offset >= result.total) {
        const next = new URLSearchParams(f);
        next.set(
          "offset",
          String(
            Math.max(0, Math.floor((result.total - 1) / PAGE_SIZE) * PAGE_SIZE),
          ),
        );
        setParams(next, { replace: true });
        return;
      }
      setData({ ...result, query });
      setError(null);
      setUpdated(new Date());
    } catch (e) {
      if (id === requestId.current && currentQuery.current === query)
        setError(e.message);
    } finally {
      if (id === requestId.current) setBusy(false);
    }
  }, [query, setParams]);
  usePolling(load, 10000);
  const visible = data?.query === query ? data : null;
  const update = (changes) => {
    setNotice("");
    setError(null);
    const next = { ...filters, offset: 0, ...changes };
    setParams(
      Object.fromEntries(
        Object.entries(next).filter(
          ([k, v]) => String(v) !== DEFAULTS[k] && v !== "",
        ),
      ),
    );
  };
  const open = (id) =>
    navigate(`/transactions/${id}`, { state: { from: location.search } });
  const exportPage = () => {
    exportTransactions(visible.items);
    setNotice(`Exported ${visible.items.length} transactions from this page.`);
  };
  return (
    <section className="queue-page">
      <div className="page-heading">
        <div>
          <div className="eyebrow page-eyebrow">YOUR OPERATIONS, IN FOCUS</div>
          <h1>
            Review queue<span className="heading-dot">.</span>
          </h1>
          <p>Spot the signals. Investigate risk. Stay one step ahead.</p>
        </div>
        <div className="heading-actions">
          <button
            className="button-icon"
            disabled={busy}
            onClick={() => {
              load();
              refreshStats();
            }}
          >
            <Icon name="refresh" size={16} className={busy ? "spin" : ""} />
            Refresh
          </button>
          <Link className="btn-primary button-icon" to="/simulator">
            <Icon name="play" size={16} />
            Run simulation
          </Link>
        </div>
      </div>
      <div className="section-label">
        <span>Portfolio overview</span>
        <span>ALL TIME</span>
      </div>
      <StatsBar stats={stats} />
      <RiskOverview
        stats={stats}
        system={system}
        onFilter={(risk_level) => update({ status: "FLAGGED", risk_level })}
      />
      <section className="queue-panel" aria-label="Transaction review queue">
        <div className="queue-head">
          <div>
            <h2>
              Flagged transactions{" "}
              <span className="count-pill">
                {visible ? visible.total : "—"}
              </span>
            </h2>
            <p>Review the evidence and decide what happens next.</p>
          </div>
          <button
            className="button-icon export-button"
            disabled={!visible?.items.length || !!error}
            onClick={exportPage}
          >
            <Icon name="download" size={16} />
            Export page
          </button>
        </div>
        <Filters filters={filters} onChange={update} stats={stats} />
        {notice && (
          <div className="banner banner-ok" role="status">
            {notice}
          </div>
        )}
        {error && (
          <div className="banner banner-error" role="alert">
            <span>
              {error} {visible ? "Showing last successful results." : ""}
            </span>
            <button onClick={load}>Retry</button>
          </div>
        )}
        {!visible && !error && (
          <div className="empty loading-state" role="status">
            <Icon name="refresh" className="spin" />
            <p>Loading transactions…</p>
          </div>
        )}
        {visible && visible.items.length === 0 && (
          <div className="empty">
            <span className="empty-icon">
              <Icon name="shield" size={28} />
            </span>
            <h3>
              {filters.account_id || filters.risk_level
                ? "No matching transactions"
                : "You’re all caught up"}
            </h3>
            <p>
              {filters.account_id || filters.risk_level
                ? "Try another account or adjust your risk filter."
                : "No transactions in this view. Run a simulation to explore the review workflow."}
            </p>
            {filters.account_id || filters.risk_level ? (
              <button
                onClick={() => update({ account_id: "", risk_level: "" })}
              >
                Clear filters
              </button>
            ) : (
              <Link to="/simulator">Open simulator →</Link>
            )}
          </div>
        )}
        {visible && visible.items.length > 0 && (
          <FlagsTable items={visible.items} onOpen={open} />
        )}
        <div className="queue-footer">
          <span className="refresh-status">
            <i />
            {updated
              ? `Updated ${updated.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} · Refreshes every 10s`
              : "Automatic refresh every 10s"}
          </span>
          {visible && (
            <Pagination
              offset={filters.offset}
              limit={PAGE_SIZE}
              total={visible.total}
              onChange={(offset) => update({ offset })}
            />
          )}
        </div>
      </section>
    </section>
  );
}
