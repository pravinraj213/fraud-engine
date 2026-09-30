import { useCallback, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { api } from "./api/client.js";
import AlertModePill from "./components/AlertModePill.jsx";
import ReviewerName from "./components/ReviewerName.jsx";
import Icon from "./components/Icon.jsx";
import usePolling from "./hooks/usePolling.js";

function readReviewer() {
  try {
    return localStorage.getItem("reviewerName") || "";
  } catch {
    return "";
  }
}
export default function App() {
  const [reviewer, setReviewerState] = useState(readReviewer);
  const [stats, setStats] = useState(null);
  const [system, setSystem] = useState(null);
  const [connected, setConnected] = useState(null);
  const [updated, setUpdated] = useState(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const location = useLocation();
  const setReviewer = (name) => {
    setReviewerState(name);
    try {
      localStorage.setItem("reviewerName", name);
    } catch {
      /* Session-only identity */
    }
  };
  const refresh = useCallback(async () => {
    try {
      const [s, sys] = await Promise.all([api.stats(), api.system()]);
      setStats(s);
      setSystem(sys);
      setConnected(true);
      setUpdated(new Date());
    } catch {
      setConnected(false);
    }
  }, []);
  usePolling(refresh, 10000);
  const title = location.pathname.startsWith("/transactions/")
    ? "Transaction review"
    : location.pathname === "/rules"
      ? "Detection rules"
      : location.pathname === "/simulator"
        ? "Simulator"
        : "Review queue";
  return (
    <div className="app">
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      {menuOpen && (
        <button
          className="sidebar-scrim"
          aria-label="Close navigation"
          onClick={() => setMenuOpen(false)}
        />
      )}
      <aside className={`sidebar ${menuOpen ? "is-open" : ""}`}>
        <NavLink to="/" className="brand" onClick={() => setMenuOpen(false)}>
          <span className="brand-mark">
            <Icon name="shield" size={26} />
          </span>
          <span>
            sentinel<span className="brand-subtitle">FRAUD ENGINE</span>
          </span>
        </NavLink>
        <div className="workspace-switch">
          <span className="workspace-avatar">FE</span>
          <div>
            <strong>Fraud operations</strong>
            <small>Analyst workspace</small>
          </div>
          <span className="workspace-dot" />
        </div>
        <span className="nav-label">WORKSPACE</span>
        <nav className="nav" aria-label="Main">
          <NavLink to="/" end onClick={() => setMenuOpen(false)}>
            <Icon name="queue" />
            Review queue
            {stats?.by_status?.FLAGGED > 0 && (
              <span className="nav-count">{stats.by_status.FLAGGED}</span>
            )}
          </NavLink>
          <NavLink to="/rules" onClick={() => setMenuOpen(false)}>
            <Icon name="rules" />
            Detection rules
          </NavLink>
          <NavLink to="/simulator" onClick={() => setMenuOpen(false)}>
            <Icon name="play" />
            Simulator
          </NavLink>
          <a href="/how-it-works.html">
            <Icon name="globe" />
            How it works
          </a>
        </nav>
        <div className="sidebar-bottom">
          <div className="sidebar-note">
            <Icon name="shield" />
            <strong>Clarity behind every flag.</strong>
            <p>
              Understand the signals.
              <br />
              Make a confident decision.
            </p>
            <NavLink to="/rules" onClick={() => setMenuOpen(false)}>
              Explore your rules <Icon name="arrow" size={15} />
            </NavLink>
          </div>
          <div className="reviewer-profile">
            <span className="avatar">
              {reviewer ? (
                reviewer.slice(0, 2).toUpperCase()
              ) : (
                <Icon name="user" size={18} />
              )}
            </span>
            <ReviewerName value={reviewer} onChange={setReviewer} />
          </div>
          <div className="sidebar-foot">
            Sentinel console <span>v1.0</span>
          </div>
        </div>
      </aside>
      <div className="app-body">
        <header className="topbar">
          <div className="breadcrumbs">
            <button
              className="icon-button mobile-menu"
              aria-label="Open navigation"
              aria-expanded={menuOpen}
              onClick={() => setMenuOpen(true)}
            >
              <Icon name="menu" />
            </button>
            <span>Workspace</span>
            <Icon name="chevron" size={13} />
            <strong>{title}</strong>
          </div>
          <div className="topbar-right">
            <span
              className={`connection ${connected === true ? "online" : connected === false ? "offline" : ""}`}
            >
              <i />
              {connected === true
                ? "Engine connected"
                : connected === false
                  ? "Connection lost"
                  : "Connecting"}
            </span>
            <span className="header-divider" />
            <AlertModePill system={system} onChange={setSystem} />
          </div>
        </header>
        <main id="main-content" tabIndex={-1}>
          {connected === false && (
            <div className="banner banner-error" role="alert">
              <span>
                Unable to reach the engine. Displayed data may be out of date.
              </span>
              <button onClick={refresh}>Reconnect</button>
            </div>
          )}
          <Outlet
            context={{
              reviewer,
              refreshStats: refresh,
              system,
              stats,
              updated,
            }}
          />
          <footer className="content-footer">
            <span>
              <Icon name="shield" size={14} /> Sentinel · Fraud intelligence,
              explained.
            </span>
            <span>All amounts in INR · Times shown locally</span>
          </footer>
        </main>
      </div>
    </div>
  );
}
