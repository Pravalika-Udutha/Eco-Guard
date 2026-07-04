"""
Google Earth Engine: Sentinel-2 NDWI water-body analysis for a Telangana lake/reservoir.

NDWI (McFeeters) = (Green - NIR) / (Green + NIR), using Sentinel-2 bands B3 (green) and B8 (NIR).
Water pixels have NDWI > ~0.1-0.3; a drop in NDWI over time within the water body's footprint
indicates shrinking water spread (drought, encroachment, illegal draining).

Falls back to deterministic simulation when GEE is disabled or errors occur — same pattern as gee_ndvi.py.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import ee

from app.config import Config
from app.period_placeholder import build_placeholder_url
from app.utils_ndvi import classify_status, geojson_empty_feature_collection
from app.water_bodies_data import get_water_body_by_slug

logger = logging.getLogger(__name__)

WATER_NDWI_MIN = 0.05          # baseline NDWI threshold to classify a pixel as "water"
NDWI_DROP_THRESHOLD = -0.15    # NDWI drop beyond this = water loss / shrinkage

_ee_ready = False


def _ensure_ee() -> None:
    global _ee_ready
    if _ee_ready:
        return
    if not Config.GEE_ENABLED:
        raise RuntimeError("GEE disabled")
    if not Config.GEE_PROJECT:
        raise RuntimeError("GEE_PROJECT not set")
    cred_path = Config.GEE_CREDENTIALS_JSON
    try:
        if cred_path:
            p = Path(cred_path)
            sa = json.loads(p.read_text(encoding="utf-8"))
            creds = ee.ServiceAccountCredentials(sa["client_email"], str(p))
            ee.Initialize(creds, project=Config.GEE_PROJECT)
        else:
            ee.Initialize(project=Config.GEE_PROJECT)
        _ee_ready = True
        logger.info("Earth Engine initialized for %s (water module)", Config.GEE_PROJECT)
    except Exception:
        logger.exception("Earth Engine init failed (water module)")
        raise


def _ndwi_thumb_url(image: ee.Image, aoi: ee.Geometry) -> str | None:
    try:
        return image.getThumbURL(
            {
                "region": aoi,
                "dimensions": 768,
                "format": "png",
                "min": -0.3,
                "max": 0.5,
                "palette": ["8b5e34", "d9b44a", "e8f0d0", "8ecae6", "219ebc", "023047"],
            }
        )
    except Exception:
        logger.exception("Failed to generate NDWI thumbnail URL")
        return None


def _s2_median_composite(coll_id: str, aoi: ee.Geometry, d_start: date, d_end: date) -> tuple[ee.Image, dict[str, Any]]:
    meta: dict[str, Any] = {
        "requested_start": d_start.isoformat(),
        "requested_end": d_end.isoformat(),
        "used_start": d_start.isoformat(),
        "used_end": d_end.isoformat(),
        "s2_scene_count": 0,
    }
    strategies: list[tuple[int, int, int | None]] = [
        (0, 0, 85), (0, 90, 85), (45, 90, 85), (60, 120, 90),
        (90, 150, 95), (120, 180, None), (180, 365, None), (365, 730, None),
    ]
    for back_d, fwd_d, cloud_max in strategies:
        s_date = d_start - timedelta(days=back_d)
        e_date = d_end + timedelta(days=fwd_d)
        if e_date <= s_date:
            e_date = s_date + timedelta(days=1)
        s, e = s_date.isoformat(), e_date.isoformat()
        coll = ee.ImageCollection(coll_id).filterBounds(aoi).filterDate(s, e).select(["B3", "B8"])
        if cloud_max is not None:
            coll = coll.filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", cloud_max))
        try:
            n = int(coll.size().getInfo() or 0)
        except Exception:
            logger.debug("S2 size check failed for %s–%s (will try wider window)", s, e)
            n = 0
        if n > 0:
            meta["used_start"], meta["used_end"], meta["s2_scene_count"] = s, e, n
            if s != d_start.isoformat() or e != d_end.isoformat():
                meta["window_expanded"] = True
            return coll.median(), meta
    raise ValueError("No Sentinel-2 (B3/B8) scenes for this AOI after expanding date windows.")


def run_water_analysis(water_slug: str, d1: date, e1: date, d2: date, e2: date) -> dict[str, Any]:
    body = get_water_body_by_slug(water_slug)
    if not body:
        return _error_payload("Water body not found", water_slug)

    try:
        _ensure_ee()
    except Exception as exc:
        logger.warning("GEE unavailable for water analysis (%s); using simulation", exc)
        return _simulated_analysis(body, d1, e1, str(exc))

    try:
        aoi = ee.Geometry(body["geojson"])
        coll_id = Config.GEE_S2_COLLECTION

        im1, meta1 = _s2_median_composite(coll_id, aoi, d1, e1)
        im2, meta2 = _s2_median_composite(coll_id, aoi, d2, e2)

        ndwi1 = im1.normalizedDifference(["B3", "B8"]).rename("ndwi")
        ndwi2 = im2.normalizedDifference(["B3", "B8"]).rename("ndwi")

        before_img = _ndwi_thumb_url(ndwi1, aoi) or build_placeholder_url(f"Start (GEE) — {body['name']}", d1.isoformat(), "before")
        after_img = _ndwi_thumb_url(ndwi2, aoi) or build_placeholder_url(f"End (GEE) — {body['name']}", e2.isoformat(), "after")

        water_mask = ndwi1.gt(WATER_NDWI_MIN).rename("water")
        delta = ndwi2.subtract(ndwi1).rename("delta")
        loss_mask = delta.lt(NDWI_DROP_THRESHOLD).multiply(water_mask).rename("loss")

        water_px = water_mask.reduceRegion(reducer=ee.Reducer.sum(), geometry=aoi, scale=20, maxPixels=1e13, tileScale=2)
        loss_px = loss_mask.reduceRegion(reducer=ee.Reducer.sum(), geometry=aoi, scale=20, maxPixels=1e13, tileScale=2)
        wsum = float((water_px.getInfo() or {}).get("water", 0) or 0)
        lsum = float((loss_px.getInfo() or {}).get("loss", 0) or 0)
        shrink_pct = (lsum / wsum * 100.0) if wsum > 0 else 0.0

        n1 = float((ndwi1.updateMask(water_mask).reduceRegion(reducer=ee.Reducer.mean(), geometry=aoi, scale=20, maxPixels=1e13, tileScale=2).getInfo() or {}).get("ndwi", 0) or 0)
        n2 = float((ndwi2.updateMask(water_mask).reduceRegion(reducer=ee.Reducer.mean(), geometry=aoi, scale=20, maxPixels=1e13, tileScale=2).getInfo() or {}).get("ndwi", 0) or 0)

        vectors = loss_mask.selfMask().reduceToVectors(geometry=aoi, scale=20, maxPixels=1e9, tileScale=2)
        gj = vectors.getInfo() or {}
        fc = {"type": "FeatureCollection", "features": (gj.get("features") or [])[:200]} if gj.get("type") == "FeatureCollection" else geojson_empty_feature_collection()

        status = classify_status(shrink_pct)

        return {
            "water_slug": water_slug,
            "water_name": body["name"],
            "description": body["description"],
            "period1": {"start": d1.isoformat(), "end": e1.isoformat()},
            "period2": {"start": d2.isoformat(), "end": e2.isoformat(), "derived_from_period1": True},
            "ndwi_mean_period1_water": round(n1, 4),
            "ndwi_mean_period2_water": round(n2, 4),
            "ndwi_change_water": round(n2 - n1, 4),
            "ndwi_drop_threshold_used": NDWI_DROP_THRESHOLD,
            "water_shrink_percent": round(shrink_pct, 2),
            "status": status,
            "affected_geojson": fc,
            "period_images": {"before_url": before_img, "after_url": after_img},
            "simulated": False,
            "error": None,
        }
    except Exception as exc:
        logger.exception("GEE water analysis failed")
        return _simulated_analysis(body, d1, e1, str(exc))


def _error_payload(msg: str, slug: str) -> dict[str, Any]:
    return {
        "water_slug": slug, "error": msg, "simulated": True,
        "affected_geojson": geojson_empty_feature_collection(),
        "water_shrink_percent": 0.0, "status": "Normal",
        "period_images": {
            "before_url": build_placeholder_url("Before", msg[:120], "error"),
            "after_url": build_placeholder_url("After", "No analysis", "error"),
        },
    }


def _simulated_analysis(body: dict, d1: date, e1: date, reason: str) -> dict[str, Any]:
    key = f"{body['slug']}|{d1}|{e1}"
    h = hashlib.sha256(key.encode()).hexdigest()
    shrink_pct = (int(h[:4], 16) % 15000) / 1000.0
    n1 = 0.25 + (int(h[4:8], 16) % 400) / 10000.0
    n2 = n1 - (shrink_pct / 250.0)
    status = classify_status(shrink_pct)
    lon, lat = body["center_lon"], body["center_lat"]
    d = 0.03
    fc = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {"simulated": True, "note": "Simulated water-loss fragment"},
            "geometry": {"type": "Polygon", "coordinates": [[[lon - d, lat - d], [lon + d, lat - d], [lon + d, lat + d], [lon - d, lat + d], [lon - d, lat - d]]]},
        }],
    }
    p1s, p1e = d1.isoformat(), e1.isoformat()
    return {
        "water_slug": body["slug"], "water_name": body["name"], "description": body["description"],
        "period1": {"start": p1s, "end": p1e},
        "period2": {"start": p1e, "end": p1e, "derived_from_period1": True},
        "ndwi_mean_period1_water": round(n1, 4),
        "ndwi_mean_period2_water": round(n2, 4),
        "ndwi_change_water": round(n2 - n1, 4),
        "ndwi_drop_threshold_used": NDWI_DROP_THRESHOLD,
        "water_shrink_percent": round(shrink_pct, 2),
        "status": status,
        "affected_geojson": fc,
        "period_images": {
            "before_url": build_placeholder_url(f"Start (simulated) — {body['name']}", p1s, "before"),
            "after_url": build_placeholder_url(f"End (simulated) — {body['name']}", p1e, "after"),
        },
        "simulated": True,
        "error": reason,
    }