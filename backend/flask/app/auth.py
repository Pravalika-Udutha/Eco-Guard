"""Admin-only API token check (no public access)."""

from __future__ import annotations

from functools import wraps

from flask import jsonify, request

from app.config import Config


def require_admin(f):
    """Require `X-Admin-Token` header to match ADMIN_API_TOKEN."""

    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("X-Admin-Token", "")
        if not token or token != Config.ADMIN_API_TOKEN:
            return jsonify({"error": "Unauthorized", "detail": "Valid X-Admin-Token required"}), 401
        return f(*args, **kwargs)

    return decorated