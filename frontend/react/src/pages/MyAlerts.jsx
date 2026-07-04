import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Leaf, History, Home as HomeIcon, LogOut, CheckCircle2, XCircle } from "lucide-react";
import { apiBase, useAuth } from "../AuthContext.jsx";
import "./MyAlerts.css";

export default function MyAlerts() {
  const { token, username, logout } = useAuth();
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    (async () => {
      setLoading(true);
      setErr("");
      try {
        const r = await fetch(`${apiBase}/my-alerts`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        const data = await r.json();
        if (!r.ok) throw new Error(data.error || "Failed to load alerts");
        setAlerts(data.alerts || []);
      } catch (e) {
        setErr(e.message || String(e));
      } finally {
        setLoading(false);
      }
    })();
  }, [token]);

  return (
    <div className="alerts-page">
      <div className="tool-topbar">
        <Link to="/" className="tool-topbar-brand">
          <Leaf size={20} /> Eco-Guard
        </Link>
        <div className="tool-topbar-actions">
          <span className="tool-topbar-user">Signed in as {username}</span>
          <Link to="/tool" className="tool-topbar-link">
            <History size={15} /> Analysis Tool
          </Link>
          <Link to="/" className="tool-topbar-link">
            <HomeIcon size={15} /> Home
          </Link>
          <button type="button" className="tool-topbar-logout" onClick={logout}>
            <LogOut size={15} /> Logout
          </button>
        </div>
      </div>

      <div className="alerts-content">
        <h1>My Alert History</h1>
        <p className="alerts-sub">Every legal/illegal decision you've made, with region, status, and time.</p>

        {loading && <p className="alerts-loading">Loading your history…</p>}
        {err && <p className="alerts-error">{err}</p>}

        {!loading && !err && alerts.length === 0 && (
          <div className="alerts-empty">
            <History size={32} />
            <p>No alerts yet. Run an analysis and verify it to see history here.</p>
            <Link to="/tool" className="alerts-cta">Go to Analysis Tool</Link>
          </div>
        )}

        {!loading && alerts.length > 0 && (
          <div className="alerts-table-wrap">
            <table className="alerts-table">
              <thead>
                <tr>
                  <th>Region</th>
                  <th>Decision</th>
                  <th>Status</th>
                  <th>Forest Loss %</th>
                  <th>Analysis ID</th>
                  <th>When</th>
                </tr>
              </thead>
              <tbody>
                {alerts.map((a) => (
                  <tr key={a.id}>
                    <td style={{ textTransform: "capitalize" }}>{a.region_slug}</td>
                    <td>
                      <span className={`decision-pill ${a.decision === "illegal" ? "illegal" : "legal"}`}>
                        {a.decision === "illegal" ? <XCircle size={13} /> : <CheckCircle2 size={13} />}
                        {a.decision}
                      </span>
                    </td>
                    <td>{a.status || "–"}</td>
                    <td>{a.loss_percent != null ? `${a.loss_percent}%` : "–"}</td>
                    <td className="mono-cell">{a.analysis_id?.slice(0, 8)}…</td>
                    <td className="mono-cell">
                      {a.verified_at ? new Date(a.verified_at).toLocaleString() : "–"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}