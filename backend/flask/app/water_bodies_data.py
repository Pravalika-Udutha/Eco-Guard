"""
Predefined Telangana water bodies (lakes/reservoirs) for NDWI-based monitoring.

Coordinates are approximate centers; polygons are simple bounding boxes around
the water body sized to comfortably cover its water-spread area for GEE analysis.
"""

from __future__ import annotations

TELANGANA_BOUNDS = {
    "min_lat": 15.8,
    "max_lat": 19.9,
    "min_lon": 77.0,
    "max_lon": 81.5,
}


def _box(minx: float, miny: float, maxx: float, maxy: float) -> list[list[list[float]]]:
    return [[[minx, miny], [maxx, miny], [maxx, maxy], [minx, maxy], [minx, miny]]]


WATER_BODIES: list[dict] = [
    {
        "slug": "hussain-sagar",
        "name": "Hussain Sagar Lake",
        "center_lat": 17.4239,
        "center_lon": 78.4738,
        "geojson": {"type": "Polygon", "coordinates": _box(78.45, 17.41, 78.50, 17.44)},
        "description": "Iconic heart-shaped artificial lake in central Hyderabad, built 1562.",
    },
    {
        "slug": "osman-sagar",
        "name": "Osman Sagar (Gandipet)",
        "center_lat": 17.3833,
        "center_lon": 78.3167,
        "geojson": {"type": "Polygon", "coordinates": _box(78.28, 17.35, 78.36, 17.42)},
        "description": "Reservoir on the Musi River, a major drinking-water source for Hyderabad.",
    },
    {
        "slug": "himayat-sagar",
        "name": "Himayat Sagar",
        "center_lat": 17.3333,
        "center_lon": 78.3667,
        "geojson": {"type": "Polygon", "coordinates": _box(78.32, 17.30, 78.41, 17.37)},
        "description": "Artificial lake parallel to Osman Sagar, built for flood control and irrigation.",
    },
    {
        "slug": "nagarjuna-sagar",
        "name": "Nagarjuna Sagar Reservoir",
        "center_lat": 16.5722,
        "center_lon": 79.3122,
        "geojson": {"type": "Polygon", "coordinates": _box(79.20, 16.45, 79.45, 16.70)},
        "description": "One of the largest masonry dam reservoirs in Asia, on the Krishna River.",
    },
    {
        "slug": "nizam-sagar",
        "name": "Nizam Sagar Dam",
        "center_lat": 18.2667,
        "center_lon": 77.9333,
        "geojson": {"type": "Polygon", "coordinates": _box(77.85, 18.20, 78.00, 18.35)},
        "description": "Reservoir on the Manjira River in Nizamabad district, built 1923-31.",
    },
    {
        "slug": "singur-dam",
        "name": "Singur Dam",
        "center_lat": 17.7333,
        "center_lon": 77.9333,
        "geojson": {"type": "Polygon", "coordinates": _box(77.85, 17.68, 78.00, 17.80)},
        "description": "Telangana's largest artificial lake, on the Manjira River in Medak district.",
    },
]


def get_water_body_by_slug(slug: str) -> dict | None:
    slug = (slug or "").strip().lower()
    for w in WATER_BODIES:
        if w["slug"] == slug:
            return w
    return None


def list_water_bodies_summary() -> list[dict]:
    return [
        {"slug": w["slug"], "name": w["name"], "center_lat": w["center_lat"], "center_lon": w["center_lon"], "description": w["description"]}
        for w in WATER_BODIES
    ]


def point_inside_telangana(lat: float, lon: float) -> bool:
    b = TELANGANA_BOUNDS
    return b["min_lat"] <= lat <= b["max_lat"] and b["min_lon"] <= lon <= b["max_lon"]