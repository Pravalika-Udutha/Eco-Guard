from datetime import datetime

from pydantic import BaseModel, Field


class DangerZoneCreate(BaseModel):
    latitude: float
    longitude: float
    radius: float = Field(gt=0, description="Radius in meters")
    severity: str = "low"


class DangerZoneRead(BaseModel):
    id: int
    latitude: float
    longitude: float
    radius: float
    severity: str
    created_at: datetime

    model_config = {"from_attributes": True}


class LocationUpdateRequest(BaseModel):
    latitude: float
    longitude: float
    user_id: str | None = Field(
        default=None,
        description="Optional id for per-user alert cooldown (defaults to 'default')",
    )


class ZoneMatch(BaseModel):
    latitude: float
    longitude: float
    radius: float
    severity: str


class LocationUpdateResponse(BaseModel):
    inside_zone: bool
    near_danger: bool = False
    risk_level: str = "clear"
    zone: ZoneMatch | None
    near_zone: ZoneMatch | None = None
    distance_meters: float | None = None
    distance_to_edge_meters: float | None = None
    near_distance_meters: float | None = None
    user_message: str = ""
    alert_triggered: bool = False
    alert_channel: str | None = None
    alert_detail: str | None = None
    proximity_alert_triggered: bool = False
    proximity_alert_channel: str | None = None
    proximity_alert_detail: str | None = None
    gee_sync: dict | None = None


class GeeSyncRequest(BaseModel):
    latitude: float
    longitude: float


class GeeSyncResponse(BaseModel):
    ok: bool
    skipped: bool
    change_detected: bool = False
    zones_upserted: int = 0
    reason: str | None = None
    gee: dict | None = None


# ============================
# Forest Monitoring Schemas
# ============================

class TelanganaRegionCreate(BaseModel):
    name: str
    geojson_geometry: str  # GeoJSON polygon as string
    center_lat: float
    center_lon: float
    forest_area_sq_km: float | None = None
    description: str | None = None


class TelanganaRegionRead(BaseModel):
    id: int
    name: str
    center_lat: float
    center_lon: float
    forest_area_sq_km: float | None
    description: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ForestChangeDetected(BaseModel):
    region_id: int
    latitude: float
    longitude: float
    ndvi_before: float
    ndvi_after: float
    area_affected_sq_meters: float | None = None
    change_date: datetime
    detection_confidence: float
    satellite_source: str = "Sentinel-2"
    image_url: str | None = None


class ForestChangeRead(BaseModel):
    id: int
    region_id: int
    latitude: float
    longitude: float
    ndvi_before: float
    ndvi_after: float
    ndvi_change: float
    area_affected_sq_meters: float | None
    change_date: datetime
    detection_confidence: float
    status: str
    satellite_source: str
    image_url: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ForestChangeVerificationCreate(BaseModel):
    change_id: int
    admin_id: str
    admin_name: str | None = None
    is_legal: bool
    change_type: str | None = None
    verification_notes: str | None = None
    alert_channels: str = "SMS,Email"  # Comma-separated


class ForestChangeVerificationRead(BaseModel):
    id: int
    change_id: int
    admin_id: str
    admin_name: str | None
    is_legal: bool
    change_type: str | None
    verification_notes: str | None
    alert_sent: bool
    alert_sent_at: datetime | None
    alert_channels: str
    verified_at: datetime

    model_config = {"from_attributes": True}


class AlertRecipientCreate(BaseModel):
    region_id: int
    name: str
    organization: str | None = None
    role: str | None = None  # Forest Officer, NGO, HR, Water Body Manager, etc.
    phone: str | None = None
    email: str | None = None
    fax: str | None = None


class AlertRecipientRead(BaseModel):
    id: int
    region_id: int
    name: str
    organization: str | None
    role: str | None
    phone: str | None
    email: str | None
    fax: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class SeasonalNDVIThresholdCreate(BaseModel):
    season: str  # summer, monsoon, winter
    forest_ndvi_min: float
    change_threshold: float
    confidence_threshold: float = 0.7
    max_days_difference: int = 3
    months: str | None = None  # e.g., "3,4,5"
    description: str | None = None


class SeasonalNDVIThresholdRead(BaseModel):
    id: int
    season: str
    forest_ndvi_min: float
    change_threshold: float
    confidence_threshold: float
    max_days_difference: int
    months: str | None
    description: str | None
    created_at: datetime

    model_config = {"from_attributes": True}