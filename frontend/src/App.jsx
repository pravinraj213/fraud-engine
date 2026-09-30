import { useCallback, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { api } from "./api/client.js";
import AlertModePill from "./components/AlertModePill.jsx";
import ReviewerName from "./components/ReviewerName.jsx";
import StatsBar from "./components/StatsBar.jsx";
import usePolling from "./hooks/usePolling.js";

const REVIEWER_KEY = "reviewerName";

function readReviewer() {
  try {
    return localStorage.getItem(REVIEWER_KEY) || "";
  } catch {
    return "";
  }
}

function Logo() {
  return (
    <svg width="28" height="28" viewBox="0 0 32 32" aria-hidden="true">
      <path d="M16 2 4 6.5v8.2C4 22.3 9.1 28.6 16 30c6.9-1.4 12-7.7 12-15.3V6.5L16 2Z" fill="var(--accent)" />
      <path d="m10.5 16.2 3.8 3.8 7.4-8" fill="none" stroke="#fff" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export default function App() {
  const [reviewer, setReviewerState] = useState(readReviewer);
  const [stats, setStats] = useState(null);
  const [system, setSystem] = useState(null);

  const setReviewer = (name) => {
    setReviewerState(name);
    try {
      localStorage.setItem(REVIEWER_KEY, name);
    } catch {
      /* storage unavailable: keep the name for this session only */
    }
  };

  const refresh = useCallback(async () => {
    try {
      const [s, sys] = await Promise.all([api.stats(), api.system()]);
      setStats(s);
      setSystem(sys);
    } catch {
      /* pages show API errors; the header keeps its last numbers */
    }
  }, []);
  usePolling(refresh, 10000);

  const openFlags = stats?.by_status?.FLAGGED;

  return (
    <div className="app">
      <a className="skip-link" href="#main-content">Skip to content</a>
      <header className="topbar">
        <div className="topbar-inner">
          <NavLink to="/" className="brand">
            <Logo />
            <span>Fraud Rule Engine</span>
          </NavLink>
          <nav className="nav" aria-label="Main">
            <NavLink to="/" end>
              Review queue
              {openFlags > 0 && <span className="nav-count">{openFlags}</span>}
            </NavLink>
            <NavLink to="/simulator">Simulator</NavLink>
            <NavLink to="/rules">Rules</NavLink>
            <a href="/how-it-works.html">How it works ↗</a>
          </nav>
          <div className="topbar-right">
            <AlertModePill system={system} onChange={setSystem} />
            <ReviewerName value={reviewer} onChange={setReviewer} />
          </div>
        </div>
      </header>
      <main id="main-content" tabIndex={-1}>
        <div className="workspace-heading">
          <div><span className="eyebrow">RISK OPERATIONS</span><h2>Transaction oversight</h2></div>
          <span className="workspace-note">Detect. Investigate. Resolve.</span>
        </div>
        <StatsBar stats={stats} />
        <Outlet context={{ reviewer, refreshStats: refresh, system }} />
        <footer className="app-footer"><span>Fraud Rule Engine · Reviewer workspace</span><a href="/how-it-works.html">Understand the workflow →</a></footer>
      </main>
    </div>
  );
}
