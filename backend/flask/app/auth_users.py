"""Simple username/password accounts with token-based sessions (Postgres-backed)."""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from werkzeug.security import check_password_hash, generate_password_hash

from app.config import Config

logger = logging.getLogger(__name__)

SESSION_LIFETIME = timedelta(days=14)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


_engine = None
_SessionLocal: sessionmaker | None = None


def _engine_and_session():
    global _engine, _SessionLocal
    if _engine is None:
        url = (Config.DATABASE_URL or "").strip()
        if not url:
            raise RuntimeError("DATABASE_URL is required for user accounts")
        _engine = create_engine(url, pool_pre_ping=True, future=True)
        _SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False, future=True)
    assert _SessionLocal is not None
    return _engine, _SessionLocal


def init_auth_tables() -> None:
    engine, _ = _engine_and_session()
    Base.metadata.create_all(engine)


def register_user(username: str, password: str) -> dict[str, Any]:
    username = username.strip()
    if len(username) < 3:
        return {"ok": False, "error": "Username must be at least 3 characters"}
    if len(password) < 6:
        return {"ok": False, "error": "Password must be at least 6 characters"}

    _, SessionLocal = _engine_and_session()
    with SessionLocal() as session:
        existing = session.scalar(select(User).where(User.username == username))
        if existing:
            return {"ok": False, "error": "Username already taken"}

        user = User(username=username, password_hash=generate_password_hash(password))
        session.add(user)
        session.commit()
        session.refresh(user)
        return {"ok": True, "user_id": user.id, "username": user.username}


def login_user(username: str, password: str) -> dict[str, Any]:
    username = username.strip()
    _, SessionLocal = _engine_and_session()
    with SessionLocal() as session:
        user = session.scalar(select(User).where(User.username == username))
        if not user or not check_password_hash(user.password_hash, password):
            return {"ok": False, "error": "Invalid username or password"}

        token = secrets.token_hex(32)
        expires_at = datetime.now(timezone.utc) + SESSION_LIFETIME
        session.add(UserSession(token=token, user_id=user.id, expires_at=expires_at))
        session.commit()

        return {"ok": True, "token": token, "user_id": user.id, "username": user.username}


def get_user_from_token(token: str) -> dict[str, Any] | None:
    if not token:
        return None
    _, SessionLocal = _engine_and_session()
    with SessionLocal() as session:
        sess = session.scalar(select(UserSession).where(UserSession.token == token))
        if not sess:
            return None
        if sess.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            return None
        user = session.get(User, sess.user_id)
        if not user:
            return None
        return {"user_id": user.id, "username": user.username}


def logout_user(token: str) -> None:
    _, SessionLocal = _engine_and_session()
    with SessionLocal() as session:
        sess = session.scalar(select(UserSession).where(UserSession.token == token))
        if sess:
            session.delete(sess)
            session.commit()