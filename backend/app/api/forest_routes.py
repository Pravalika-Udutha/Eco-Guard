"""API routes for Telangana forest monitoring."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.forest import (
    TelanganaRegion,
    ForestChange,
    AlertRecipient,
)
from app.schemas import (
    TelanganaRegionCreate,
    TelanganaRegionRead,
    ForestChangeDetected,
    ForestChangeRead,
    ForestChangeVerificationCreate,
    ForestChangeVerificationRead,
    AlertRecipientCreate,
    AlertRecipientRead,
    SeasonalNDVIThresholdCreate,
    SeasonalNDVIThresholdRead,
)
from app.services import forest_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/forest", tags=["forest-monitoring"])


# =============================
# REGIONS MANAGEMENT
# =============================

@router.post("/regions", response_model=TelanganaRegionRead)
def create_region(
    payload: TelanganaRegionCreate,
    db: Session = Depends(get_db),
):
    """Create a new Telangana forest region with GeoJSON boundaries."""
    existing = db.query(TelanganaRegion).filter(
        TelanganaRegion.name == payload.name
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail=f"Region '{payload.name}' already exists")

    return forest_service.create_region(db, payload)


@router.get("/regions", response_model=list[TelanganaRegionRead])
def list_regions(db: Session = Depends(get_db)):
    """List all Telangana forest regions."""
    return forest_service.list_regions(db)


@router.get("/regions/{region_id}", response_model=TelanganaRegionRead)
def get_region(region_id: int, db: Session = Depends(get_db)):
    """Get details of a specific region."""
    region = db.query(TelanganaRegion).filter(TelanganaRegion.id == region_id).first()
    if not region:
        raise HTTPException(status_code=404, detail="Region not found")
    return region


@router.get("/regions/location/{latitude}/{longitude}", response_model=TelanganaRegionRead | None)
def get_region_for_location(
    latitude: float,
    longitude: float,
    db: Session = Depends(get_db),
):
    """Find which region a location falls into."""
    return forest_service.get_region_for_location(db, latitude, longitude)


# =============================
# FOREST CHANGE DETECTION
# =============================

@router.post("/changes", response_model=ForestChangeRead)
def report_forest_change(
    payload: ForestChangeDetected,
    db: Session = Depends(get_db),
):
    """Record a detected forest change (typically from GEE)."""
    region = db.query(TelanganaRegion).filter(
        TelanganaRegion.id == payload.region_id
    ).first()
    if not region:
        raise HTTPException(status_code=404, detail="Region not found")

    change = forest_service.detect_forest_change(db, payload)
    return change


@router.get("/changes", response_model=list[ForestChangeRead])
def list_forest_changes(
    region_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """List all detected forest changes, optionally filtered by region."""
    query = db.query(ForestChange)

    if region_id:
        query = query.filter(ForestChange.region_id == region_id)

    return query.order_by(ForestChange.change_date.desc()).all()


@router.get("/changes/pending", response_model=list[ForestChangeRead])
def get_pending_verifications(
    region_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """Get forest changes pending admin verification."""
    return forest_service.get_pending_verifications(db, region_id)


# =============================
# ADMIN VERIFICATION
# =============================

@router.post("/verify", response_model=ForestChangeVerificationRead)
def verify_forest_change(
    payload: ForestChangeVerificationCreate,
    db: Session = Depends(get_db),
):
    """
    Admin verifies if a detected forest change is legal or illegal.
    If illegal, alerts are sent to authorities, NGOs, and other recipients.
    """
    verification = forest_service.verify_change(
        db,
        change_id=payload.change_id,
        admin_id=payload.admin_id,
        is_legal=payload.is_legal,
        change_type=payload.change_type,
        notes=payload.verification_notes,
        alert_channels=payload.alert_channels,
    )

    if not payload.is_legal:
        logger.info(f"Illegal forest change verified (ID: {payload.change_id}). Sending alerts...")

        from app.services.alert_system import send_illegal_change_alerts

        change = db.query(ForestChange).filter(ForestChange.id == payload.change_id).first()
        if change:
            recipients = forest_service.get_region_alert_recipients(db, change.region_id)

            if recipients:
                stats = send_illegal_change_alerts(db, change, verification, recipients)
                logger.info(f"Alert campaign complete: {stats}")
            else:
                logger.warning(f"No alert recipients configured for region {change.region_id}")

    return verification


# =============================
# ALERT RECIPIENTS
# =============================

@router.post("/recipients", response_model=AlertRecipientRead)
def add_alert_recipient(
    payload: AlertRecipientCreate,
    db: Session = Depends(get_db),
):
    """Add a new alert recipient (authority, NGO, etc.) for a region."""
    region = db.query(TelanganaRegion).filter(
        TelanganaRegion.id == payload.region_id
    ).first()
    if not region:
        raise HTTPException(status_code=404, detail="Region not found")

    return forest_service.add_alert_recipient(db, payload)


@router.get("/recipients/{region_id}", response_model=list[AlertRecipientRead])
def get_region_recipients(
    region_id: int,
    db: Session = Depends(get_db),
):
    """Get all alert recipients for a specific region."""
    region = db.query(TelanganaRegion).filter(
        TelanganaRegion.id == region_id
    ).first()
    if not region:
        raise HTTPException(status_code=404, detail="Region not found")

    return forest_service.get_region_alert_recipients(db, region_id)


@router.put("/recipients/{recipient_id}")
def update_recipient(
    recipient_id: int,
    payload: AlertRecipientCreate,
    db: Session = Depends(get_db),
):
    """Update alert recipient details."""
    recipient = db.query(AlertRecipient).filter(
        AlertRecipient.id == recipient_id
    ).first()
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")

    recipient.name = payload.name
    recipient.organization = payload.organization
    recipient.role = payload.role
    recipient.phone = payload.phone
    recipient.email = payload.email
    recipient.fax = payload.fax

    db.commit()
    db.refresh(recipient)
    return recipient


@router.delete("/recipients/{recipient_id}")
def delete_recipient(
    recipient_id: int,
    db: Session = Depends(get_db),
):
    """Soft-delete (deactivate) an alert recipient."""
    recipient = db.query(AlertRecipient).filter(
        AlertRecipient.id == recipient_id
    ).first()
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")

    recipient.is_active = False
    db.commit()

    return {"message": "Recipient deactivated"}


# =============================
# SEASONAL THRESHOLDS
# =============================

@router.post("/thresholds", response_model=SeasonalNDVIThresholdRead)
def create_seasonal_threshold(
    payload: SeasonalNDVIThresholdCreate,
    db: Session = Depends(get_db),
):
    """Create or update seasonal NDVI thresholds."""
    from app.models.forest import SeasonalNDVIThreshold

    existing = db.query(SeasonalNDVIThreshold).filter(
        SeasonalNDVIThreshold.season == payload.season
    ).first()

    if existing:
        existing.forest_ndvi_min = payload.forest_ndvi_min
        existing.change_threshold = payload.change_threshold
        existing.confidence_threshold = payload.confidence_threshold
        existing.max_days_difference = payload.max_days_difference
        existing.months = payload.months
        existing.description = payload.description
        db.commit()
        db.refresh(existing)
        return existing

    threshold = SeasonalNDVIThreshold(
        season=payload.season,
        forest_ndvi_min=payload.forest_ndvi_min,
        change_threshold=payload.change_threshold,
        confidence_threshold=payload.confidence_threshold,
        max_days_difference=payload.max_days_difference,
        months=payload.months,
        description=payload.description,
    )
    db.add(threshold)
    db.commit()
    db.refresh(threshold)
    return threshold


@router.get("/thresholds", response_model=list[SeasonalNDVIThresholdRead])
def get_seasonal_thresholds(db: Session = Depends(get_db)):
    """Get all seasonal NDVI thresholds."""
    from app.models.forest import SeasonalNDVIThreshold

    return db.query(SeasonalNDVIThreshold).all()


@router.get("/thresholds/{season}", response_model=SeasonalNDVIThresholdRead)
def get_season_threshold(
    season: str,
    db: Session = Depends(get_db),
):
    """Get NDVI thresholds for a specific season."""
    from app.models.forest import SeasonalNDVIThreshold

    threshold = db.query(SeasonalNDVIThreshold).filter(
        SeasonalNDVIThreshold.season == season
    ).first()

    if not threshold:
        raise HTTPException(status_code=404, detail=f"No thresholds configured for season '{season}'")

    return threshold