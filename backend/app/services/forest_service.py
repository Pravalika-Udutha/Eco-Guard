"""Service for managing Telangana regions and forest monitoring."""

import json
import logging
from datetime import datetime
from typing import Optional

import shapely.geometry
from sqlalchemy.orm import Session

from app.models.forest import (
    TelanganaRegion,
    ForestChange,
    ForestChangeVerification,
    AlertRecipient,
    SeasonalNDVIThreshold,
    ChangeStatus,
    Season,
)
from app.schemas import (
    ForestChangeDetected,
    TelanganaRegionCreate,
    AlertRecipientCreate,
)

logger = logging.getLogger(__name__)


def point_in_region(latitude: float, longitude: float, geojson_str: str) -> bool:
    """Check if a point (lat, lon) is within a GeoJSON polygon."""
    try:
        geometry = json.loads(geojson_str)
        shape = shapely.geometry.shape(geometry)
        point = shapely.geometry.Point(longitude, latitude)  # Note: lat/lon vs lon/lat
        return shape.contains(point)
    except Exception as e:
        logger.error(f"Error checking point in region: {e}")
        return False


def get_region_for_location(
    db: Session, latitude: float, longitude: float
) -> Optional[TelanganaRegion]:
    """Find which Telangana region a location falls into."""
    regions = db.query(TelanganaRegion).filter(TelanganaRegion.is_active == True).all()

    for region in regions:
        if point_in_region(latitude, longitude, region.geojson_geometry):
            return region

    return None


def create_region(db: Session, payload: TelanganaRegionCreate) -> TelanganaRegion:
    """Create a new Telangana forest region."""
    region = TelanganaRegion(
        name=payload.name,
        geojson_geometry=payload.geojson_geometry,
        center_lat=payload.center_lat,
        center_lon=payload.center_lon,
        forest_area_sq_km=payload.forest_area_sq_km,
        description=payload.description,
    )
    db.add(region)
    db.commit()
    db.refresh(region)
    return region


def list_regions(db: Session) -> list[TelanganaRegion]:
    """List all active Telangana regions."""
    return db.query(TelanganaRegion).filter(TelanganaRegion.is_active == True).all()


def detect_forest_change(
    db: Session,
    payload: ForestChangeDetected,
) -> ForestChange:
    """Record a detected forest change."""
    change = ForestChange(
        region_id=payload.region_id,
        latitude=payload.latitude,
        longitude=payload.longitude,
        ndvi_before=payload.ndvi_before,
        ndvi_after=payload.ndvi_after,
        ndvi_change=payload.ndvi_after - payload.ndvi_before,
        area_affected_sq_meters=payload.area_affected_sq_meters,
        change_date=payload.change_date,
        detection_confidence=payload.detection_confidence,
        satellite_source=payload.satellite_source,
        image_url=payload.image_url,
        status=ChangeStatus.DETECTED.value,
    )
    db.add(change)
    db.commit()
    db.refresh(change)
    return change


def get_pending_verifications(db: Session, region_id: Optional[int] = None) -> list[ForestChange]:
    """Get all forest changes pending admin verification."""
    query = db.query(ForestChange).filter(
        ForestChange.status == ChangeStatus.DETECTED.value
    )
    if region_id:
        query = query.filter(ForestChange.region_id == region_id)

    return query.order_by(ForestChange.change_date.desc()).all()


def verify_change(
    db: Session,
    change_id: int,
    admin_id: str,
    is_legal: bool,
    change_type: str | None = None,
    notes: str | None = None,
    alert_channels: str = "SMS,Email",
) -> ForestChangeVerification:
    """Admin verifies if a forest change is legal or illegal."""

    change = db.query(ForestChange).filter(ForestChange.id == change_id).first()
    if not change:
        raise ValueError(f"No forest change found with ID {change_id}")

    status = ChangeStatus.VERIFIED_LEGAL if is_legal else ChangeStatus.VERIFIED_ILLEGAL
    change.status = status.value

    verification = ForestChangeVerification(
        change_id=change_id,
        admin_id=admin_id,
        is_legal=is_legal,
        change_type=change_type,
        verification_notes=notes,
        alert_channels=alert_channels,
        alert_sent=False,
    )

    db.add(verification)
    db.commit()
    db.refresh(verification)

    return verification


def get_region_alert_recipients(db: Session, region_id: int) -> list[AlertRecipient]:
    """Get all active alert recipients (authorities, NGOs, etc.) for a region."""
    return db.query(AlertRecipient).filter(
        AlertRecipient.region_id == region_id,
        AlertRecipient.is_active == True,
    ).all()


def add_alert_recipient(
    db: Session,
    payload: AlertRecipientCreate,
) -> AlertRecipient:
    """Add a new alert recipient (authority, NGO, etc.) for a region."""
    recipient = AlertRecipient(
        region_id=payload.region_id,
        name=payload.name,
        organization=payload.organization,
        role=payload.role,
        phone=payload.phone,
        email=payload.email,
        fax=payload.fax,
    )
    db.add(recipient)
    db.commit()
    db.refresh(recipient)
    return recipient


def get_current_season() -> Season:
    """Determine current season based on month."""
    month = datetime.now().month

    if month in [3, 4, 5]:
        return Season.SUMMER
    elif month in [6, 7, 8, 9]:
        return Season.MONSOON
    else:
        return Season.WINTER


def get_seasonal_threshold(
    db: Session,
    season: Optional[Season] = None,
) -> Optional[SeasonalNDVIThreshold]:
    """Get NDVI thresholds for current or specified season."""
    if not season:
        season = get_current_season()

    return db.query(SeasonalNDVIThreshold).filter(
        SeasonalNDVIThreshold.season == season.value
    ).first()


def is_forest(ndvi: float, db: Session, season: Optional[Season] = None) -> bool:
    """Determine if an NDVI value qualifies as forest."""
    threshold = get_seasonal_threshold(db, season)
    if not threshold:
        return ndvi > 0.4

    return ndvi >= threshold.forest_ndvi_min


def is_significant_change(
    ndvi_before: float,
    ndvi_after: float,
    db: Session,
    season: Optional[Season] = None,
) -> bool:
    """Check if NDVI change is significant enough to flag."""
    threshold = get_seasonal_threshold(db, season)
    if not threshold:
        return abs(ndvi_before - ndvi_after) > 0.2

    change = ndvi_before - ndvi_after  # Positive = loss
    return change >= threshold.change_threshold