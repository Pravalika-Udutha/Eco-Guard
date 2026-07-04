"""
Eco-Guard Telangana Flask API.

Forest:  GET /regions, /forests/<region>, /analyze/<region>, POST /verify
Water:   GET /water-bodies, /analyze-water/<slug>, POST /verify-water
Auth:    POST /auth/register, /auth/login, /auth/logout, GET /auth/me
History: GET /my-alerts
Admin:   GET /verifications, /contacts/<region>
"""

from __future__ import annotations

import logging

from flask import Blueprint, Response, g, jsonify, request

from app.analysis_store import get_analysis, save_analysis
from app.alerts_service import send_illegal_alerts
from app.auth import require_admin, require_user
from app.auth_users import login_user, logout_user, register_user
from app.db_contacts import list_contacts_for_region
from app.gee_ndvi import run_gee_analysis
from app.gee_ndwi import run_water_analysis
from app.period_placeholder import render_svg
from app.regions_data import get_region_by_slug, list_regions_summary, point_inside_telangana
from app.utils_ndvi import derive_period2_following, validate_period_one
from app.verification_log import list_verifications, record_verification
from app.water_bodies_data import get_water_body_by_slug, list_water_bodies_summary

logger = logging.getLogger(__name__)

bp = Blueprint("api", __name__)


# =============================
# Auth
# =============================

@bp.post("/auth/register")
def auth_register():
    data = request.get_json(silent=True) or {}
    result = register_user(data.get("username", ""), data.get("password", ""))
    if not result.get("ok"):
        return jsonify({"error": result.get("error", "Registration failed")}), 400
    return jsonify(result)


@bp.post("/auth/login")
def auth_login():
    data = request.get_json(silent=True) or {}
    result = login_user(data.get("username", ""), data.get("password", ""))
    if not result.get("ok"):
        return jsonify({"error": result.get("error", "Login failed")}), 401
    return jsonify(result)


@bp.post("/auth/logout")
@require_user
def auth_logout():
    auth_header = request.headers.get("Authorization", "")
    token = auth_header[7:].strip() if auth_header.startswith("Bearer ") else ""
    logout_user(token)
    return jsonify({"ok": True})


@bp.get("/auth/me")
@require_user
def auth_me():
    return jsonify({"user": g.current_user})


@bp.get("/public/period-preview.svg")
def period_preview_svg():
    t1 = (request.args.get("t1") or "Before")[:200]
    t2 = (request.args.get("t2") or "")[:200]
    v = (request.args.get("v") or "before").lower()[:20]
    if v not in ("before", "after", "error"):
        v = "before"
    svg = render_svg(t1, t2, v)
    resp = Response(svg, mimetype="image/svg+xml")
    resp.headers["Cache-Control"] = "public, max-age=120"
    return resp


# =============================
# Forest tool — logged-in users only
# =============================

@bp.get("/regions")
@require_user
def get_regions():
    return jsonify({"regions": list_regions_summary()})


@bp.get("/forests/<region>")
@require_user
def get_forests(region: str):
    r = get_region_by_slug(region)
    if not r:
        return jsonify({"error": "Region not found", "slug": region}), 404
    return jsonify({"region": r["slug"], "name": r["name"], "center_lat": r["center_lat"], "center_lon": r["center_lon"], "forests": r["forests"]})


