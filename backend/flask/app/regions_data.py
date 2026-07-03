"""
Predefined Telangana regions with coordinates and forest names.

Each region has a stable `slug` for URLs, a center point, a simple polygon in
WGS84 (GeoJSON coordinates: [lon, lat]), and a list of major forest / reserve
names for admin display (not individual GEE polygons per forest in this MVP).
"""

from __future__ import annotations

# Telangana state rough outer bounds for validation (subset of India)
TELANGANA_BOUNDS = {
    "min_lat": 15.8,
    "max_lat": 19.9,
    "min_lon": 77.0,
    "max_lon": 81.5,
}


def _box(minx: float, miny: float, maxx: float, maxy: float) -> list[list[list[float]]]:
    """Axis-aligned rectangle as GeoJSON Polygon outer ring (lon, lat)."""
    return [
        [
            [minx, miny],
            [maxx, miny],
            [maxx, maxy],
            [minx, maxy],
            [minx, miny],
        ]
    ]


REGIONS: list[dict] = [
    {
        "slug": "hyderabad",
        "name": "Hyderabad",
        "center_lat": 17.385,
        "center_lon": 78.4867,
        "geojson": {"type": "Polygon", "coordinates": _box(78.2, 17.2, 78.65, 17.55)},
        "forests": [
            "Kasu Brahmananda Reddy National Park",
            "Mahavir Harina Vanasthali National Park",
            "Mrugavani National Park",
            "Ameenpur Reserve Forest (periphery)",
        ],
    },
    {
        "slug": "warangal",
        "name": "Warangal",
        "center_lat": 17.9689,
        "center_lon": 79.5941,
        "geojson": {"type": "Polygon", "coordinates": _box(79.35, 17.75, 79.85, 18.2)},
        "forests": [
            "Eturnagaram Wildlife Sanctuary (range)",
            "Pakhal Wildlife Sanctuary (range)",
            "Govindaraopet Reserve Forest blocks",
        ],
    },
    {
        "slug": "khammam",
        "name": "Khammam",
        "center_lat": 17.2473,
        "center_lon": 80.1514,
        "geojson": {"type": "Polygon", "coordinates": _box(79.9, 16.95, 80.45, 17.55)},
        "forests": [
            "Kinnerasani Wildlife Sanctuary (range)",
            "Papikondalu forest belt (adjacent tracts)",
            "Dammapet Reserve blocks",
        ],
    },
    {
        "slug": "nizamabad",
        "name": "Nizamabad",
        "center_lat": 18.6725,
        "center_lon": 78.0941,
        "geojson": {"type": "Polygon", "coordinates": _box(77.75, 18.35, 78.35, 18.95)},
        "forests": [
            "Pocharam Wildlife Sanctuary (range)",
            "Nizamabad division reserve compartments",
        ],
    },
    {
        "slug": "karimnagar",
        "name": "Karimnagar",
        "center_lat": 18.4386,
        "center_lon": 79.1288,
        "geojson": {"type": "Polygon", "coordinates": _box(78.85, 18.15, 79.45, 18.65)},
        "forests": [
            "Kawal Tiger Reserve (peripheral Telangana tracts)",
            "Sirpur forest blocks",
        ],
    },
    {
        "slug": "mahbubnagar",
        "name": "Mahbubnagar",
        "center_lat": 16.7488,
        "center_lon": 77.9856,
        "geojson": {"type": "Polygon", "coordinates": _box(77.55, 16.45, 78.35, 17.05)},
        "forests": [
            "Farahabad tiger landscape linkage (forest patches)",
            "Achampet division reserve forests",
        ],
    },
]


def get_region_by_slug(slug: str) -> dict | None:
    slug = (slug or "").strip().lower()
    for r in REGIONS:
        if r["slug"] == slug:
            return r
    return None


def list_regions_summary() -> list[dict]:
    """Public list for GET /regions."""
    return [
        {
            "slug": r["slug"],
            "name": r["name"],
            "center_lat": r["center_lat"],
            "center_lon": r["center_lon"],
            "forest_count": len(r["forests"]),
        }
        for r in REGIONS
    ]


def point_inside_telangana(lat: float, lon: float) -> bool:
    b = TELANGANA_BOUNDS
    return b["min_lat"] <= lat <= b["max_lat"] and b["min_lon"] <= lon <= b["max_lon"]