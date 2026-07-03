"""Seed the database with the original reference data."""

import json

from app.db import SessionLocal, Base, engine
from app.models import (
    TelanganaRegion,
    AlertRecipient,
    SeasonalNDVIThreshold,
    DangerZone,
)


REGIONS = [
    dict(
        name="Mulaganda National Forest",
        geojson_geometry=json.dumps({"type": "Polygon", "coordinates": [[[78.2, 17.2], [78.8, 17.2], [78.8, 17.8], [78.2, 17.8], [78.2, 17.2]]]}),
        center_lat=17.5, center_lon=78.5, forest_area_sq_km=1250.0,
        description="Major forest reserve in northern Telangana",
    ),
    dict(
        name="Amrabad Wildlife Sanctuary",
        geojson_geometry=json.dumps({"type": "Polygon", "coordinates": [[[78.4, 16.0], [79.0, 16.0], [79.0, 16.6], [78.4, 16.6], [78.4, 16.0]]]}),
        center_lat=16.3, center_lon=78.7, forest_area_sq_km=2631.0,
        description="Major wildlife sanctuary in Telangana",
    ),
    dict(
        name="Kawal Wildlife Sanctuary",
        geojson_geometry=json.dumps({"type": "Polygon", "coordinates": [[[77.5, 18.9], [78.1, 18.9], [78.1, 19.5], [77.5, 19.5], [77.5, 18.9]]]}),
        center_lat=19.2, center_lon=77.8, forest_area_sq_km=895.0,
        description="Forest sanctuary in Adilabad district",
    ),
    dict(
        name="Mahavir Harina Vanasthali National Park",
        geojson_geometry=json.dumps({"type": "Polygon", "coordinates": [[[77.2, 28.2], [77.8, 28.2], [77.8, 28.8], [77.2, 28.8], [77.2, 28.2]]]}),
        center_lat=28.5, center_lon=77.5, forest_area_sq_km=3770.0,
        description="Protected forest area in southern Telangana",
    ),
    dict(
        name="Nagarjunasagar Srisailam Tiger Reserve",
        geojson_geometry=json.dumps({"type": "Polygon", "coordinates": [[[78.9, 16.2], [79.5, 16.2], [79.5, 16.8], [78.9, 16.8], [78.9, 16.2]]]}),
        center_lat=16.5, center_lon=79.2, forest_area_sq_km=3568.0,
        description="Tiger reserve spanning Telangana and Andhra Pradesh",
    ),
]

RECIPIENTS = [
    dict(region_id=1, name="Regional Forest Officer", organization="Forest Department, Telangana",
         role="Forest Officer", phone="+91-40-23450000", email="rfo.muluganda@forests.telangana.gov.in", fax="+91-40-23451234"),
    dict(region_id=1, name="Wildlife Conservation Group", organization="Telangana Wildlife Preservation NGO",
         role="NGO", phone="+91-40-23456789", email="alert@twcg.org.in", fax=None),
    dict(region_id=1, name="Water Resources Department", organization="Irrigation Department, Telangana",
         role="Water Body Manager", phone="+91-40-23460000", email="water.mgmt@irrigation.telangana.gov.in", fax="+91-40-23461234"),
    dict(region_id=2, name="Sanctuary Director", organization="Forest Department, Telangana",
         role="Forest Officer", phone="+91-40-23451111", email="director.amrabad@forests.telangana.gov.in", fax="+91-40-23452222"),
    dict(region_id=2, name="Wildlife Management Authority", organization="Ministry of Environment & Forests",
         role="Government Officer", phone="+91-40-23453333", email="alert@wma.org.in", fax="+91-40-23454444"),
]

THRESHOLDS = [
    dict(season="summer", forest_ndvi_min=0.45, change_threshold=0.25, confidence_threshold=0.75,
         max_days_difference=3, months="3,4,5",
         description="Summer (March-May) - Hot and dry season. Higher NDVI variation expected due to water stress."),
    dict(season="monsoon", forest_ndvi_min=0.5, change_threshold=0.2, confidence_threshold=0.7,
         max_days_difference=3, months="6,7,8,9",
         description="Monsoon (June-September) - Wet season with lush vegetation. Lower thresholds due to cloud cover."),
    dict(season="winter", forest_ndvi_min=0.48, change_threshold=0.22, confidence_threshold=0.72,
         max_days_difference=3, months="10,11,12,1,2",
         description="Winter (October-February) - Cool season. Moderate NDVI with clear skies."),
]

DANGER_ZONES = [
    dict(latitude=8.0, longitude=80.0, radius=300.0, severity="high"),
    dict(latitude=10.0, longitude=71.0, radius=300.0, severity="high"),
]


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(TelanganaRegion).count() == 0:
            for r in REGIONS:
                db.add(TelanganaRegion(**r))
            db.commit()
            print(f"Inserted {len(REGIONS)} regions")
        else:
            print("Regions already seeded, skipping")

        if db.query(AlertRecipient).count() == 0:
            for r in RECIPIENTS:
                db.add(AlertRecipient(**r))
            db.commit()
            print(f"Inserted {len(RECIPIENTS)} alert recipients")
        else:
            print("Alert recipients already seeded, skipping")

        if db.query(SeasonalNDVIThreshold).count() == 0:
            for t in THRESHOLDS:
                db.add(SeasonalNDVIThreshold(**t))
            db.commit()
            print(f"Inserted {len(THRESHOLDS)} seasonal thresholds")
        else:
            print("Seasonal thresholds already seeded, skipping")

        if db.query(DangerZone).count() == 0:
            for z in DANGER_ZONES:
                db.add(DangerZone(**z))
            db.commit()
            print(f"Inserted {len(DANGER_ZONES)} danger zones")
        else:
            print("Danger zones already seeded, skipping")

    finally:
        db.close()


if __name__ == "__main__":
    seed()