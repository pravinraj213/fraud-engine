import { useCallback, useEffect, useState } from "react";
import { Link, useLocation, useOutletContext, useParams } from "react-router-dom";
import { api } from "../api/client.js";
import ReviewHistory from "../components/ReviewHistory.jsx";
import ReviewPanel from "../components/ReviewPanel.jsx";
import RiskBadge from "../components/RiskBadge.jsx";
import RuleHitCard from "../components/RuleHitCard.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import { dateTime, money, timeOnly } from "../utils/format.js";

function AlertLine({ notification }) {
  if (!notification) return null;
  if (notification.status === "SENT" && notification.channel === "ses") {
    return <p className="alert-line alert-sent">Alert emailed at {timeOnly(notification.created_at)}</p>;
  }
  if (notification.status === "SENT") {
    return <p className="alert-line muted">Alert written to server log at {timeOnly(notification.created_at)} (email off)</p>;
  }
  if (notification.status === "FAILED") {
    return <p className="alert-line alert-failed">Alert failed: {notification.error}</p>;
  }
  return <p className="alert-line muted">Alert sending…</p>;
}

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard blocked: the ID is still selectable */
    }
  };
  return <button className="btn-small" onClick={copy}>{copied ? "Copied" : "Copy"}</button>;
}

export default function TransactionPage() {
  const { id } = useParams();
  const location = useLocation();
  const { reviewer, refreshStats } = useOutletContext();
  const [detail, setDetail] = useState(null);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    try {
      setDetail(await api.transaction(id));
      setError(null);
    } catch (e) {
      setError(e);
    }
  }, [id]);
  useEffect(() => { load(); }, [load]);

  const submitReview = async (action, note) => {
    try {
      setDetail(await api.review(id, { action, reviewer, note }));
      refreshStats();
    } catch (e) {
      if (e.status === 409) await load();
      throw e;
    }
  };

  const back = <Link className="back" to={`/${location.state?.from ?? ""}`}>← Back to queue</Link>;

  if (error) {
    return (
      <section>
        {back}
        <div className="banner banner-error" role="alert">
          <span>{error.status === 404 ? "Transaction not found." : error.message}</span>
          {error.status !== 404 && <button onClick={load}>Retry</button>}
        </div>
      </section>
    );
  }
  if (!detail) return <section>{back}<p className="empty">Loading…</p></section>;

  const { transaction: t, assessment: a } = detail;
  return (
    <section className="detail">
      {back}
      <header className="detail-head">
        <div>
          <h1>{money(t.amount, t.currency)} <span className="muted">at</span> {t.merchant}</h1>
          <div className="badges">
            <RiskBadge level={a.risk_level} score={a.total_score} />
            <StatusBadge status={a.status} />
          </div>
        </div>
        <AlertLine notification={detail.notification} />
      </header>

      <div className="detail-grid">
        <div className="detail-main">
          <section className="panel">
            <h2>Risk breakdown</h2>
            {detail.rule_hits.length === 0
              ? <p className="muted">No rules triggered.</p>
              : detail.rule_hits.map((h) => <RuleHitCard key={h.rule_name} hit={h} />)}
          </section>
          <ReviewHistory reviews={detail.reviews} />
        </div>

        <aside className="detail-side">
          <section className="panel">
            <h2>Transaction</h2>
            <dl className="facts">
              <div><dt>Account</dt><dd className="mono">{t.account_id}</dd></div>
              <div><dt>Time</dt><dd>{dateTime(t.occurred_at)}</dd></div>
              <div><dt>Location</dt><dd>{t.location_label || "–"}<br />
                <small className="muted">{t.latitude.toFixed(4)}, {t.longitude.toFixed(4)}</small></dd></div>
              <div><dt>Currency</dt><dd>{t.currency}</dd></div>
              <div><dt>Transaction ID</dt><dd className="mono id-row"><span>{t.id}</span> <CopyButton text={t.id} /></dd></div>
            </dl>
          </section>
          <ReviewPanel key={t.id} allowedActions={detail.allowed_actions} reviewer={reviewer} onSubmit={submitReview} />
        </aside>
      </div>
    </section>
  );
}
