import { useCallback, useState } from "react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api/client.js";
import Filters from "../components/Filters.jsx";
import FlagsTable from "../components/FlagsTable.jsx";
import Pagination from "../components/Pagination.jsx";
import usePolling from "../hooks/usePolling.js";

const PAGE_SIZE = 25;
const DEFAULTS = { status: "FLAGGED", risk_level: "", account_id: "", sort: "score", offset: "0" };

function readFilters(params) {
  const f = Object.fromEntries(Object.entries(DEFAULTS).map(([k, d]) => [k, params.get(k) ?? d]));
  return { ...f, offset: Math.max(0, Number(f.offset) || 0) };
}

export default function QueuePage() {
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const location = useLocation();
  const filters = readFilters(params);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  const query = JSON.stringify(filters);
  const load = useCallback(async () => {
    const f = JSON.parse(query);
    const request = { status: f.status, sort: f.sort, limit: PAGE_SIZE, offset: f.offset };
    if (f.risk_level) request.risk_level = f.risk_level;
    if (f.account_id) request.account_id = f.account_id;
    try {
      setData(await api.flags(request));
      setError(null);
    } catch (e) {
      setError(e.message);
    }
  }, [query]);
  usePolling(load, 10000);

  const update = (changes) => {
    const next = { ...filters, offset: 0, ...changes };
    const clean = Object.fromEntries(
      Object.entries(next).filter(([k, v]) => String(v) !== DEFAULTS[k] && v !== ""),
    );
    setParams(clean);
  };

  const open = (id) => navigate(`/transactions/${id}`, { state: { from: location.search } });

  return (
    <section>
      <div className="queue-head">
        <h1>Review queue</h1>
        {data && <span className="muted small">{data.total} {data.total === 1 ? "transaction" : "transactions"}</span>}
      </div>
      <Filters filters={filters} onChange={update} />
      {error && (
        <div className="banner banner-error" role="alert">
          <span>{error}</span>
          <button onClick={load}>Retry</button>
        </div>
      )}
      {!data && !error && <p className="empty">Loading flagged transactions…</p>}
      {data && data.items.length === 0 && (
        <p className="empty">
          {filters.status === "FLAGGED" && !filters.risk_level && !filters.account_id
            ? <>Nothing waiting for review. Generate some traffic in the <Link to="/simulator">simulator</Link>.</>
            : "No transactions match these filters."}
        </p>
      )}
      {data && data.items.length > 0 && (
        <>
          <FlagsTable items={data.items} onOpen={open} />
          <Pagination offset={filters.offset} limit={PAGE_SIZE} total={data.total}
                      onChange={(offset) => update({ offset })} />
        </>
      )}
    </section>
  );
}
