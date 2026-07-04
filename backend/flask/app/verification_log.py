"""PostgreSQL audit log of who verified each analysis as Legal/Illegal."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, Integer, String, Text, create_engine, func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from app.config import Config

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


class AnalysisVerification(Base):
    __tablename__ = "analysis_verifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    analysis_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    region_slug: Mapped[str] = mapped_column(String(128), nullable=False)
    decision: Mapped[str] = mapped_column(String(16), nullable=False)  # "legal" | "illegal"
    admin_id: Mapped[str] = mapped_column(String(128), nullable=False)
    admin_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    loss_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


_engine = None
_SessionLocal: sessionmaker | None = None


def _engine_and_session():
    global _engine, _SessionLocal
    if _engine is None:
        url = (Config.DATABASE_URL or "").strip()
        if not url:
            raise RuntimeError("DATABASE_URL is required to log verifications")
        _engine = create_engine(url, pool_pre_ping=True, future=True)
        _SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False, future=True)
    assert _SessionLocal is not None
    return _engine, _SessionLocal


def init_verification_log() -> None:
    engine, _ = _engine_and_session()
    Base.metadata.create_all(engine)


def record_verification(
    *,
    analysis_id: str,
    region_slug: str,
    decision: str,
    admin_id: str,
    admin_name: str | None = None,
    loss_percent: float | None = None,
    status: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """Insert one audit row. Never raises to the caller — logs and returns ok=False on failure."""
    try:
        _, SessionLocal = _engine_and_session()
        with SessionLocal() as session:
            row = AnalysisVerification(
                analysis_id=analysis_id,
                region_slug=region_slug,
                decision=decision,
                admin_id=admin_id,
                admin_name=admin_name,
                loss_percent=loss_percent,
                status=status,
                notes=notes,
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return {"ok": True, "id": row.id, "verified_at": row.verified_at.isoformat()}
    except Exception:
        logger.exception("Failed to record verification for analysis_id=%s", analysis_id)
        return {"ok": False}


def list_verifications(region_slug: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    """Return recent verifications, optionally filtered by region, newest first."""
    try:
        _, SessionLocal = _engine_and_session()
        with SessionLocal() as session:
            stmt = select(AnalysisVerification).order_by(AnalysisVerification.verified_at.desc())
            if region_slug:
                stmt = stmt.where(AnalysisVerification.region_slug == region_slug)
            stmt = stmt.limit(limit)
            rows = session.scalars(stmt).all()
            return [
                {
                    "id": r.id,
                    "analysis_id": r.analysis_id,
                    "region_slug": r.region_slug,
                    "decision": r.decision,
                    "admin_id": r.admin_id,
                    "admin_name": r.admin_name,
                    "loss_percent": r.loss_percent,
                    "status": r.status,
                    "notes": r.notes,
                    "verified_at": r.verified_at.isoformat() if r.verified_at else None,
                }
                for r in rows
            ]
    except Exception:
        logger.exception("Failed to list verifications")
        return []