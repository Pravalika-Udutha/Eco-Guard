"""
Google Earth Engine: Sentinel-2 NDVI forest analysis for a Telangana region.

Computes median NDVI for two short windows, masks forest (NDVI > 0.5 on baseline),
flags loss where NDVI drop exceeds seasonal threshold, and returns loss % plus
GeoJSON of affected vectors (simplified).

Falls back to deterministic simulation when GEE is disabled or errors occur.
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
from app.regions_data import get_region_by_slug
from app.utils_ndvi import (
    classify_status,
    geojson_empty_feature_collection,
    ndvi_drop_threshold_for_dates,
)

logger = logging.getLogger(__name__)

_ee_ready = False


def _ndvi_thumb_url(image: ee.Image, aoi: ee.Geometry) -> str | None:
    """Build a preview URL for NDVI image over the region."""
    try:
        return image.getThumbURL(
            {
                "region": aoi,
                "dimensions": 768,
                "format": "png",
                "min": 0,
                "max": 1,
                "palette": [
                    "8b0000",
                    "d73027",
                    "fdae61",
                    "fee08b",
                    "d9ef8b",
                    "66bd63",
                    "1a9850",
                    "006400",
                ],
            }
        )
    except Exception:
        logger.exception("Failed to generate NDVI thumbnail URL")
        return None


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
        logger.info("Earth Engine initialized for %s", Config.GEE_PROJECT)
    except Exception:
        logger.exception("Earth Engine init failed")
        raise


def _region_geometry(region: dict) -> ee.Geometry:
    gj = region["geojson"]
    return ee.Geometry(gj)


def _s2_median_composite(
    coll_id: str,
    aoi: ee.Geometry,
    d_start: date,
    d_end: date,
) -> tuple[ee.Image, dict[str, Any]]:
    """
    Median SR composite for [d_start, d_end]. Short windows often have zero clear S2 scenes
    (empty composite -> no B8/B4). We widen the filter window and relax cloud cap until scenes exist.
    """
    meta: dict[str, Any] = {
        "requested_start": d_start.isoformat(),
        "requested_end": d_end.isoformat(),
        "used_start": d_start.isoformat(),
        "used_end": d_end.isoformat(),
        "s2_scene_count": 0,
        "cloud_filter_max_pct": 85,
    }

    strategies: list[tuple[int, int, int | None]] = [
        (0, 0, 85),
        (0, 90, 85),
        (45, 90, 85),
        (60, 120, 90),
        (90, 150, 95),
        (120, 180, None),
        (180, 365, None),
        (365, 730, None),
    ]

    for back_d, fwd_d, cloud_max in strategies:
        s_date = d_start - timedelta(days=back_d)
        e_date = d_end + timedelta(days=fwd_d)
        if e_date <= s_date:
            # Earth Engine rejects zero-width date ranges outright; widen by 1 day.
            e_date = s_date + timedelta(days=1)
        s = s_date.isoformat()
        e = e_date.isoformat()
        coll = ee.ImageCollection(coll_id).filterBounds(aoi).filterDate(s, e).select(["B8", "B4"])
        if cloud_max is not None:
            coll = coll.filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", cloud_max))
        try:
            n = int(coll.size().getInfo() or 0)
        except Exception:
            logger.debug("S2 size check failed for %s–%s (will try wider window)", s, e)
            n = 0
        if n > 0:
            meta["used_start"] = s
            meta["used_end"] = e
            meta["s2_scene_count"] = n
            meta["cloud_filter_max_pct"] = cloud_max if cloud_max is not None else -1
            if s != d_start.isoformat() or e != d_end.isoformat():
                meta["window_expanded"] = True
            return coll.median(), meta

    raise ValueError(
        "No Sentinel-2 (B8/B4) scenes for this AOI after expanding date windows. "
        "Check GEE_PROJECT / collection access or pick a different season."
    )


def run_gee_analysis(
    region_slug: str,
    d1: date,
    e1: date,
    d2: date,
    e2: date,
) -> dict[str, Any]:
    """
    Returns analysis dict: loss_pct, geojson (FeatureCollection), ndvi stats,
    threshold used, forests list, simulated flag, error optional.
    """
    region = get_region_by_slug(region_slug)
    if not region:
        return _error_payload("Region not found", region_slug)

    threshold = ndvi_drop_threshold_for_dates(d1, e1, d2, e2)
    forest_min = Config.FOREST_NDVI_MIN

    try:
        _ensure_ee()
    except Exception as exc:
        logger.warning("GEE unavailable (%s); using simulation", exc)
        return _simulated_analysis(region, d1, e1, d2, e2, threshold, forest_min, str(exc))

    try:
        aoi = _region_geometry(region)
        coll_id = Config.GEE_S2_COLLECTION

        p1_start, p1_end = d1.isoformat(), e1.isoformat()
        p2_start, p2_end = d2.isoformat(), e2.isoformat()

        im1, meta1 = _s2_median_composite(coll_id, aoi, d1, e1)
        im2, meta2 = _s2_median_composite(coll_id, aoi, d2, e2)

        ndvi1 = im1.normalizedDifference(["B8", "B4"]).rename("ndvi")
        ndvi2 = im2.normalizedDifference(["B8", "B4"]).rename("ndvi")

        im_start, _ = _s2_median_composite(coll_id, aoi, d1, d1)
        im_end, _ = _s2_median_composite(coll_id, aoi, e1, e1)
        ndvi_start = im_start.normalizedDifference(["B8", "B4"]).rename("ndvi")
        ndvi_end = im_end.normalizedDifference(["B8", "B4"]).rename("ndvi")
        before_img = _ndvi_thumb_url(ndvi_start, aoi)
        after_img = _ndvi_thumb_url(ndvi_end, aoi)
        if not before_img:
            before_img = build_placeholder_url(
                "Start date (GEE)", p1_start, "before"
            )
        if not after_img:
            after_img = build_placeholder_url(
                "End date (GEE)", p1_end, "after"
            )

        forest = ndvi1.gt(forest_min).rename("forest")
        delta = ndvi2.subtract(ndvi1).rename("delta")
        loss_mask = delta.lt(threshold).multiply(forest).rename("loss")

        forest_px = forest.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=aoi,
            scale=30,
            maxPixels=1e13,
            tileScale=2,
        )
        loss_px = loss_mask.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=aoi,
            scale=30,
            maxPixels=1e13,
            tileScale=2,
        )
        fpi = forest_px.getInfo() or {}
        lpi = loss_px.getInfo() or {}
        fsum = float(fpi.get("forest", 0) or 0)
        lsum = float(lpi.get("loss", 0) or 0)
        loss_pct = (lsum / fsum * 100.0) if fsum > 0 else 0.0

        ndvi_mean = ndvi1.updateMask(forest).reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=aoi,
            scale=30,
            maxPixels=1e13,
            tileScale=2,
        )
        ndvi_mean2 = ndvi2.updateMask(forest).reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=aoi,
            scale=30,
            maxPixels=1e13,
            tileScale=2,
        )
        n1 = float((ndvi_mean.getInfo() or {}).get("ndvi", 0) or 0)
        n2 = float((ndvi_mean2.getInfo() or {}).get("ndvi", 0) or 0)

        vectors = loss_mask.selfMask().reduceToVectors(
            geometry=aoi,
            scale=30,
            maxPixels=1e9,
            tileScale=2,
        )
        gj = vectors.getInfo() or {}
        if gj.get("type") != "FeatureCollection":
            fc = geojson_empty_feature_collection()
        else:
            feats = gj.get("features") or []
            fc = {"type": "FeatureCollection", "features": feats[:200]}

        status = classify_status(loss_pct)

        gee_note_parts: list[str] = []
        if meta1.get("window_expanded"):
            gee_note_parts.append(
                f"Before: S2 composite window {meta1.get('used_start')} to {meta1.get('used_end')} "
                f"({meta1.get('s2_scene_count')} scenes); chart labels still show your period 1."
            )
        if meta2.get("window_expanded"):
            gee_note_parts.append(
                f"After: S2 composite window {meta2.get('used_start')} to {meta2.get('used_end')} "
                f"({meta2.get('s2_scene_count')} scenes); chart labels still show your period 2."
            )
        gee_composite_note = "; ".join(gee_note_parts) if gee_note_parts else None

        return {
            "region_slug": region_slug,
            "region_name": region["name"],
            "forests": region["forests"],
            "period1": {"start": p1_start, "end": p1_end},
            "period2": {
                "start": p2_start,
                "end": p2_end,
                "derived_from_period1": True,
            },
            "gee_composite": {"period1": meta1, "period2": meta2},
            "ndvi_mean_period1_forest": round(n1, 4),
            "ndvi_mean_period2_forest": round(n2, 4),
            "ndvi_change_forest": round(n2 - n1, 4),
            "ndvi_loss_threshold_used": threshold,
            "forest_mask_ndvi_min": forest_min,
            "loss_percent": round(loss_pct, 2),
            "status": status,
            "affected_geojson": fc,
            "period_images": {
                "before_url": before_img,
                "after_url": after_img,
            },
            "simulated": False,
            "error": None,
            "gee_composite_note": gee_composite_note,
        }
    except Exception as exc:
        logger.exception("GEE analysis failed")
        return _simulated_analysis(region, d1, e1, d2, e2, threshold, forest_min, str(exc))


def _error_payload(msg: str, slug: str) -> dict[str, Any]:
    return {
        "region_slug": slug,
        "error": msg,
        "simulated": True,
        "affected_geojson": geojson_empty_feature_collection(),
        "loss_percent": 0.0,
        "status": "Normal",
        "period_images": {
            "before_url": build_placeholder_url("Before", msg[:120], "error"),
            "after_url": build_placeholder_url("After", "No analysis", "error"),
        },
    }


def _simulated_analysis(
    region: dict,
    d1: date,
    e1: date,
    d2: date,
    e2: date,
    threshold: float,
    forest_min: float,
    reason: str,
) -> dict[str, Any]:
    """Deterministic pseudo-metrics from dates + slug (for demo without GEE)."""
    key = f"{region['slug']}|{d1}|{e1}|{d2}|{e2}"
    h = hashlib.sha256(key.encode()).hexdigest()
    loss_pct = (int(h[:4], 16) % 18000) / 1000.0
    n1 = 0.55 + (int(h[4:8], 16) % 500) / 10000.0
    n2 = n1 - (loss_pct / 200.0)
    status = classify_status(loss_pct)
    lon, lat = region["center_lon"], region["center_lat"]
    d = 0.06
    fc = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"simulated": True, "note": "Simulated AOI fragment"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [lon - d, lat - d],
                            [lon + d, lat - d],
                            [lon + d, lat + d],
                            [lon - d, lat + d],
                            [lon - d, lat - d],
                        ]
                    ],
                },
            }
        ],
    }
    p1s, p1e = d1.isoformat(), e1.isoformat()
    p2s, p2e = d2.isoformat(), e2.isoformat()
    return {
        "region_slug": region["slug"],
        "region_name": region["name"],
        "forests": region["forests"],
        "period1": {"start": p1s, "end": p1e},
        "period2": {
            "start": p2s,
            "end": p2e,
            "derived_from_period1": True,
        },
        "ndvi_mean_period1_forest": round(n1, 4),
        "ndvi_mean_period2_forest": round(n2, 4),
        "ndvi_change_forest": round(n2 - n1, 4),
        "ndvi_loss_threshold_used": threshold,
        "forest_mask_ndvi_min": forest_min,
        "loss_percent": round(loss_pct, 2),
        "status": status,
        "affected_geojson": fc,
        "period_images": {
            "before_url": build_placeholder_url(
                f"Start date (simulated) — {region['name']}", p1s, "before"
            ),
            "after_url": build_placeholder_url(
                f"End date (simulated) — {region['name']}", p1e, "after"
            ),
        },
        "simulated": True,
        "error": reason,
    }