@bp.get("/analyze/<region>")
@require_user
def analyze(region: str):
    r = get_region_by_slug(region)
    if not r:
        return jsonify({"error": "Region not found", "slug": region}), 404
    lat, lon = r["center_lat"], r["center_lon"]
    if not point_inside_telangana(lat, lon):
        return jsonify({"error": "Region center outside Telangana bounds"}), 400
    p1s, p1e = request.args.get("period1_start"), request.args.get("period1_end")
    if not p1s or not p1e:
        return jsonify({"error": "Missing date parameters", "required": ["period1_start", "period1_end"]}), 400
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
@require_user
def verify():
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
    username = g.current_user["username"]
    log_result = record_verification(
        analysis_id=aid, domain="forest", region_slug=rec.get("region_slug", ""), decision=decision,
        admin_id=username, admin_name=username, loss_percent=rec.get("loss_percent"), status=rec.get("status"),
    )
    alerts_summary = None
    if decision == "illegal":
        try:
            alerts_summary = send_illegal_alerts(rec)
        except Exception as exc:
            logger.exception("send_illegal_alerts failed")
            return jsonify({"error": "Alerts could not be sent", "detail": str(exc)}), 503
    return jsonify({
        "ok": True, "analysis_id": aid, "decision": decision, "admin_id": username, "admin_name": username,
        "alerts_sent": decision == "illegal", "alerts_summary": alerts_summary, "logged": log_result.get("ok", False),
    })


# =============================
# Water tool — logged-in users only
# =============================

@bp.get("/water-bodies")
@require_user
def get_water_bodies():
    return jsonify({"water_bodies": list_water_bodies_summary()})


@bp.get("/analyze-water/<slug>")
@require_user
def analyze_water(slug: str):
    body = get_water_body_by_slug(slug)
    if not body:
        return jsonify({"error": "Water body not found", "slug": slug}), 404
    p1s, p1e = request.args.get("period1_start"), request.args.get("period1_end")
    if not p1s or not p1e:
        return jsonify({"error": "Missing date parameters", "required": ["period1_start", "period1_end"]}), 400
    try:
        d1, e1 = validate_period_one(p1s, p1e)
        d2, e2 = derive_period2_following(d1, e1)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    try:
        result = run_water_analysis(slug, d1, e1, d2, e2)
    except Exception as exc:
        logger.exception("Water analysis failed")
        return jsonify({"error": "Analysis failed", "detail": str(exc)}), 500
    if result.get("error") and not result.get("water_name"):
        return jsonify(result), 400
    aid = save_analysis(result)
    result["analysis_id"] = aid
    return jsonify(result)


@bp.post("/verify-water")
@require_user
def verify_water():
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
    username = g.current_user["username"]
    log_result = record_verification(
        analysis_id=aid, domain="water", region_slug=rec.get("water_slug", ""), decision=decision,
        admin_id=username, admin_name=username, loss_percent=rec.get("water_shrink_percent"), status=rec.get("status"),
    )
    alerts_summary = None
    if decision == "illegal":
        # Reuse the forest alert templater — remap water-specific keys to the generic names it expects.
        rec_for_alert = dict(rec)
        rec_for_alert["region_slug"] = rec.get("water_slug", "")
        rec_for_alert["region_name"] = rec.get("water_name", "")
        rec_for_alert["loss_percent"] = rec.get("water_shrink_percent")
        try:
            alerts_summary = send_illegal_alerts(rec_for_alert)
        except Exception as exc:
            logger.exception("send_illegal_alerts failed (water)")
            return jsonify({"error": "Alerts could not be sent", "detail": str(exc)}), 503
    return jsonify({
        "ok": True, "analysis_id": aid, "decision": decision, "admin_id": username, "admin_name": username,
        "alerts_sent": decision == "illegal", "alerts_summary": alerts_summary, "logged": log_result.get("ok", False),
    })


# =============================
# History
# =============================

@bp.get("/my-alerts")
@require_user
def my_alerts():
    username = g.current_user["username"]
    all_records = list_verifications(limit=500)
    mine = [v for v in all_records if v.get("admin_id") == username]
    return jsonify({"alerts": mine})


# =============================
# Admin-only oversight
# =============================

@bp.get("/verifications")
@require_admin
def verifications():
    region = request.args.get("region")
    domain = request.args.get("domain")
    return jsonify({"verifications": list_verifications(region_slug=region, domain=domain)})


@bp.get("/contacts/<region>")
@require_admin
def contacts(region: str):
    r = get_region_by_slug(region)
    if not r:
        return jsonify({"error": "Region not found"}), 404
    return jsonify({"region": region, "contacts": list_contacts_for_region(region)})