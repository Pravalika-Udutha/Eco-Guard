"""Sample Telangana forest regions data."""

import json

# Sample Telangana forest regions with GeoJSON polygons
# These are simplified examples for demonstration. Real data should use accurate boundaries.
TELANGANA_REGIONS = [
    {
        "name": "Mulaganda National Forest",
        "center_lat": 17.5,
        "center_lon": 78.5,
        "forest_area_sq_km": 1250.0,
        "description": "Major forest reserve in northern Telangana",
        "geojson_geometry": {
            "type": "Polygon",
            "coordinates": [[
                [78.2, 17.2], [78.8, 17.2], [78.8, 17.8], [78.2, 17.8], [78.2, 17.2]
            ]]
        }
    },
    {
        "name": "Amrabad Wildlife Sanctuary",
        "center_lat": 16.3,
        "center_lon": 78.7,
        "forest_area_sq_km": 2631.0,
        "description": "Major wildlife sanctuary in Telangana",
        "geojson_geometry": {
            "type": "Polygon",
            "coordinates": [[
                [78.4, 16.0], [79.0, 16.0], [79.0, 16.6], [78.4, 16.6], [78.4, 16.0]
            ]]
        }
    },
    {
        "name": "Kawal Wildlife Sanctuary",
        "center_lat": 19.2,
        "center_lon": 77.8,
        "forest_area_sq_km": 895.0,
        "description": "Forest sanctuary in Adilabad district",
        "geojson_geometry": {
            "type": "Polygon",
            "coordinates": [[
                [77.5, 18.9], [78.1, 18.9], [78.1, 19.5], [77.5, 19.5], [77.5, 18.9]
            ]]
        }
    },
    {
        "name": "Mahavir Harina Vanasthali National Park",
        "center_lat": 28.5,
        "center_lon": 77.5,
        "forest_area_sq_km": 3770.0,
        "description": "Protected forest area in southern Telangana",
        "geojson_geometry": {
            "type": "Polygon",
            "coordinates": [[
                [77.2, 28.2], [77.8, 28.2], [77.8, 28.8], [77.2, 28.8], [77.2, 28.2]
            ]]
        }
    },
    {
        "name": "Nagarjunasagar Srisailam Tiger Reserve",
        "center_lat": 16.5,
        "center_lon": 79.2,
        "forest_area_sq_km": 3568.0,
        "description": "Tiger reserve spanning Telangana and Andhra Pradesh",
        "geojson_geometry": {
            "type": "Polygon",
            "coordinates": [[
                [78.9, 16.2], [79.5, 16.2], [79.5, 16.8], [78.9, 16.8], [78.9, 16.2]
            ]]
        }
    }
]

# Seasonal NDVI thresholds for reliable change detection in Telangana
SEASONAL_NDVI_THRESHOLDS = [
    {
        "season": "summer",
        "months": "3,4,5",
        "forest_ndvi_min": 0.45,
        "change_threshold": 0.25,
        "confidence_threshold": 0.75,
        "max_days_difference": 3,
        "description": "Summer (March-May) - Hot and dry season. Higher NDVI variation expected due to water stress."
    },
    {
        "season": "monsoon",
        "months": "6,7,8,9",
        "forest_ndvi_min": 0.50,
        "change_threshold": 0.20,
        "confidence_threshold": 0.70,
        "max_days_difference": 3,
        "description": "Monsoon (June-September) - Wet season with lush vegetation. Lower thresholds due to cloud cover."
    },
    {
        "season": "winter",
        "months": "10,11,12,1,2",
        "forest_ndvi_min": 0.48,
        "change_threshold": 0.22,
        "confidence_threshold": 0.72,
        "max_days_difference": 3,
        "description": "Winter (October-February) - Cool season. Moderate NDVI with clear skies."
    }
]

# Sample alert recipients for each region
ALERT_RECIPIENTS_BY_REGION = {
    "Mulaganda National Forest": [
        {
            "name": "Regional Forest Officer",
            "organization": "Forest Department, Telangana",
            "role": "Forest Officer",
            "phone": "+91-40-23450000",
            "email": "rfo.muluganda@forests.telangana.gov.in",
            "fax": "+91-40-23451234"
        },
        {
            "name": "Wildlife Conservation Group",
            "organization": "Telangana Wildlife Preservation NGO",
            "role": "NGO",
            "phone": "+91-40-23456789",
            "email": "alert@twcg.org.in",
            "fax": None
        },
        {
            "name": "Water Resources Department",
            "organization": "Irrigation Department, Telangana",
            "role": "Water Body Manager",
            "phone": "+91-40-23460000",
            "email": "water.mgmt@irrigation.telangana.gov.in",
            "fax": "+91-40-23461234"
        }
    ],
    "Amrabad Wildlife Sanctuary": [
        {
            "name": "Sanctuary Director",
            "organization": "Forest Department, Telangana",
            "role": "Forest Officer",
            "phone": "+91-40-23451111",
            "email": "director.amrabad@forests.telangana.gov.in",
            "fax": "+91-40-23452222"
        },
        {
            "name": "Wildlife Management Authority",
            "organization": "Ministry of Environment & Forests",
            "role": "Government Officer",
            "phone": "+91-40-23453333",
            "email": "alert@wma.org.in",
            "fax": "+91-40-23454444"
        }
    ]
}


def get_region_geojson_string(region: dict) -> str:
    """Convert region geometry to JSON string."""
    return json.dumps(region["geojson_geometry"])


def get_sample_regions_for_db() -> list:
    """Get regions formatted for database insertion."""
    return [
        {
            "name": r["name"],
            "geojson_geometry": get_region_geojson_string(r),
            "center_lat": r["center_lat"],
            "center_lon": r["center_lon"],
            "forest_area_sq_km": r.get("forest_area_sq_km"),
            "description": r.get("description"),
        }
        for r in TELANGANA_REGIONS
    ]