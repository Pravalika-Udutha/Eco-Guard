"""PostgreSQL contacts store: region-scoped authorities, NGOs, HR.

Uses the same DATABASE_URL as the FastAPI stack (repo-root .env).
Table: telangana_alert_contacts
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import Integer, String, Text, create_engine, func, select, update
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from app.config import Config

logger = logging.getLogger(__name__)

# SMS destinations for illegal-change alerts (E.164) — one number per role; authority has no SMS (email only).
# NOTE: these are placeholder demo numbers from the original project — replace with your own test numbers.
_PHONE_BY_ROLE: dict[str, str] = {
    "forest_department": "",
    "ngo": "",
    "human_resources": "",
    "authority": "",
}


class Base(DeclarativeBase):
    pass


class TelanganaAlertContact(Base):
    __tablename__ = "telangana_alert_contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    region_slug: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    organization: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)


_engine = None
_SessionLocal: sessionmaker | None = None


def _require_pg_url() -> str:
    url = (Config.DATABASE_URL or "").strip()
    if not url:
        raise RuntimeError(
            "DATABASE_URL is required in .env (PostgreSQL). "
            "Example: postgresql+psycopg2://postgres:password@localhost:5432/ecoguard"
        )
    if url.lower().startswith("sqlite"):
        raise RuntimeError(
            "SQLite is no longer supported. Set DATABASE_URL to a postgresql+psycopg2:// connection string."
        )
    return url


def _engine_and_session():
    global _engine, _SessionLocal
    if _engine is None:
        url = _require_pg_url()
        _engine = create_engine(url, pool_pre_ping=True, future=True)
        _SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False, future=True)
    assert _SessionLocal is not None
    return _engine, _SessionLocal


def init_db() -> None:
    """Create telangana_alert_contacts table and seed demo rows if empty."""
    engine, SessionLocal = _engine_and_session()
    Base.metadata.create_all(engine)
    with SessionLocal() as session:
        n = session.scalar(select(func.count()).select_from(TelanganaAlertContact)) or 0
        if n == 0:
            _seed(session)
        _sync_alert_phone_numbers(session)
        session.commit()


def _seed(session: Session) -> None:
    """Demo contacts per Telangana region (fictional placeholders)."""
    for slug in ("hyderabad", "warangal", "khammam", "nizamabad", "karimnagar", "mahbubnagar"):
        session.add_all(
            [
                TelanganaAlertContact(
                    region_slug=slug,
                    role="forest_department",
                    name="Divisional Forest Officer",
                    organization=f"{slug.title()} Forest Division",
                    phone=_PHONE_BY_ROLE["forest_department"] or None,
                    email=f"dfo.{slug}@forest.telangana.gov.in",
                ),
                TelanganaAlertContact(
                    region_slug=slug,
                    role="ngo",
                    name="Green Watch NGO",
                    organization="Telangana Conservation Network",
                    phone=_PHONE_BY_ROLE["ngo"] or None,
                    email=f"alerts.{slug}@greenwatch.example.org",
                ),
                TelanganaAlertContact(
                    region_slug=slug,
                    role="human_resources",
                    name="HR Liaison",
                    organization="State Monitoring Cell",
                    phone=_PHONE_BY_ROLE["human_resources"] or None,
                    email=f"hr.{slug}@monitoring.example.gov.in",
                ),
                TelanganaAlertContact(
                    region_slug=slug,
                    role="authority",
                    name="District Collector Office",
                    organization=f"{slug.title()} District",
                    phone=None,
                    email=f"collector.{slug}@telangana.gov.in",
                ),
            ]
        )


def _sync_alert_phone_numbers(session: Session) -> None:
    """Keep SMS numbers aligned with _PHONE_BY_ROLE (new installs and existing DBs)."""
    for role, phone in _PHONE_BY_ROLE.items():
        session.execute(
            update(TelanganaAlertContact)
            .where(TelanganaAlertContact.role == role)
            .values(phone=phone if phone else None)
        )


def list_contacts_for_region(region_slug: str) -> list[dict[str, Any]]:
    """Return Postgres contacts for a region, or [] if DB is down / table missing (alerts still use Twilio/email fallbacks)."""
    region_slug = region_slug.strip().lower()
    try:
        _, SessionLocal = _engine_and_session()
        with SessionLocal() as session:
            rows = session.scalars(
                select(TelanganaAlertContact)
                .where(TelanganaAlertContact.region_slug == region_slug)
                .order_by(TelanganaAlertContact.role, TelanganaAlertContact.id)
            ).all()
            return [
                {
                    "id": r.id,
                    "region_slug": r.region_slug,
                    "role": r.role,
                    "name": r.name,
                    "organization": r.organization,
                    "phone": r.phone or "",
                    "email": r.email or "",
                }
                for r in rows
            ]
    except (OperationalError, ProgrammingError) as exc:
        logger.warning(
            "telangana_alert_contacts unavailable (%s); continuing with no DB contacts. "
            "Start PostgreSQL and restart Flask to restore contacts.",
            exc.__class__.__name__,
        )
        return []
    except RuntimeError:
        raise
    except Exception as exc:
        logger.warning("telangana_alert_contacts query failed: %s", exc)
        return []