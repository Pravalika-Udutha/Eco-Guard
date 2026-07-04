"""Eco-Guard Telangana — Flask application factory."""

from __future__ import annotations

import logging

from flask import Flask, Response, jsonify, redirect, request
from flask_cors import CORS

from app.alerts_service import init_mail
from app.auth_users import init_auth_tables
from app.config import Config
from app.db_contacts import init_db
from app.routes import bp
from app.verification_log import init_verification_log

logger = logging.getLogger(__name__)


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config.setdefault("JSON_SORT_KEYS", False)

    init_mail(app)
    try:
        init_db()
    except Exception:
        logger.exception("Contacts DB init failed (continuing)")

    try:
        init_verification_log()
    except Exception:
        logger.exception("Verification log init failed (continuing)")

    try:
        init_auth_tables()
    except Exception:
        logger.exception("Auth tables init failed (continuing)")

    app.register_blueprint(bp)

    CORS(
        app,
        resources={
            r"/*": {
                "origins": [
                    "http://127.0.0.1:5173",
                    "http://localhost:5173",
                    "http://127.0.0.1:4173",
                    "http://localhost:4173",
                    "http://127.0.0.1:3000",
                ]
            }
        },
        supports_credentials=True,
        allow_headers=["Content-Type", "X-Admin-Token", "Authorization"],
    )

    @app.get("/")
    def root():
        m = request.accept_mimetypes
        strict_json = m.provided and m.accept_json and not m.accept_html and not m.accept_xhtml
        ui = f"{Config.PUBLIC_UI_BASE_URL.rstrip('/')}/"
        if strict_json:
            return jsonify({"service": "Eco-Guard Telangana API", "ui": ui.rstrip("/"), "health": "/health"})
        return redirect(ui, code=302)

    @app.get("/health")
    def health():
        return jsonify({"status": "ok", "service": "Eco-Guard Telangana", "gee_enabled": Config.GEE_ENABLED})

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(500)
    def server_err(e):
        return jsonify({"error": "Internal server error"}), 500

    return app