"""Run Eco-Guard Telangana Flask API (development)."""

import logging
import sys
from pathlib import Path

from app import create_app

logging.basicConfig(level=logging.INFO)

app = create_app()


def _reloader_exclude_patterns() -> list[str]:
    """Keep Werkzeug/watchdog from watching venv + system stdlib (avoids endless reloads)."""
    patterns: list[str] = []
    base = Path(sys.base_prefix).resolve()
    patterns.append(str(base / "Lib") + "*")
    dlls = base / "DLLs"
    if dlls.is_dir():
        patterns.append(str(dlls) + "*")

    project_root = Path(__file__).resolve().parents[2]
    for name in ("venv", ".venv"):
        site = project_root / name / "Lib" / "site-packages"
        if site.is_dir():
            patterns.append(str(site.resolve()) + "*")

    return patterns


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True,
    )