import { useCallback, useEffect, useMemo, useState } from "react";
import { GeoJSON, MapContainer, TileLayer, useMap } from "react-leaflet";
import "./App.css";

/** Leaflet ignores `center` prop updates; fly when region / forest payload changes. */
function FlyToRegion({ lat, lon, zoom = 9 }) {
  const map = useMap();
  useEffect(() => {
    if (lat == null || lon == null || Number.isNaN(Number(lat)) || Number.isNaN(Number(lon))) return;
    map.flyTo([Number(lat), Number(lon)], zoom, { duration: 0.75 });
  }, [lat, lon, zoom, map]);
  return null;
}

// Dev: use Vite proxy (/api -> Flask :5000) to avoid CORS. Override with VITE_API_URL for production.
const apiBase =
  import.meta.env.VITE_API_URL ||
  (import.meta.env.DEV ? "/api" : "http://127.0.0.1:5000");
const adminToken = import.meta.env.VITE_ADMIN_TOKEN || "dev-admin-token";

function resolveImageUrl(url) {
  if (!url) return "";
  const u = String(url);
  if (u.startsWith("data:") || u.startsWith("http://") || u.startsWith("https://")) return u;
  if (u.startsWith("/")) return `${apiBase}${u}`;
  return u;
}

function buildFallbackPreviewUrl(periodLabel, dateRange, variant = "before") {
  const q = new URLSearchParams({
    t1: periodLabel || "NDVI preview",
    t2: dateRange || "",
    v: variant,
  });
  return `${apiBase}/public/period-preview.svg?${q.toString()}`;
}

async function apiGet(path) {
  let r;
  try {
    r = await fetch(`${apiBase}${path}`, {
      headers: { "X-Admin-Token": adminToken },
    });
  } catch (e) {
    const msg = e?.message ? String(e.message) : String(e);
    throw new Error(
      `Backend unavailable (expected Flask on http://127.0.0.1:5000). Start it with: cd backend\\flask && python run.py. Original error: ${msg}`,
    );
  }
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.error || data.detail || r.statusText);
  return data;
}

async function apiPost(path, body) {
  let r;
  try {
    r = await fetch(`${apiBase}${path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Admin-Token": adminToken,
      },
      body: JSON.stringify(body),
    });
  } catch (e) {
    const msg = e?.message ? String(e.message) : String(e);
    throw new Error(
      `Backend unavailable (expected Flask on http://127.0.0.1:5000). Start it with: cd backend\\flask && python run.py. Original error: ${msg}`,
    );
  }
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.error || data.detail || r.statusText);
  return data;
}

function statusClass(status) {
  if (!status) return "status-normal";
  const s = String(status).toLowerCase();
  if (s.includes("critical")) return "status-critical";
  if (s.includes("moderate")) return "status-moderate";
  return "status-normal";
}

