"""
Eco-Guard Telangana Flask API.

Endpoints:
  GET  /regions
  GET  /forests/<region>
  GET  /analyze/<region>
  POST /verify
"""

from __future__ import annotations

import logging

from flask import Blueprint, Response, jsonify, request

from app.analysis_store import get_analysis, save_analysis
from app.alerts_service import send_illegal_alerts
from app.auth import require_admin
from app.db_contacts import list_contacts_for_region
from app.gee_ndvi import run_gee_analysis
from app.period_placeholder import render_svg
from app.regions_data import get_region_by_slug, list_regions_summary, point_inside_telangana
from app.utils_ndvi import derive_period2_following, validate_period_one

logger = logging.getLogger(__name__)

bp = Blueprint("api", __name__)


@bp.get("/public/period-preview.svg")
def period_preview_svg():
    """Public NDVI-style placeholder (no X-Admin-Token). Used as period_images URLs from the React UI."""
    t1 = (request.args.get("t1") or "Before")[:200]
    t2 = (request.args.get("t2") or "")[:200]
    v = (request.args.get("v") or "before").lower()[:20]
    if v not in ("before", "after", "error"):
        v = "before"
    svg = render_svg(t1, t2, v)
    resp = Response(svg, mimetype="image/svg+xml")
    resp.headers["Cache-Control"] = "public, max-age=120"
    return resp


@bp.get("/regions")
@require_admin
def get_regions():
    """List Telangana regions (dropdown data)."""
    return jsonify({"regions": list_regions_summary()})


@bp.get("/forests/<region>")
@require_admin
def get_forests(region: str):
    """Forests associated with a region slug."""
    r = get_region_by_slug(region)
    if not r:
        return jsonify({"error": "Region not found", "slug": region}), 404
    return jsonify(
        {
            "region": r["slug"],
            "name": r["name"],
            "center_lat": r["center_lat"],
            "center_lon": r["center_lon"],
            "forests": r["forests"],
        }
    )


@bp.get("/analyze/<region>")
@require_admin
def analyze(region: str):
    """
    Sentinel-2 NDVI analysis for a region.

    Query: period1_start, period1_end (YYYY-MM-DD). Period 1 length is capped by MAX_PERIOD_DAYS (default 3).
    Period 2 is computed automatically as the next contiguous window of the same length (not a query param).
    """
    r = get_region_by_slug(region)
    if not r:
        return jsonify({"error": "Region not found", "slug": region}), 404

    lat, lon = r["center_lat"], r["center_lon"]
    if not point_inside_telangana(lat, lon):
        return jsonify({"error": "Region center outside Telangana bounds"}), 400

    p1s = request.args.get("period1_start")
    p1e = request.args.get("period1_end")
    if not p1s or not p1e:
        return jsonify(
            {
                "error": "Missing date parameters",
                "required": ["period1_start", "period1_end"],
            }
        ), 400

    try:
        d1, e1 = validate_period_one(p1s, p1e)
        d2, e2 = derive_period2_following(d1, e1)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    try:
        result = run_gee_analysis(region, d1, e1, d2, e2)
    except Exception as exc:
        logger.exception("Analysis failed")
        return jsonify({"error": "Analysis failed", "detail": str(exc)}), 500

    if result.get("error") and not result.get("region_name"):
        return jsonify(result), 400

    aid = save_analysis(result)
    result["analysis_id"] = aid

    return jsonify(result)


@bp.post("/verify")
@require_admin
def verify():
    """
    Admin verification of analysis. Body JSON:
      { "analysis_id": "<uuid>", "decision": "legal" | "illegal" }

    Alerts (SMS / email) are sent only for illegal.
    """
    data = request.get_json(silent=True) or {}
    aid = (data.get("analysis_id") or "").strip()
    decision = (data.get("decision") or "").strip().lower()
    if not aid:
        return jsonify({"error": "analysis_id required"}), 400
    if decision not in ("legal", "illegal"):
        return jsonify({"error": 'decision must be "legal" or "illegal"'}), 400

    rec = get_analysis(aid)
    if not rec:
        return jsonify({"error": "Unknown analysis_id"}), 404

    rec = dict(rec)
    rec["analysis_id"] = aid
    rec["verification"] = decision

    alerts_summary = None
    if decision == "illegal":
        try:
            alerts_summary = send_illegal_alerts(rec)
        except Exception as exc:
            logger.exception("send_illegal_alerts failed")
            return (
                jsonify(
                    {
                        "error": "Alerts could not be sent",
                        "detail": str(exc),
                        "hint": "Set DATABASE_URL in repo-root .env (PostgreSQL) and restart Flask.",
                    }
                ),
                503,
            )

    return jsonify(
        {
            "ok": True,
            "analysis_id": aid,
            "decision": decision,
            "alerts_sent": decision == "illegal",
            "alerts_summary": alerts_summary,
        }
    )


@bp.get("/contacts/<region>")
@require_admin
def contacts(region: str):
    """Optional: list notification contacts for a region (admin transparency)."""
    r = get_region_by_slug(region)
    if not r:
        return jsonify({"error": "Region not found"}), 404
    return jsonify({"region": region, "contacts": list_contacts_for_region(region)})


# =============================
# Compatibility aliases: /api/*
# =============================
# The React dev setup typically uses Vite proxy (/api -> Flask :5000),
# but if VITE_API_URL is misconfigured, the browser may call /api/regions
# instead of /regions. These aliases prevent 404s by delegating to the existing handlers.

@bp.get("/api/regions")
def get_regions_api():
    return get_regions()


@bp.get("/api/forests/<region>")
def get_forests_api(region: str):
    return get_forests(region)


@bp.get("/api/analyze/<region>")
def analyze_api(region: str):
    return analyze(region)


@bp.post("/api/verify")
def verify_api():
    return verify()


@bp.get("/api/contacts/<region>")
def contacts_api(region: str):
    return contacts(region)


@bp.get("/api/public/period-preview.svg")
def period_preview_svg_api():
    return period_preview_svg()