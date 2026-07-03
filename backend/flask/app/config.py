"""Flask configuration for Eco-Guard Telangana (loads from environment)."""

import os
from pathlib import Path

from dotenv import load_dotenv

_flask_dir = Path(__file__).resolve().parent.parent
_repo_root = _flask_dir.parent.parent

# Repo-root .env (same as FastAPI), then optional backend/flask/.env overrides.
if (_repo_root / ".env").is_file():
    load_dotenv(_repo_root / ".env", override=True)
if (_flask_dir / ".env").is_file():
    load_dotenv(_flask_dir / ".env", override=True)


class Config:
    """Application configuration."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-change-in-production")
    ADMIN_API_TOKEN = os.environ.get("ADMIN_API_TOKEN", "dev-admin-token")

    # Telangana bounds (India) — reject analysis outside this box
    TELANGANA_MIN_LAT = float(os.environ.get("TELANGANA_MIN_LAT", "15.8"))
    TELANGANA_MAX_LAT = float(os.environ.get("TELANGANA_MAX_LAT", "19.9"))
    TELANGANA_MIN_LON = float(os.environ.get("TELANGANA_MIN_LON", "77.0"))
    TELANGANA_MAX_LON = float(os.environ.get("TELANGANA_MAX_LON", "81.5"))

    # Google Earth Engine
    GEE_ENABLED = os.environ.get("GEE_ENABLED", "false").lower() in ("1", "true", "yes")
    GEE_PROJECT = os.environ.get("GEE_PROJECT") or os.environ.get("GOOGLE_CLOUD_PROJECT", "")
    GEE_CREDENTIALS_JSON = os.environ.get("GEE_CREDENTIALS_JSON") or os.environ.get(
        "GOOGLE_APPLICATION_CREDENTIALS", ""
    )

    # Sentinel-2
    GEE_S2_COLLECTION = os.environ.get("GEE_S2_COLLECTION", "COPERNICUS/S2_SR_HARMONIZED")

    # NDVI rules: forest mask > 0.5; loss if NDVI drop exceeds threshold
    FOREST_NDVI_MIN = float(os.environ.get("FOREST_NDVI_MIN", "0.5"))
    NDVI_DROP_THRESHOLD_NORMAL = float(os.environ.get("NDVI_DROP_THRESHOLD_NORMAL", "-0.25"))
    NDVI_DROP_THRESHOLD_MONSOON = float(os.environ.get("NDVI_DROP_THRESHOLD_MONSOON", "-0.15"))
    MONSOON_MONTHS = {6, 7, 8, 9}

    MAX_PERIOD_DAYS = int(os.environ.get("MAX_PERIOD_DAYS", "3"))

    STATUS_MODERATE_MIN_PCT = float(os.environ.get("STATUS_MODERATE_MIN_PCT", "2.0"))
    STATUS_CRITICAL_MIN_PCT = float(os.environ.get("STATUS_CRITICAL_MIN_PCT", "10.0"))

    # PostgreSQL only — same DATABASE_URL as FastAPI (repo-root .env)
    DATABASE_URL = (os.environ.get("DATABASE_URL") or "").strip()

    BASE_DIR = Path(__file__).resolve().parent.parent

    _public_base = os.environ.get("PUBLIC_API_BASE_URL", "http://127.0.0.1:5000").rstrip("/")
    PUBLIC_API_BASE_URL = _public_base.replace("0.0.0.0", "127.0.0.1")

    _public_ui = os.environ.get("PUBLIC_UI_BASE_URL", "http://127.0.0.1:5173").rstrip("/")
    PUBLIC_UI_BASE_URL = _public_ui.replace("0.0.0.0", "127.0.0.1")

    # Twilio (optional)
    TWILIO_ENABLED = os.environ.get("TWILIO_ENABLED", "true").lower() in ("1", "true", "yes")
    TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
    TWILIO_FROM_NUMBER = os.environ.get("TWILIO_FROM_NUMBER", "")
    TWILIO_MESSAGING_SERVICE_SID = (os.environ.get("TWILIO_MESSAGING_SERVICE_SID") or "").strip()
    TWILIO_SMS_SHORT_BODY = os.environ.get("TWILIO_SMS_SHORT_BODY", "false").lower() in (
        "1", "true", "yes",
    )
    ALERT_TO_NUMBER = (os.environ.get("ALERT_TO_NUMBER") or "").strip()
    SIMULATE_SMS = os.environ.get("SIMULATE_SMS", "true").lower() in ("1", "true", "yes")
    TWILIO_SMS_ALL_CONTACTS = os.environ.get("TWILIO_SMS_ALL_CONTACTS", "true").lower() in (
        "1", "true", "yes",
    )

    # Flask-Mail
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "localhost")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", "587"))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() in ("1", "true", "yes")
    MAIL_USE_SSL = os.environ.get("MAIL_USE_SSL", "false").lower() in ("1", "true", "yes")
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
    _raw_mail_pw = (os.environ.get("MAIL_PASSWORD") or "").strip().strip('"').strip("'")
    MAIL_PASSWORD = "".join(_raw_mail_pw.split())
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "noreply@ecoguard.local")

    SENDGRID_API_KEY = (os.environ.get("SENDGRID_API_KEY") or "").strip()

    SIMULATE_EMAIL = os.environ.get("SIMULATE_EMAIL", "true").lower() in ("1", "true", "yes")
    ALERT_NOTIFY_EMAIL = (os.environ.get("ALERT_NOTIFY_EMAIL") or "").strip()
    ALERT_EMAIL_CONTACTS_ONLY_OPERATOR = os.environ.get(
        "ALERT_EMAIL_CONTACTS_ONLY_OPERATOR", "false"
    ).lower() in ("1", "true", "yes")

    @classmethod
    def operator_illegal_alert_email(cls) -> str:
        """Inbox that always receives one copy of illegal forest alerts when SMTP is enabled."""
        if cls.ALERT_NOTIFY_EMAIL and "@" in cls.ALERT_NOTIFY_EMAIL:
            return cls.ALERT_NOTIFY_EMAIL.strip()
        u = (cls.MAIL_USERNAME or "").strip()
        return u if "@" in u else ""