export default function App() {
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
  const [adminName, setAdminName] = useState(() => localStorage.getItem("ecoguard_admin_name") || "");
  const [periodImgErr, setPeriodImgErr] = useState({ before: false, after: false });

  useEffect(() => {
    setPeriodImgErr({ before: false, after: false });
  }, [analysis?.analysis_id]);

  const loadRegions = useCallback(async () => {
    setLoadingRegions(true);
    setErr("");
    try {
      const data = await apiGet("/regions");
      const list = data.regions || [];
      setRegions(list);
      setSlug((prev) => prev || list[0]?.slug || "");
    } catch (e) {
      setErr(e.message || String(e));
    } finally {
      setLoadingRegions(false);
    }
  }, []);

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
        const data = await apiGet(`/forests/${encodeURIComponent(slug)}`);
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
  }, [slug]);

  const mapCenter = useMemo(() => {
    if (forestPayload?.center_lat != null && forestPayload?.center_lon != null) {
      return [forestPayload.center_lat, forestPayload.center_lon];
    }
    const r = regions.find((x) => x.slug === slug);
    if (r?.center_lat != null && r?.center_lon != null) {
      return [r.center_lat, r.center_lon];
    }
    return [17.385, 78.4867];
  }, [forestPayload, regions, slug]);

  async function runAnalyze() {
    setLoadingAnalyze(true);
    setErr("");
    setVerifyMsg("");
    setAnalysis(null);
    try {
      const q = new URLSearchParams({
        period1_start: p1s,
        period1_end: p1e,
      });
      const data = await apiGet(`/analyze/${encodeURIComponent(slug)}?${q.toString()}`);
      setAnalysis(data);
    } catch (e) {
      setErr(e.message || String(e));
    } finally {
      setLoadingAnalyze(false);
    }
  }

  async function runVerify(decision) {
    if (!analysis?.analysis_id) {
      setErr("Run analysis first.");
      return;
    }
    if (!adminName.trim()) {
      setErr("Enter your name/ID before verifying.");
      return;
    }
    localStorage.setItem("ecoguard_admin_name", adminName.trim());
    setLoadingVerify(true);
    setVerifyMsg("");
    try {
      const res = await apiPost("/verify", {
        analysis_id: analysis.analysis_id,
        decision,
        admin_id: adminName.trim(),
        admin_name: adminName.trim(),
      });
      if (res.alerts_sent) {
        const sd = res.alerts_summary?.sms_delivery;
        if (sd === "twilio_live") {
          setVerifyMsg(`Marked ILLEGAL by ${res.admin_name} — SMS sent via Twilio.`);
        } else if (sd === "simulated_log_only") {
          setVerifyMsg(`Marked ILLEGAL by ${res.admin_name} — SMS console-only (SIMULATE_SMS=true).`);
        } else {
          setVerifyMsg(`Marked ILLEGAL by ${res.admin_name} — SMS skipped (Twilio disabled).`);
        }
      } else {
        setVerifyMsg(`Marked LEGAL by ${res.admin_name} — no alerts sent.`);
      }
    } catch (e) {
      setErr(e.message || String(e));
    } finally {
      setLoadingVerify(false);
    }
  }

  const gj = analysis?.affected_geojson;
  const beforeFallbackUrl = analysis
    ? buildFallbackPreviewUrl(
        `Before preview — ${analysis.region_name || analysis.region_slug || "Region"}`,
        `${analysis.period1?.start || ""} to ${analysis.period1?.end || ""}`,
        "before",
      )
    : "";
  const afterFallbackUrl = analysis
    ? buildFallbackPreviewUrl(
        `After preview — ${analysis.region_name || analysis.region_slug || "Region"}`,
        `${analysis.period2?.start || ""} to ${analysis.period2?.end || ""}`,
        "after",
      )
    : "";
  const beforeImageUrl = analysis
    ? resolveImageUrl(analysis.period_images?.before_url || beforeFallbackUrl)
    : "";
  const afterImageUrl = analysis
    ? resolveImageUrl(analysis.period_images?.after_url || afterFallbackUrl)
    : "";

  return (
    <div className="layout">
      <aside className="sidebar">
        <h1 className="brand">Eco-Guard Telangana</h1>
        <p className="sub">Admin · Telangana forest monitoring (satellite)</p>

        <div>
          <label htmlFor="region">Region</label>
          {loadingRegions && <div className="loading">Loading regions…</div>}
          <select
            id="region"
            value={slug}
            onChange={(e) => setSlug(e.target.value)}
            disabled={!regions.length}
          >
            {regions.map((r) => (
              <option key={r.slug} value={r.slug}>
                {r.name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label>Forests in region</label>
          {loadingForests && <div className="loading">Loading forests…</div>}
          {!loadingForests && forestPayload?.forests && (
            <ul className="forest-list">
              {forestPayload.forests.map((f) => (
                <li key={f}>{f}</li>
              ))}
            </ul>
          )}
        </div>

        <div>
          <label>
            Analysis window (max 3 days inclusive). A matching comparison window is chosen automatically
            after this range.
          </label>
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
        </div>

        <button
          type="button"
          className="btn-primary"
          onClick={runAnalyze}
          disabled={loadingAnalyze || !slug}
        >
          {loadingAnalyze ? "Analyzing…" : "Run analysis"}
        </button>

        {err && <p className="error">{err}</p>}

        <div className="panel" style={{ marginTop: "0.25rem" }}>
          <div style={{ fontSize: "0.8rem", opacity: 0.85 }}>Admin verification</div>
          <p style={{ fontSize: "0.78rem", opacity: 0.75, margin: "0.35rem 0" }}>
            Alerts run only if you mark <strong>Illegal</strong> (set <code>SIMULATE_SMS=false</code> for real
            Twilio SMS).
          </p>
          <label htmlFor="admin-name">Your name / ID (recorded with this decision)</label>
          <input
            id="admin-name"
            type="text"
            placeholder="e.g. Pravalika"
            value={adminName}
            onChange={(e) => setAdminName(e.target.value)}
            style={{ marginBottom: "0.5rem" }}
          />
          <div className="btn-row">
            <button
              type="button"
              className="btn-legal"
              disabled={!analysis?.analysis_id || loadingVerify}
              onClick={() => runVerify("legal")}
            >
              {loadingVerify ? "…" : "Legal"}
            </button>
            <button
              type="button"
              className="btn-illegal"
              disabled={!analysis?.analysis_id || loadingVerify}
              onClick={() => runVerify("illegal")}
            >
              {loadingVerify ? "…" : "Illegal"}
            </button>
          </div>
          {verifyMsg && (
            <p style={{ fontSize: "0.8rem", marginTop: "0.5rem", lineHeight: 1.35 }}>{verifyMsg}</p>
          )}
        </div>
      </aside>

      <main className="main">
        <div className="panel">
          <strong>Results</strong>
          {analysis && (
            <div style={{ marginTop: "0.5rem", lineHeight: 1.5, fontSize: "0.9rem" }}>
              <div>
                Status:{" "}
                <span className={`status-pill ${statusClass(analysis.status)}`}>
                  {analysis.status}
                </span>
              </div>
              <div>Forest loss %: {analysis.loss_percent}</div>
              {analysis.period1 && analysis.period2 && (
                <div style={{ fontSize: "0.82rem", opacity: 0.9 }}>
                  Windows: {analysis.period1.start} → {analysis.period1.end} (baseline), then{" "}
                  {analysis.period2.start} → {analysis.period2.end} (auto comparison). Image cards use
                  selected start/end dates from period 1.
                </div>
              )}
              <div>
                NDVI change (forest mean): {analysis.ndvi_change_forest} (threshold{" "}
                {analysis.ndvi_loss_threshold_used})
              </div>
              <div>Simulated / fallback GEE: {String(analysis.simulated)}</div>
              {analysis.gee_composite_note && (
                <div style={{ opacity: 0.88, marginTop: "0.35rem", fontSize: "0.82rem" }}>
                  GEE: {analysis.gee_composite_note}
                </div>
              )}
              {analysis.error && (
                <div style={{ opacity: 0.85, marginTop: "0.35rem" }}>
                  Note: {analysis.error}
                </div>
              )}
            </div>
          )}
          {!analysis && <p style={{ opacity: 0.75 }}>Run analysis to see NDVI loss and status.</p>}
        </div>

        <div className="row-2">
          <div className="panel map-wrap">
            <MapContainer
              center={mapCenter}
              zoom={8}
              style={{ height: "100%", width: "100%" }}
              scrollWheelZoom
            >
              <FlyToRegion lat={mapCenter[0]} lon={mapCenter[1]} zoom={9} />
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              {gj && gj.features?.length > 0 && (
                <GeoJSON
                  data={gj}
                  style={() => ({
                    color: "#ff7043",
                    weight: 2,
                    fillOpacity: 0.25,
                  })}
                />
              )}
            </MapContainer>
          </div>
          <div className="panel image-wrap">
            {analysis ? (
              <div className="compare-grid">
                <div className="compare-card">
                  <div className="compare-title">Start date ({analysis.period1?.start})</div>
                  {!periodImgErr.before ? (
                    <img
                      className="compare-image"
                      src={beforeImageUrl}
                      alt={`Start date image ${analysis.period1?.start}`}
                      onError={(e) => {
                        if (!e.currentTarget.dataset.fallbackApplied) {
                          e.currentTarget.dataset.fallbackApplied = "1";
                          e.currentTarget.src = resolveImageUrl(beforeFallbackUrl);
                          return;
                        }
                        setPeriodImgErr((p) => ({ ...p, before: true }));
                      }}
                    />
                  ) : (
                    <div className="image-fallback">
                      Before image failed to load (blocked URL or network). Simulated run uses inline preview.
                    </div>
                  )}
                </div>
                <div className="compare-card">
                  <div className="compare-title">End date ({analysis.period1?.end})</div>
                  {!periodImgErr.after ? (
                    <img
                      className="compare-image"
                      src={afterImageUrl}
                      alt={`End date image ${analysis.period1?.end}`}
                      onError={(e) => {
                        if (!e.currentTarget.dataset.fallbackApplied) {
                          e.currentTarget.dataset.fallbackApplied = "1";
                          e.currentTarget.src = resolveImageUrl(afterFallbackUrl);
                          return;
                        }
                        setPeriodImgErr((p) => ({ ...p, after: true }));
                      }}
                    />
                  ) : (
                    <div className="image-fallback">
                      After image failed to load. If GEE: thumb URLs expire; use simulated previews or re-run analysis.
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div style={{ opacity: 0.7, padding: "1rem" }}>
                Before/after images appear after analysis.
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}