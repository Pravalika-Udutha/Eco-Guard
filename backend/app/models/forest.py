"""Forest region and change detection models for Telangana monitoring."""

import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ChangeStatus(str, enum.Enum):
    """Status of a detected forest change."""
    DETECTED = "detected"
    PENDING_REVIEW = "pending_review"
    VERIFIED_LEGAL = "verified_legal"
    VERIFIED_ILLEGAL = "verified_illegal"


class Season(str, enum.Enum):
    """Indian seasons for NDVI threshold adjustment."""
    SUMMER = "summer"      # Mar-May
    MONSOON = "monsoon"    # Jun-Sep
    WINTER = "winter"      # Oct-Feb


class TelanganaRegion(Base):
    """Predefined forest regions within Telangana state."""
    __tablename__ = "telangana_regions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    geojson_geometry: Mapped[str] = mapped_column(Text, nullable=False)
    center_lat: Mapped[float] = mapped_column(Float, nullable=False)
    center_lon: Mapped[float] = mapped_column(Float, nullable=False)
    forest_area_sq_km: Mapped[float] = mapped_column(Float, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ForestChange(Base):
    """Detected forest cover changes in Telangana regions."""
    __tablename__ = "forest_changes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    region_id: Mapped[int] = mapped_column(ForeignKey("telangana_regions.id"), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)

    # Change metrics
    ndvi_before: Mapped[float] = mapped_column(Float, nullable=False)
    ndvi_after: Mapped[float] = mapped_column(Float, nullable=False)
    ndvi_change: Mapped[float] = mapped_column(Float, nullable=False)

    # Detection info
    area_affected_sq_meters: Mapped[float] = mapped_column(Float, nullable=True)
    change_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    detection_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default=ChangeStatus.DETECTED.value)

    # Satellite info
    satellite_source: Mapped[str] = mapped_column(String(100), nullable=False)
    image_url: Mapped[str] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ForestChangeVerification(Base):
    """Admin verification of a detected forest change."""
    __tablename__ = "forest_change_verifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    change_id: Mapped[int] = mapped_column(ForeignKey("forest_changes.id"), nullable=False)
    admin_id: Mapped[str] = mapped_column(String(255), nullable=False)
    admin_name: Mapped[str] = mapped_column(String(255), nullable=True)

    # Verification details
    is_legal: Mapped[bool] = mapped_column(Boolean, nullable=False)
    change_type: Mapped[str] = mapped_column(String(255), nullable=True)
    verification_notes: Mapped[str] = mapped_column(Text, nullable=True)
    evidence_file_path: Mapped[str] = mapped_column(Text, nullable=True)

    alert_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    alert_sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    alert_channels: Mapped[str] = mapped_column(String(255), nullable=True)

    verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class AlertRecipient(Base):
    """Recipient who gets notified about forest changes in a region."""
    __tablename__ = "alert_recipients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    region_id: Mapped[int] = mapped_column(ForeignKey("telangana_regions.id"), nullable=False)

    # Recipient info
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    organization: Mapped[str] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(100), nullable=True)  # e.g. "Forest Officer", "NGO"

    # Contact channels
    phone: Mapped[str] = mapped_column(String(20), nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=True)
    fax: Mapped[str] = mapped_column(String(20), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class SeasonalNDVIThreshold(Base):
    """Seasonal NDVI thresholds for reliable forest change detection."""
    __tablename__ = "seasonal_ndvi_thresholds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    season: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    forest_ndvi_min: Mapped[float] = mapped_column(Float, nullable=False)  # Min NDVI to classify as forest
    change_threshold: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_threshold: Mapped[float] = mapped_column(Float, nullable=False)  # Min confidence score

    # Monitoring parameters
    max_days_difference: Mapped[int] = mapped_column(Integer, nullable=False)
    months: Mapped[str] = mapped_column(String(50), nullable=True)  # e.g. "3,4,5" for summer
    description: Mapped[str] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )