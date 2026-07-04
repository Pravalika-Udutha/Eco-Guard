"""Two auth layers: static admin token (existing) and per-user login sessions (new)."""

from __future__ import annotations

from functools import wraps

from flask import g, jsonify, request

from app.config import Config


def require_admin(f):
    """Require `X-Admin-Token` header to match ADMIN_API_TOKEN (used for admin-only oversight routes)."""

    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("X-Admin-Token", "")
        if not token or token != Config.ADMIN_API_TOKEN:
            return jsonify({"error": "Unauthorized", "detail": "Valid X-Admin-Token required"}), 401
        return f(*args, **kwargs)

    return decorated


def require_user(f):
    """Require `Authorization: Bearer <token>` matching a logged-in user session."""

    @wraps(f)
    def decorated(*args, **kwargs):
        from app.auth_users import get_user_from_token

        auth_header = request.headers.get("Authorization", "")
        token = auth_header[7:].strip() if auth_header.startswith("Bearer ") else ""
        user = get_user_from_token(token)
        if not user:
            return jsonify({"error": "Unauthorized", "detail": "Please log in"}), 401
        g.current_user = user
        return f(*args, **kwargs)

    return decorated