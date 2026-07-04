import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { GeoJSON, MapContainer, TileLayer, useMap } from "react-leaflet";
import {
  Leaf,
  Satellite,
  MapPin,
  ShieldCheck,
  AlertTriangle,
  Radar,
  CheckCircle2,
  XCircle,
  Trees,
  CalendarRange,
  LogOut,
  History,
  Home as HomeIcon,
  ArrowLeft,
  RotateCcw,
  Droplets,
} from "lucide-react";
import { apiBase, useAuth } from "../AuthContext.jsx";
import "../App.css";
import "./Tool.css";

function FlyToRegion({ lat, lon, zoom = 9 }) {
  const map = useMap();
  useEffect(() => {
    if (lat == null || lon == null || Number.isNaN(Number(lat)) || Number.isNaN(Number(lon))) return;
    map.flyTo([Number(lat), Number(lon)], zoom, { duration: 0.75 });
  }, [lat, lon, zoom, map]);
  return null;
}

function NdviDial({ value, threshold }) {
  const domainMin = -0.3;
  const domainMax = 0.1;
  const clamped = Math.max(domainMin, Math.min(domainMax, value ?? 0));
  const pct = ((clamped - domainMin) / (domainMax - domainMin)) * 100;
  return (
    <div className="ndvi-dial">
      <div className="ndvi-dial-track">
        <div className="ndvi-dial-marker" style={{ left: `${pct}%` }} />
      </div>
      <div className="ndvi-dial-labels">
        <span>loss</span>
        <span>threshold {threshold ?? "–"}</span>
        <span>gain</span>
      </div>
    </div>
  );
}

function resolveImageUrl(url) {
  if (!url) return "";
  const u = String(url);
  if (u.startsWith("data:") || u.startsWith("http://") || u.startsWith("https://")) return u;
  if (u.startsWith("/")) return `${apiBase}${u}`;
  return u;
}

function buildFallbackPreviewUrl(periodLabel, dateRange, variant = "before") {
  const q = new URLSearchParams({ t1: periodLabel || "NDVI preview", t2: dateRange || "", v: variant });
  return `${apiBase}/public/period-preview.svg?${q.toString()}`;
}

function statusClass(status) {
  if (!status) return "status-normal";
  const s = String(status).toLowerCase();
  if (s.includes("critical")) return "status-critical";
  if (s.includes("moderate")) return "status-moderate";
  return "status-normal";
}

