"""Eco-Guard Telangana — Flask application factory."""

from __future__ import annotations

import logging

from flask import Flask, Response, jsonify, redirect, request
from flask_cors import CORS

from app.alerts_service import init_mail
from app.config import Config
from app.db_contacts import init_db
from app.verification_log import init_verification_log
from app.routes import bp

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
        allow_headers=["Content-Type", "X-Admin-Token"],
    )

    @app.get("/")
    def root():
        """Send browsers to the Vite UI; JSON for API clients."""
        m = request.accept_mimetypes
        strict_json = m.provided and m.accept_json and not m.accept_html and not m.accept_xhtml
        ui = f"{Config.PUBLIC_UI_BASE_URL.rstrip('/')}/"

        if strict_json:
            return jsonify(
                {
                    "service": "Eco-Guard Telangana API",
                    "ui": ui.rstrip("/"),
                    "health": "/health",
                    "docs": "See backend/flask/app/routes.py for GET /regions, /forests/<slug>, /analyze/<slug>.",
                }
            )

        if request.args.get("info") == "1":
            html = (
                "<!DOCTYPE html><html><head><meta charset='utf-8'><title>Eco-Guard API</title></head>"
                "<body style='font-family:system-ui;margin:2rem'>"
                "<h1>Eco-Guard Telangana API</h1>"
                "<p>This is the JSON API (port 5000), not the web UI.</p>"
                "<p><strong>If the UI link fails</strong>, the Vite dev server is "
                "probably not running. In <code>frontend/react</code>: <code>npm run dev</code>.</p>"
                "<ul>"
                f"<li>App: <a href='{ui}'>{ui.rstrip('/')}</a></li>"
                "<li><a href='/health'>GET /health</a> — API check</li>"
                "</ul>"
                "</body></html>"
            )
            return Response(html, mimetype="text/html; charset=utf-8")

        return redirect(ui, code=302)

    @app.get("/health")
    def health():
        return jsonify(
            {
                "status": "ok",
                "service": "Eco-Guard Telangana",
                "gee_enabled": Config.GEE_ENABLED,
                "hint": "Telangana UI uses this API on port 5000; send X-Admin-Token on /regions and /analyze.",
            }
        )

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(500)
    def server_err(e):
        return jsonify({"error": "Internal server error"}), 500

    return app