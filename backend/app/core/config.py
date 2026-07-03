from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root = .../Eco-Guard (contains .env, backend/, frontend/)
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
_PROJECT_ROOT = _BACKEND_DIR.parent


def _env_file_path() -> Path:
    """Prefer a project-root .env, fall back to backend/.env."""
    if (_PROJECT_ROOT / ".env").is_file():
        return _PROJECT_ROOT / ".env"
    return _BACKEND_DIR / ".env"


class Settings(BaseSettings):
    app_name: str = "Eco-Guard"
    env: str = "development"

    database_url: str = Field(
        ...,
        description="PostgreSQL connection URL, e.g. postgresql://user:pass@localhost:5432/ecoguard",
    )

    # Google Earth Engine settings
    gee_enabled: bool = False
    gee_project: str | None = None
    gee_credentials_json: str | None = None
    gee_auto_sync_on_location: bool = True
    gee_buffer_meters: float = 5000
    gee_loss_mean_threshold: float = 0.01
    gee_ndvi_drop_threshold: float = 0.2
    gee_zone_radius_meters: float = 1500
    gee_before_start: str = "2022-01-01"
    gee_before_end: str = "2022-06-01"
    gee_after_start: str = "2023-01-01"
    gee_after_end: str = "2023-06-01"
    gee_s2_collection: str = "COPERNICUS/S2_SR_HARMONIZED"

    # Alerting / geofencing
    nearby_alert_buffer_meters: float = 2000
    alerts_enabled: bool = True
    alert_cooldown_seconds: int = 300

    # Twilio (optional SMS alerts)
    twilio_enabled: bool = False
    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    twilio_from_number: str | None = None
    alert_to_number: str | None = None

    model_config = SettingsConfigDict(
        env_file=str(_env_file_path()),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()