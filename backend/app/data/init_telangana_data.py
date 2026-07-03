"""Script to initialize Telangana forest data in the database."""

import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_path))

# Load .env from project root
from dotenv import load_dotenv
project_root = backend_path.parent
dotenv_path = project_root / ".env"
load_dotenv(dotenv_path)

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import Base
from app.data.telangana_regions import (
    TELANGANA_REGIONS,
    SEASONAL_NDVI_THRESHOLDS,
    ALERT_RECIPIENTS_BY_REGION,
    get_region_geojson_string,
)
from app.models.forest import (
    TelanganaRegion,
    SeasonalNDVIThreshold,
    AlertRecipient,
)


def init_database():
    """Initialize database with sample Telangana forest regions and data."""

    engine = create_engine(settings.database_url)
    Base.metadata.create_all(bind=engine)

    with Session(engine) as db:
        print("Adding Telangana forest regions...")
        for region_data in TELANGANA_REGIONS:
            existing = db.query(TelanganaRegion).filter(
                TelanganaRegion.name == region_data["name"]
            ).first()

            if not existing:
                region = TelanganaRegion(
                    name=region_data["name"],
                    geojson_geometry=get_region_geojson_string(region_data),
                    center_lat=region_data["center_lat"],
                    center_lon=region_data["center_lon"],
                    forest_area_sq_km=region_data.get("forest_area_sq_km"),
                    description=region_data.get("description"),
                )
                db.add(region)
                print(f"  Added: {region_data['name']}")
            else:
                print(f"  Already exists: {region_data['name']}")

        db.commit()

        print("\nAdding seasonal NDVI thresholds...")
        for threshold_data in SEASONAL_NDVI_THRESHOLDS:
            existing = db.query(SeasonalNDVIThreshold).filter(
                SeasonalNDVIThreshold.season == threshold_data["season"]
            ).first()

            if not existing:
                threshold = SeasonalNDVIThreshold(
                    season=threshold_data["season"],
                    months=threshold_data["months"],
                    forest_ndvi_min=threshold_data["forest_ndvi_min"],
                    change_threshold=threshold_data["change_threshold"],
                    confidence_threshold=threshold_data["confidence_threshold"],
                    max_days_difference=threshold_data["max_days_difference"],
                    description=threshold_data["description"],
                )
                db.add(threshold)
                print(f"  Added: {threshold_data['season'].title()}")
            else:
                print(f"  Already exists: {threshold_data['season'].title()}")

        db.commit()

        print("\nAdding alert recipients...")
        for region_name, recipients in ALERT_RECIPIENTS_BY_REGION.items():
            region = db.query(TelanganaRegion).filter(
                TelanganaRegion.name == region_name
            ).first()

            if region:
                for recipient_data in recipients:
                    existing = db.query(AlertRecipient).filter(
                        AlertRecipient.region_id == region.id,
                        AlertRecipient.name == recipient_data["name"],
                    ).first()

                    if not existing:
                        recipient = AlertRecipient(
                            region_id=region.id,
                            name=recipient_data["name"],
                            organization=recipient_data.get("organization"),
                            role=recipient_data.get("role"),
                            phone=recipient_data.get("phone"),
                            email=recipient_data.get("email"),
                            fax=recipient_data.get("fax"),
                        )
                        db.add(recipient)
                        print(f"  Added: {recipient_data['name']} ({region_name})")
                    else:
                        print(f"  Already exists: {recipient_data['name']} ({region_name})")

        db.commit()

    print("\nDatabase initialization complete!")


if __name__ == "__main__":
    init_database()