export default function Tool() {
  const { token, username, logout } = useAuth();
  const [stage, setStage] = useState("setup"); // "setup" | "results"

  const authGet = useCallback(
    async (path) => {
      const r = await fetch(`${apiBase}${path}`, { headers: { Authorization: `Bearer ${token}` } });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(data.error || data.detail || r.statusText);
      return data;
    },
    [token],
  );

  const authPost = useCallback(
    async (path, body) => {
      const r = await fetch(`${apiBase}${path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify(body),
      });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(data.error || data.detail || r.statusText);
      return data;
    },
    [token],
  );

  const [regions, setRegions] = useState([]);
  const [slug, setSlug] = useState("");
  const [forestPayload, setForestPayload] = useState(null);
  const [p1s, setP1s] = useState("2024-01-01");
  const [p1e, setP1e] = useState("2024-01-03");
  const [analysis, setAnalysis] = useState(null);
  const [loadingRegions, setLoadingRegions] = useState(false);
  const [loadingForests, setLoadingForests] = useState(false);
  const [loadingAnalyze, setLoadingAnalyze] = useState(false);
  const [loadingVerify, setLoadingVerify] = useState(false);
  const [err, setErr] = useState("");
  const [verifyMsg, setVerifyMsg] = useState("");
  const [verifyOk, setVerifyOk] = useState(true);
  const [periodImgErr, setPeriodImgErr] = useState({ before: false, after: false });

  useEffect(() => {
    setPeriodImgErr({ before: false, after: false });
  }, [analysis?.analysis_id]);

  const loadRegions = useCallback(async () => {
    setLoadingRegions(true);
    setErr("");
    try {
      const data = await authGet("/regions");
      const list = data.regions || [];
      setRegions(list);
      setSlug((prev) => prev || list[0]?.slug || "");
    } catch (e) {
      setErr(e.message || String(e));
    } finally {
      setLoadingRegions(false);
    }
  }, [authGet]);

  useEffect(() => {
    loadRegions();
  }, [loadRegions]);

  useEffect(() => {
    if (!slug) return;
    let cancelled = false;
    (async () => {
      setLoadingForests(true);
      setErr("");
      try {
        const data = await authGet(`/forests/${encodeURIComponent(slug)}`);
        if (!cancelled) setForestPayload(data);
      } catch (e) {
        if (!cancelled) setErr(e.message || String(e));
      } finally {
        if (!cancelled) setLoadingForests(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [slug, authGet]);

  const mapCenter = useMemo(() => {
    if (forestPayload?.center_lat != null && forestPayload?.center_lon != null) {
      return [forestPayload.center_lat, forestPayload.center_lon];
    }
    const r = regions.find((x) => x.slug === slug);
    if (r?.center_lat != null && r?.center_lon != null) return [r.center_lat, r.center_lon];
    return [17.385, 78.4867];
  }, [forestPayload, regions, slug]);

  async function runAnalyze() {
    setLoadingAnalyze(true);
    setErr("");
    setVerifyMsg("");
    setAnalysis(null);
    try {
      const q = new URLSearchParams({ period1_start: p1s, period1_end: p1e });
      const data = await authGet(`/analyze/${encodeURIComponent(slug)}?${q.toString()}`);
      setAnalysis(data);
      setStage("results");
    } catch (e) {
      setErr(e.message || String(e));
    } finally {
      setLoadingAnalyze(false);
    }
  }

  async function runVerify(decision) {
    if (!analysis?.analysis_id) return;
    setLoadingVerify(true);
    setVerifyMsg("");
    try {
      const res = await authPost("/verify", { analysis_id: analysis.analysis_id, decision });
      setVerifyOk(decision === "legal");
      if (res.alerts_sent) {
        const sd = res.alerts_summary?.sms_delivery;
        if (sd === "twilio_live") setVerifyMsg(`Marked illegal — SMS sent via Twilio.`);
        else if (sd === "simulated_log_only") setVerifyMsg(`Marked illegal — SMS console-only (simulation).`);
        else setVerifyMsg(`Marked illegal — SMS skipped (Twilio disabled).`);
      } else {
        setVerifyMsg(`Marked legal — no alerts sent.`);
      }
    } catch (e) {
      setErr(e.message || String(e));
    } finally {
      setLoadingVerify(false);
    }
  }

  function newAnalysis() {
    setAnalysis(null);
    setVerifyMsg("");
    setErr("");
    setStage("setup");
  }

  const gj = analysis?.affected_geojson;
  const beforeFallbackUrl = analysis
    ? buildFallbackPreviewUrl(`Before — ${analysis.region_name || ""}`, analysis.period1?.start || "", "before")
    : "";
  const afterFallbackUrl = analysis
    ? buildFallbackPreviewUrl(`After — ${analysis.region_name || ""}`, analysis.period1?.end || "", "after")
    : "";
  const beforeImageUrl = analysis ? resolveImageUrl(analysis.period_images?.before_url || beforeFallbackUrl) : "";
  const afterImageUrl = analysis ? resolveImageUrl(analysis.period_images?.after_url || afterFallbackUrl) : "";

  return (
    <div className="tool-page">
      <div className="tool-topbar">
        <Link to="/" className="tool-topbar-brand">
          <Leaf size={20} /> Eco-Guard
        </Link>
        <div className="tool-topbar-actions">
          <span className="tool-topbar-user">Signed in as {username}</span>
          <Link to="/water-tool" className="tool-topbar-link">
            <Droplets size={15} /> Water Tool
          </Link>
          <Link to="/my-alerts" className="tool-topbar-link">
            <History size={15} /> My Alerts
          </Link>
          <Link to="/" className="tool-topbar-link">
            <HomeIcon size={15} /> Home
          </Link>
          <button type="button" className="tool-topbar-logout" onClick={logout}>
            <LogOut size={15} /> Logout
          </button>
        </div>
      </div>

      {/* ===== Stage 1: Setup ===== */}
      {stage === "setup" && (
        <div className="stage-grid">
          <div className="panel setup-panel">
            <div className="panel-title"><Satellite size={16} /> New Analysis</div>

            <label htmlFor="region"><MapPin size={13} /> Region of Interest</label>
            {loadingRegions && <div className="loading"><Radar size={14} /> Loading regions…</div>}
            <select id="region" value={slug} onChange={(e) => setSlug(e.target.value)} disabled={!regions.length}>
              {regions.map((r) => (
                <option key={r.slug} value={r.slug}>{r.name}</option>
              ))}
            </select>

            <label style={{ marginTop: "1rem" }}><Trees size={13} /> Forests in region</label>
            {loadingForests && <div className="loading"><Radar size={14} /> Loading forests…</div>}
            {!loadingForests && forestPayload?.forests && (
              <ul className="forest-list dark-list">
                {forestPayload.forests.map((f) => (
                  <li key={f}><Leaf size={13} />{f}</li>
                ))}
              </ul>
            )}

            <label style={{ marginTop: "1rem" }}><CalendarRange size={13} /> Analysis window (max 3 days)</label>
            <div className="dates-grid">
              <div>
                <label>Start</label>
                <input type="date" value={p1s} onChange={(e) => setP1s(e.target.value)} />
              </div>
              <div>
                <label>End</label>
                <input type="date" value={p1e} onChange={(e) => setP1e(e.target.value)} />
              </div>
            </div>

            <button type="button" className="btn-primary" style={{ marginTop: "1.4rem" }} onClick={runAnalyze} disabled={loadingAnalyze || !slug}>
              <Radar size={16} /> {loadingAnalyze ? "Analyzing…" : "Run analysis"}
            </button>

            {err && <p className="error" style={{ marginTop: "0.85rem" }}><AlertTriangle size={15} style={{ marginTop: 1, flexShrink: 0 }} />{err}</p>}
          </div>

          <div className="panel map-panel">
            <div className="panel-title"><MapPin size={16} /> Region Map</div>
            <div className="map-inner">
              <MapContainer center={mapCenter} zoom={8} style={{ height: "100%", width: "100%" }} scrollWheelZoom>
                <FlyToRegion lat={mapCenter[0]} lon={mapCenter[1]} zoom={9} />
                <TileLayer attribution="&copy; OSM" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
              </MapContainer>
            </div>
          </div>
        </div>
      )}

      {/* ===== Stage 2: Results ===== */}
      {stage === "results" && analysis && (
        <div className="stage-grid">
          <div className="panel results-images-panel">
            <button type="button" className="back-link" onClick={newAnalysis}>
              <ArrowLeft size={14} /> New analysis
            </button>
            <div className="panel-title" style={{ marginTop: "0.5rem" }}><Satellite size={16} /> Before / After</div>
            <div className="compare-stack">
              <div className="compare-card">
                <div className="compare-title">Start · {analysis.period1?.start}</div>
                <div className="compare-image-wrap">
                  {!periodImgErr.before ? (
                    <img className="compare-image" src={beforeImageUrl} alt="before" onError={(e) => {
                      if (!e.currentTarget.dataset.fb) { e.currentTarget.dataset.fb = "1"; e.currentTarget.src = resolveImageUrl(beforeFallbackUrl); return; }
                      setPeriodImgErr((p) => ({ ...p, before: true }));
                    }} />
                  ) : <div className="image-fallback">Before image unavailable.</div>}
                </div>
              </div>
              <div className="compare-card">
                <div className="compare-title">End · {analysis.period1?.end}</div>
                <div className="compare-image-wrap">
                  {!periodImgErr.after ? (
                    <img className="compare-image" src={afterImageUrl} alt="after" onError={(e) => {
                      if (!e.currentTarget.dataset.fb) { e.currentTarget.dataset.fb = "1"; e.currentTarget.src = resolveImageUrl(afterFallbackUrl); return; }
                      setPeriodImgErr((p) => ({ ...p, after: true }));
                    }} />
                  ) : <div className="image-fallback">After image unavailable.</div>}
                </div>
              </div>
            </div>

            <div className="map-wrap-small">
              <MapContainer center={mapCenter} zoom={8} style={{ height: "100%", width: "100%" }} scrollWheelZoom={false}>
                <FlyToRegion lat={mapCenter[0]} lon={mapCenter[1]} zoom={9} />
                <TileLayer attribution="&copy; OSM" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
                {gj && gj.features?.length > 0 && (
                  <GeoJSON data={gj} style={() => ({ color: "#D9B44A", weight: 2, fillOpacity: 0.25 })} />
                )}
              </MapContainer>
            </div>
          </div>

          <div className="panel results-stats-panel">
            <div className="panel-title"><Leaf size={16} /> Results — {analysis.region_name}</div>

            <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap", marginBottom: "0.5rem" }}>
              <span className={`status-pill ${statusClass(analysis.status)}`}>{analysis.status}</span>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem", color: "var(--text-muted)" }}>
                {analysis.period1?.start} → {analysis.period2?.end}
              </span>
            </div>

            <NdviDial value={analysis.ndvi_change_forest} threshold={analysis.ndvi_loss_threshold_used} />

            <div className="readout-grid">
              <div className="readout">
                <div className="readout-label">Forest loss</div>
                <div className="readout-value">{analysis.loss_percent}%</div>
              </div>
              <div className="readout">
                <div className="readout-label">NDVI change</div>
                <div className="readout-value">{analysis.ndvi_change_forest}</div>
              </div>
              <div className="readout">
                <div className="readout-label">Data source</div>
                <div className="readout-value" style={{ fontSize: "0.85rem" }}>
                  {analysis.simulated ? "Simulated" : "Live satellite"}
                </div>
              </div>
            </div>

            {analysis.gee_composite_note && (
              <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", marginTop: "0.7rem" }}>{analysis.gee_composite_note}</p>
            )}

            <div className="panel verify-inline-panel">
              <div className="panel-title"><ShieldCheck size={14} /> Admin verification</div>
              <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", margin: "0 0 0.6rem" }}>
                Alerts fire only when you mark <strong style={{ color: "var(--red)" }}>illegal</strong>. Recorded as <strong>{username}</strong>.
              </p>
              <div className="btn-row">
                <button type="button" className="btn-legal" disabled={loadingVerify} onClick={() => runVerify("legal")}>
                  <CheckCircle2 size={15} /> {loadingVerify ? "…" : "Legal"}
                </button>
                <button type="button" className="btn-illegal" disabled={loadingVerify} onClick={() => runVerify("illegal")}>
                  <XCircle size={15} /> {loadingVerify ? "…" : "Illegal"}
                </button>
              </div>
              {verifyMsg && (
                <p className="verify-msg">
                  {verifyOk ? <CheckCircle2 size={14} style={{ color: "var(--green)", flexShrink: 0, marginTop: 1 }} /> : <AlertTriangle size={14} style={{ color: "var(--red)", flexShrink: 0, marginTop: 1 }} />}
                  {verifyMsg}
                </p>
              )}
              <button type="button" className="new-analysis-btn" onClick={newAnalysis}>
                <RotateCcw size={14} /> Start a new analysis
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}